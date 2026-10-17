"""Local HTTP integration tests; no provider access or real credentials."""

import concurrent.futures
import contextlib
import http.client
import http.server
import importlib.util
import io
import json
import os
import ssl
import subprocess
import sys
import time
from types import SimpleNamespace
import socket
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "model_gateway.py"
SPEC = importlib.util.spec_from_file_location("model_gateway", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
gateway = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gateway)

SERVER_KEY = "NON_SECRET_TEST_GATEWAY_CREDENTIAL"
CLIENT_KEY = "NON_SECRET_TEST_CLIENT_CREDENTIAL"
MODEL = "mistral-large-4"


@contextlib.contextmanager
def running_gateway(**options):
    with tempfile.TemporaryDirectory() as directory:
        receipt = Path(directory) / "receipt.json"
        policy = gateway.ModelGateway(api_key=SERVER_KEY, receipt=receipt, **options)
        server = gateway.GatewayServer(("127.0.0.1", 0), policy)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
        thread.start()
        try:
            yield server, receipt
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


def request(server, method="POST", path="/v1/chat/completions", body=None, headers=None):
    connection = http.client.HTTPConnection(*server.server_address, timeout=5)
    if body is None:
        body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": "hi"}]}).encode()
    outgoing = {"Content-Type": "application/json", **(headers or {})}
    try:
        connection.request(method, path, body=body, headers=outgoing)
        with connection.getresponse() as response:
            return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def raw_request(server, headers, body=b"", method="POST", path="/v1/chat/completions"):
    with socket.create_connection(server.server_address, timeout=5) as connection:
        lines = [f"{method} {path} HTTP/1.1", *headers, "", ""]
        connection.sendall("\r\n".join(lines).encode("ascii") + body)
        connection.shutdown(socket.SHUT_WR)
        response = http.client.HTTPResponse(connection)
        try:
            response.begin()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            response.close()


class LocalUpstream:
    """Real HTTP fixture; the production transport still sees the pinned TLS host."""

    def __init__(self, status=200, body=b'{"choices":[]}', headers=None, parts=None):
        self.status = status
        self.body = body
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self.requests = []
        self.targets = []
        self.parts = parts
        self.release = threading.Event()
        self.finished = threading.Event()
        fixture = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format, *args):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                fixture.requests.append((self.path, dict(self.headers), body))
                self.send_response(fixture.status)
                for name, value in fixture.headers.items():
                    self.send_header(name, value)
                self.send_header("Connection", "close")
                self.close_connection = True
                if (fixture.parts is None and "Content-Length" not in fixture.headers and
                        "Transfer-Encoding" not in fixture.headers):
                    self.send_header("Content-Length", str(len(fixture.body)))
                self.end_headers()
                try:
                    if fixture.parts is None:
                        self.wfile.write(fixture.body)
                    else:
                        self.wfile.write(fixture.parts[0])
                        self.wfile.flush()
                        fixture.release.wait(5)
                        for part in fixture.parts[1:]:
                            self.wfile.write(part)
                            self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    fixture.finished.set()

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01})

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.release.set()
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()

    def connection_factory(self, host, *, timeout, context):
        self.targets.append((host, context.check_hostname, context.verify_mode, timeout))
        address, port = self.server.server_address[:2]
        return http.client.HTTPConnection(str(address), int(port), timeout=timeout)


class GatewayTests(unittest.TestCase):
    def test_health_is_local_small_metadata_without_credentials(self):
        self.assertIsNotNone(gateway, "model_gateway.py must implement the HTTP gateway")
        with running_gateway() as (server, receipt):
            status, headers, body = request(server, "GET", "/health", body=b"")
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body), {"status": "ok", "model": MODEL})
            self.assertEqual(headers["Connection"], "close")
            self.assertLess(len(body), 256)
            self.assertNotIn(SERVER_KEY, receipt.read_text())
            self.assertNotIn(SERVER_KEY.encode(), body)

    def test_nonstream_pins_model_endpoint_and_replaces_every_client_header(self):
        expected = b'{"id":"local-response","choices":[]}'
        with LocalUpstream(body=expected) as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, _):
                status, _, body = request(server, headers={
                    "Authorization": f"Bearer {CLIENT_KEY}",
                    "Proxy-Authorization": f"Bearer {CLIENT_KEY}",
                    "X-Forwarded-Host": "attacker.invalid",
                    "X-Forwarded-For": "attacker.invalid",
                    "Cookie": "untrusted=cookie",
                    "X-Request-URL": "https://attacker.invalid/",
                })
                self.assertEqual(status, 200)
                self.assertEqual(body, expected)
                self.assertEqual(len(upstream.requests), 1)
                path, headers, submitted = upstream.requests[0]
                self.assertEqual(path, "/v1/chat/completions")
                self.assertEqual(json.loads(submitted)["model"], MODEL)
                self.assertEqual(headers["Authorization"], f"Bearer {SERVER_KEY}")
                self.assertEqual(headers["Host"], "api.mistral.ai")
                for forbidden in ("Proxy-Authorization", "X-Forwarded-Host", "X-Forwarded-For", "Cookie", "X-Request-URL"):
                    self.assertNotIn(forbidden, headers)
                self.assertEqual(upstream.targets[0][:3], ("api.mistral.ai", True, ssl.CERT_REQUIRED))
                self.assertGreater(upstream.targets[0][3], 0)
                self.assertLessEqual(upstream.targets[0][3], 30)

    def test_model_must_be_the_exact_pinned_id_before_any_upstream_io(self):
        with LocalUpstream() as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, _):
                for model in ("mistral-large-latest", "Mistral-Large-4", "mistral-large-4 ", "https://attacker.invalid/", None, [], 4):
                    with self.subTest(model=model):
                        status, _, body = request(server, body=json.dumps({"model": model}).encode())
                        self.assertEqual(status, 400)
                        self.assertEqual(json.loads(body), {"error": {"code": "model_not_allowed"}})
                self.assertEqual(upstream.requests, [])

    def test_only_exact_chat_route_and_permitted_methods_are_accepted(self):
        cases = [
            ("POST", "/v1/models", 404),
            ("POST", "/v1/chat/completions?key=ignored", 404),
            ("POST", "/v1/chat/completions/", 404),
            ("POST", "/v1/chat/%63ompletions", 404),
            ("POST", "https://attacker.invalid/v1/chat/completions", 404),
            ("GET", "/v1/chat/completions", 404),
            ("GET", "/health?anything", 404),
            ("PUT", "/v1/chat/completions", 405),
            ("PATCH", "/v1/chat/completions", 405),
            ("DELETE", "/v1/chat/completions", 405),
            ("OPTIONS", "/v1/chat/completions", 405),
            ("CONNECT", "attacker.invalid:443", 405),
        ]
        with LocalUpstream() as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, _):
                for method, path, expected in cases:
                    with self.subTest(method=method, path=path):
                        status, _, body = request(server, method, path)
                        self.assertEqual(status, expected)
                        self.assertEqual(set(json.loads(body)), {"error"})
                self.assertEqual(upstream.requests, [])

    def test_invalid_or_ambiguous_json_is_rejected_without_logging_input(self):
        invalid = [
            b"not JSON " + SERVER_KEY.encode(),
            b"[]", b"null", b'"a string"',
            b'{"model":"mistral-large-4","temperature":NaN}',
            b'{"model":"bad","model":"mistral-large-4"}',
            b'{"model":"mistral-large-4","messages":"\xff"}',
            '{"model":"mistral-large-4"}'.encode("utf-16"),
            b"[" * 1100 + b"0" + b"]" * 1100,
        ]
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured), LocalUpstream() as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, receipt):
                for body in invalid:
                    with self.subTest(body_prefix=body[:20]):
                        status, _, response = request(server, body=body)
                        self.assertEqual(status, 400)
                        self.assertEqual(json.loads(response), {"error": {"code": "invalid_json"}})
                self.assertEqual(upstream.requests, [])
                self.assertNotIn(SERVER_KEY, receipt.read_text())
        self.assertEqual(captured.getvalue(), "")

    def test_body_framing_is_unambiguous_and_bounded(self):
        valid = b'{"model":"mistral-large-4"}'
        cases = [
            ([], b"", 411),
            (["Content-Length: -1"], valid, 400),
            (["Content-Length: +25"], valid, 400),
            (["Content-Length: potato"], valid, 400),
            ([f"Content-Length: {len(valid)}", f"Content-Length: {len(valid)}"], valid, 400),
            ([f"Content-Length: {len(valid)}", "Transfer-Encoding: chunked"], valid, 400),
            ([f"Content-Length: {len(valid)}", "Content-Encoding: gzip"], valid, 415),
            (["Content-Length: 8388609"], b"", 413),
            (["Content-Length: 100"], valid, 400),
            ([f"Content-Length: {len(valid)}", "Expect: 100-continue"], valid, 417),
        ]
        with LocalUpstream() as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, _):
                for extra, body, expected in cases:
                    with self.subTest(headers=extra):
                        status, _, response = raw_request(server, [
                            "Host: model-gateway", "Content-Type: application/json", *extra,
                        ], body)
                        self.assertEqual(status, expected)
                        self.assertEqual(set(json.loads(response)), {"error"})
                status, _, _ = request(server, headers={"Content-Type": "text/plain"})
                self.assertEqual(status, 415)
                self.assertEqual(upstream.requests, [])

    def test_host_header_and_request_target_are_strictly_bounded(self):
        valid = b'{"model":"mistral-large-4"}'
        cases = [
            ([], "/v1/chat/completions", 400),
            (["Host: attacker.invalid"], "/v1/chat/completions", 400),
            (["Host: model-gateway", "Host: model-gateway"], "/v1/chat/completions", 400),
            (["Host: model-gateway", "X-Padding: " + "x" * 17000], "/v1/chat/completions", 431),
            (["Host: model-gateway"], "//v1/chat/completions", 404),
        ]
        with LocalUpstream() as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, _):
                for headers, path, expected in cases:
                    with self.subTest(path=path, header_count=len(headers)):
                        status, _, body = raw_request(server, [
                            *headers, "Content-Type: application/json", f"Content-Length: {len(valid)}",
                        ], valid, path=path)
                        self.assertEqual(status, expected)
                        self.assertLess(len(body), 128)
                self.assertEqual(upstream.requests, [])

    def test_redirects_and_provider_errors_are_never_forwarded_or_logged(self):
        captured_out, captured_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
            with LocalUpstream(body=SERVER_KEY.encode(), headers={
                "Location": "https://attacker.invalid/" + SERVER_KEY,
                "X-Provider-Debug": SERVER_KEY,
            }) as upstream:
                with running_gateway(connection_factory=upstream.connection_factory) as (server, receipt):
                    for upstream_status in (301, 302, 303, 307, 308, 401, 403, 429, 500):
                        upstream.status = upstream_status
                        with self.subTest(upstream_status=upstream_status):
                            status, headers, body = request(server)
                            self.assertEqual(status, 502)
                            code = "upstream_redirect_denied" if upstream_status < 400 else "upstream_error"
                            self.assertEqual(json.loads(body), {"error": {"code": code}})
                            self.assertNotIn(SERVER_KEY, str(headers))
                            self.assertNotIn("Location", headers)
                            self.assertNotIn(SERVER_KEY, receipt.read_text())
                    self.assertEqual(len(upstream.requests), 9)
                    self.assertTrue(all(target[0] == "api.mistral.ai" for target in upstream.targets))
        self.assertEqual(captured_out.getvalue(), "")
        self.assertEqual(captured_err.getvalue(), "")

    def test_receipt_records_submissions_not_client_model_claims_and_is_private(self):
        with LocalUpstream() as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, receipt):
                initial = json.loads(receipt.read_text())
                self.assertEqual(initial.get("request_count"), 0)
                self.assertEqual(initial["model_ids_submitted"], [])
                self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
                self.assertEqual(request(server)[0], 200)
                self.assertEqual(request(server, body=b'{"model":"not-the-pinned-model"}')[0], 400)
                upstream.status = 503
                self.assertEqual(request(server)[0], 502)
                report = json.loads(receipt.read_text())
                self.assertEqual(report["request_count"], 3)
                self.assertEqual(report["upstream_request_count"], 2)
                self.assertEqual(report["model_ids_submitted"], [MODEL])
                self.assertEqual(report["successful_2xx"], 1)
                self.assertEqual(report["errors"], {"model_not_allowed": 1, "upstream_error": 1})
                self.assertGreaterEqual(report["elapsed_seconds"], 0)
                self.assertIn("started_at", report)
                self.assertIn("updated_at", report)
                self.assertEqual(report["status"], "active")
                self.assertNotIn(SERVER_KEY, receipt.read_text())
                self.assertNotIn("not-the-pinned-model", receipt.read_text())
                self.assertEqual(list(receipt.parent.iterdir()), [receipt])

    def test_global_request_budget_is_atomic_under_concurrent_clients(self):
        with LocalUpstream() as upstream:
            with running_gateway(max_requests=3, connection_factory=upstream.connection_factory) as (server, receipt):
                self.assertEqual(request(server, "GET", "/health", body=b"")[0], 200)
                stop = threading.Event()
                corrupt = []

                def read_receipts():
                    while not stop.is_set():
                        try:
                            json.loads(receipt.read_text())
                        except (ValueError, OSError) as error:
                            corrupt.append(type(error).__name__)
                        stop.wait(0.001)

                reader = threading.Thread(target=read_receipts)
                reader.start()
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
                        results = list(pool.map(lambda _: request(server)[0], range(12)))
                finally:
                    stop.set()
                    reader.join(timeout=5)
                self.assertEqual(results.count(200), 3)
                self.assertEqual(results.count(429), 9)
                self.assertEqual(len(upstream.requests), 3)
                report = json.loads(receipt.read_text())
                self.assertEqual(report["request_count"], 3)
                self.assertEqual(report["upstream_request_count"], 3)
                self.assertEqual(report["successful_2xx"], 3)
                self.assertEqual(report["errors"], {"request_budget_exceeded": 9})
                self.assertEqual(report["status"], "exhausted")
                self.assertEqual(corrupt, [])

    def test_deadline_is_global_and_caps_the_upstream_timeout(self):
        now = [100.0]
        with LocalUpstream() as upstream:
            with running_gateway(deadline_seconds=10, clock=lambda: now[0],
                                 connection_factory=upstream.connection_factory) as (server, receipt):
                self.assertEqual(request(server)[0], 200)
                self.assertLessEqual(upstream.targets[0][3], 10)
                now[0] = 110.0
                status, _, body = request(server)
                self.assertEqual(status, 408)
                self.assertEqual(json.loads(body), {"error": {"code": "deadline_exceeded"}})
                self.assertEqual(len(upstream.requests), 1)
                report = json.loads(receipt.read_text())
                self.assertEqual(report["request_count"], 1)
                self.assertEqual(report["status"], "expired")
                self.assertEqual(report["deadline_seconds"], 10)
                self.assertEqual(report["elapsed_seconds"], 10)
                self.assertEqual(report["errors"], {"deadline_exceeded": 1})

    def test_sse_is_flushed_before_upstream_finishes_without_a_false_length(self):
        first = b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
        last = b"data: [DONE]\n\n"
        with LocalUpstream(parts=[first, last], headers={
            "Content-Type": "text/event-stream; charset=utf-8; debug=" + SERVER_KEY,
            "Set-Cookie": SERVER_KEY,
            "X-Provider-Debug": SERVER_KEY,
        }) as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, receipt):
                connection = http.client.HTTPConnection(*server.server_address, timeout=3)
                try:
                    connection.request("POST", "/v1/chat/completions",
                                       body=json.dumps({"model": MODEL, "stream": True}),
                                       headers={"Content-Type": "application/json"})
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.getheader("Content-Type"), "text/event-stream")
                    self.assertIsNone(response.getheader("Content-Length"))
                    self.assertIsNone(response.getheader("Transfer-Encoding"))
                    self.assertEqual(response.getheader("Connection"), "close")
                    self.assertNotIn(SERVER_KEY, str(response.getheaders()))
                    self.assertEqual(response.read1(len(first)), first)
                    self.assertFalse(upstream.finished.is_set(), "SSE must not buffer the complete response")
                    upstream.release.set()
                    self.assertEqual(response.read(), last)
                    response.close()
                    self.assertEqual(json.loads(receipt.read_text())["successful_2xx"], 1)
                finally:
                    upstream.release.set()
                    connection.close()

    def test_nonstream_response_is_capped_before_exposing_provider_bytes(self):
        with LocalUpstream(body=b"x" * 65) as upstream:
            with running_gateway(max_response_bytes=64, connection_factory=upstream.connection_factory) as (server, receipt):
                status, _, body = request(server)
                self.assertEqual(status, 502)
                self.assertEqual(json.loads(body), {"error": {"code": "response_too_large"}})
                report = json.loads(receipt.read_text())
                self.assertEqual(report["successful_2xx"], 0)
                self.assertEqual(report["errors"], {"response_too_large": 1})

    def test_stream_is_closed_and_receipted_on_response_byte_limit(self):
        first = b"data: first\n\n"
        with LocalUpstream(parts=[first, b"x" * 100 + b"data: [DONE]\n\n"],
                           headers={"Content-Type": "text/event-stream"}) as upstream:
            with running_gateway(max_response_bytes=64, connection_factory=upstream.connection_factory) as (server, receipt):
                connection = http.client.HTTPConnection(*server.server_address, timeout=3)
                try:
                    connection.request("POST", "/v1/chat/completions", body=json.dumps({"model": MODEL, "stream": True}),
                                       headers={"Content-Type": "application/json"})
                    response = connection.getresponse()
                    body = response.read1(len(first))
                    self.assertEqual(body, first)
                    upstream.release.set()
                    body += response.read()
                    response.close()
                    self.assertLessEqual(len(body), 64)
                    self.assertNotIn(b"[DONE]", body)
                    report = json.loads(receipt.read_text())
                    self.assertEqual(report["successful_2xx"], 0)
                    self.assertEqual(report["errors"], {"response_too_large": 1})
                finally:
                    upstream.release.set()
                    connection.close()

    def test_transport_failures_are_sanitized_without_tracebacks_or_credentials(self):
        for failure, expected_status, expected_code in (
            (OSError, 502, "upstream_unavailable"),
            (TimeoutError, 504, "upstream_timeout"),
        ):
            def unavailable(*args, **kwargs):
                raise failure("provider exception " + SERVER_KEY)

            captured = io.StringIO()
            with self.subTest(failure=failure), contextlib.redirect_stderr(captured):
                with running_gateway(connection_factory=unavailable) as (server, receipt):
                    status, _, body = request(server)
                    self.assertEqual(status, expected_status)
                    self.assertEqual(json.loads(body), {"error": {"code": expected_code}})
                    report = json.loads(receipt.read_text())
                    self.assertEqual(report["upstream_request_count"], 0)
                    self.assertEqual(report["model_ids_submitted"], [])
                    self.assertEqual(report["errors"], {expected_code: 1})
                    self.assertNotIn(SERVER_KEY, receipt.read_text())
            self.assertEqual(captured.getvalue(), "")

    def test_stream_deadline_closes_without_fabricating_a_successful_completion(self):
        now = [0.0]
        first = b"data: first\n\n"
        with LocalUpstream(parts=[first, b"data: [DONE]\n\n"],
                           headers={"Content-Type": "text/event-stream"}) as upstream:
            with running_gateway(deadline_seconds=10, clock=lambda: now[0],
                                 connection_factory=upstream.connection_factory) as (server, receipt):
                connection = http.client.HTTPConnection(*server.server_address, timeout=3)
                try:
                    connection.request("POST", "/v1/chat/completions", body=json.dumps({"model": MODEL, "stream": True}),
                                       headers={"Content-Type": "application/json"})
                    response = connection.getresponse()
                    self.assertEqual(response.read1(len(first)), first)
                    now[0] = 10.0
                    upstream.release.set()
                    self.assertNotIn(b"[DONE]", response.read())
                    response.close()
                    report = json.loads(receipt.read_text())
                    self.assertEqual(report["successful_2xx"], 0)
                    self.assertEqual(report["errors"], {"deadline_exceeded": 1})
                    self.assertEqual(report["status"], "expired")
                finally:
                    upstream.release.set()
                    connection.close()

    def test_cli_requires_environment_key_and_serves_the_documented_interface(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "cli.json"
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            command = [sys.executable, str(MODULE_PATH), "--host", "127.0.0.1", "--port", str(port),
                       "--receipt", str(receipt), "--max-requests", "40", "--max-response-bytes", "16777216",
                       "--max-request-bytes", "12345", "--max-total-request-bytes", "23456",
                       "--deadline-seconds", "1200"]
            environment = dict(os.environ)
            environment.pop("MISTRAL_API_KEY", None)
            missing = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=5)
            with self.subTest(mode="missing key"):
                self.assertEqual(missing.returncode, 2)
                self.assertEqual(missing.stdout, "")
                self.assertEqual(missing.stderr, "mistral_api_key_required\n")
                self.assertFalse(receipt.exists())
            environment["MISTRAL_API_KEY"] = SERVER_KEY
            process = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                target = SimpleNamespace(server_address=("127.0.0.1", port))
                deadline = time.monotonic() + 5
                status, body = None, b""
                while process.poll() is None and time.monotonic() < deadline:
                    try:
                        status, _, body = request(target, "GET", "/health", body=b"")
                        break
                    except OSError:
                        time.sleep(0.01)
                self.assertEqual(status, 200, "CLI did not start its HTTP server")
                self.assertNotIn(SERVER_KEY.encode(), body)
                report = json.loads(receipt.read_text())
                self.assertEqual(report["request_count"], 0)
                self.assertEqual(report["model_ids_submitted"], [])
                self.assertEqual(report["max_request_bytes"], 12345)
                self.assertEqual(report["max_total_request_bytes"], 23456)
            finally:
                process.terminate()
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0)
            self.assertEqual(stdout, b"")
            self.assertEqual(stderr, b"")
            self.assertEqual(json.loads(receipt.read_text())["status"], "closed")

    def test_gateway_explicitly_disables_reasoning_independent_of_worker_settings(self):
        with LocalUpstream() as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, _):
                for options in ({}, {"reasoning_effort": "high"}, {"reasoning_effort": None},
                                {"reasoning_effort": "none"}):
                    with self.subTest(options=options):
                        status, _, _ = request(server, body=json.dumps({"model": MODEL, **options}).encode())
                        self.assertEqual(status, 200)
                        outgoing = json.loads(upstream.requests[-1][2])
                        self.assertEqual(outgoing.get("reasoning_effort"), "none")
                        self.assertEqual(outgoing["max_tokens"], 8192)
                        self.assertEqual(outgoing["n"], 1)

    def test_outgoing_generation_is_explicitly_bounded_even_without_client_limits(self):
        with LocalUpstream() as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, _):
                for options, expected in (({}, 8192), ({"max_tokens": 200000}, 8192),
                                          ({"max_tokens": 7}, 7), ({"max_tokens": 8192, "n": 1}, 8192),
                                          ({"max_tokens": None}, 8192), ({"max_tokens": 0}, 8192)):
                    with self.subTest(options=options):
                        status, _, _ = request(server, body=json.dumps({"model": MODEL, **options}).encode())
                        self.assertEqual(status, 200)
                        outgoing = json.loads(upstream.requests[-1][2])
                        self.assertEqual(outgoing.get("max_tokens"), expected)
                        self.assertEqual(outgoing.get("n"), 1)

    def test_generation_fanout_invalid_token_values_and_aliases_are_rejected(self):
        cases = [{"n": value} for value in (2, 0, True, 1.0, None)]
        cases += [{"max_tokens": value} for value in (True, False, -1, 1.5, "8192")]
        cases += [{"max_tokens": 1, alias: 999999} for alias in (
            "max_completion_tokens", "max_output_tokens", "max_new_tokens", "max_length",
            "num_predict", "max_tokens_to_sample",
        )]
        with LocalUpstream() as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, _):
                for options in cases:
                    with self.subTest(options=options):
                        status, _, body = request(server, body=json.dumps({"model": MODEL, **options}).encode())
                        self.assertEqual(status, 400)
                        self.assertEqual(json.loads(body), {"error": {"code": "invalid_generation_parameters"}})
                self.assertEqual(upstream.requests, [])

    def test_request_cap_applies_to_raw_input_and_normalized_upstream_bytes(self):
        valid = json.dumps({"model": MODEL}, separators=(",", ":")).encode()
        expanded = json.dumps({"model": MODEL, "messages": "é" * 12},
                              separators=(",", ":"), ensure_ascii=False).encode()
        self.assertLessEqual(len(expanded), 96)
        with LocalUpstream() as upstream:
            with running_gateway(max_request_bytes=96, connection_factory=upstream.connection_factory) as (server, _):
                self.assertEqual(request(server, body=valid)[0], 200)
                oversized = valid + b" " * (97 - len(valid))
                for body in (oversized, expanded):
                    with self.subTest(raw_size=len(body)):
                        status, _, response = request(server, body=body)
                        self.assertEqual(status, 413)
                        self.assertEqual(json.loads(response), {"error": {"code": "request_too_large"}})
                self.assertEqual(len(upstream.requests), 1)
            with running_gateway(connection_factory=upstream.connection_factory) as (server, _):
                self.assertEqual(raw_request(server, ["Host: model-gateway", "Content-Type: application/json",
                                                      "Content-Length: 262145"])[0], 413)

    def test_cumulative_serialized_request_budget_is_atomic_before_upstream_io(self):
        data = {"model": MODEL, "messages": [{"role": "user", "content": "hi"}]}
        raw = json.dumps(data, indent=2).encode() + b" " * 1000
        normalized = json.dumps({**data, "max_tokens": 8192, "n": 1, "reasoning_effort": "none"}, separators=(",", ":")).encode()
        limit = 2 * len(normalized)
        with LocalUpstream() as upstream:
            with running_gateway(max_total_request_bytes=limit,
                                 connection_factory=upstream.connection_factory) as (server, receipt):
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                    results = list(pool.map(lambda _: request(server, body=raw), range(8)))
                self.assertEqual(sum(status == 200 for status, _, _ in results), 2)
                denied = [json.loads(body) for status, _, body in results if status == 429]
                self.assertEqual(denied, [{"error": {"code": "request_bytes_budget_exceeded"}}] * 6)
                self.assertEqual(len(upstream.requests), 2)
                self.assertEqual(sum(len(body) for _, _, body in upstream.requests), limit)
                report = json.loads(receipt.read_text())
                self.assertEqual(report["total_request_bytes"], limit)
                self.assertEqual(report["max_total_request_bytes"], limit)
                self.assertEqual(report["max_request_bytes"], 262144)
                self.assertEqual(report["successful_2xx"], 2)
                self.assertEqual(report["status"], "exhausted")

    def test_invalid_keys_or_unbounded_configuration_fail_before_writing_receipts(self):
        invalid = [
            {"api_key": ""}, {"api_key": "bad\r\n" + SERVER_KEY},
            {"max_requests": 0}, {"max_requests": True},
            {"max_request_bytes": 0}, {"max_total_request_bytes": -1},
            {"max_response_bytes": 0}, {"deadline_seconds": 0},
            {"deadline_seconds": float("nan")}, {"deadline_seconds": float("inf")},
        ]
        with tempfile.TemporaryDirectory() as directory:
            for options in invalid:
                with self.subTest(parameter=next(iter(options))):
                    receipt = Path(directory) / "invalid.json"
                    with self.assertRaisesRegex(ValueError, "invalid_gateway_configuration"):
                        gateway.ModelGateway(**{"api_key": SERVER_KEY, "receipt": receipt, **options})
                    self.assertFalse(receipt.exists())

    def test_receipt_failure_denies_upstream_work_without_exposing_exception_text(self):
        captured = io.StringIO()
        with LocalUpstream() as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, receipt):
                with contextlib.redirect_stderr(captured), mock.patch.object(
                    server.gateway, "_write_receipt", side_effect=OSError(SERVER_KEY)
                ):
                    status, _, body = request(server)
                    self.assertEqual(status, 503)
                    self.assertEqual(json.loads(body), {"error": {"code": "receipt_unavailable"}})
                self.assertEqual(upstream.requests, [])
                self.assertNotIn(SERVER_KEY, receipt.read_text())
        self.assertEqual(captured.getvalue(), "")

    def test_incomplete_ingress_is_closed_within_its_wall_clock_limit(self):
        partials = [
            b"POST /v1/chat/completions HTTP/1.1\r\nHost: model-gateway\r\nX-Slow: ",
            b"POST /v1/chat/completions HTTP/1.1\r\nHost: model-gateway\r\n"
            b"Content-Type: application/json\r\nContent-Length: 100\r\n\r\n{",
        ]
        with mock.patch.object(gateway, "INPUT_TIMEOUT_SECONDS", 0.05, create=True), LocalUpstream() as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, _):
                for partial in partials:
                    with self.subTest(phase=partial[-10:]):
                        with socket.create_connection(server.server_address, timeout=1) as connection:
                            connection.sendall(partial)
                            self.assertEqual(connection.recv(4096), b"")
                self.assertEqual(upstream.requests, [])
                self.assertEqual(request(server, "GET", "/health", body=b"")[0], 200)

    def test_open_connections_are_capped_without_unbounded_threads(self):
        with mock.patch.object(gateway, "MAX_CONNECTIONS", 2, create=True):
            with running_gateway() as (server, _):
                with contextlib.ExitStack() as connections:
                    for _ in range(2):
                        connection = connections.enter_context(socket.create_connection(server.server_address, timeout=1))
                        connection.sendall(b"G")
                    with self.assertRaises(OSError):
                        request(server, "GET", "/health", body=b"")

    def test_metadata_is_local_model_pinned_and_rejects_request_bodies(self):
        with LocalUpstream() as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, receipt):
                status, _, body = request(server, "GET", "/v1/models", body=b"")
                self.assertEqual(status, 200)
                self.assertEqual([model["id"] for model in json.loads(body)["data"]], [MODEL])
                self.assertLess(len(body), 256)
                for path in ("/health", "/v1/models"):
                    self.assertEqual(request(server, "GET", path, body=b"x")[0], 400)
                self.assertEqual(json.loads(receipt.read_text())["request_count"], 0)
                self.assertEqual(upstream.requests, [])

    def test_invalid_or_truncated_provider_responses_do_not_reach_the_worker(self):
        cases = [
            ({"Content-Type": "text/plain"}, "invalid_upstream_response"),
            ({"Content-Encoding": "gzip"}, "invalid_upstream_response"),
            ({"Content-Length": "1000"}, "upstream_incomplete_response"),
        ]
        for headers, code in cases:
            with self.subTest(headers=headers), LocalUpstream(body=SERVER_KEY.encode(), headers=headers) as upstream:
                with running_gateway(connection_factory=upstream.connection_factory) as (server, receipt):
                    status, _, body = request(server)
                    self.assertEqual(status, 502)
                    self.assertEqual(json.loads(body), {"error": {"code": code}})
                    self.assertNotIn(SERVER_KEY.encode(), body)
                    self.assertEqual(json.loads(receipt.read_text())["successful_2xx"], 0)

    def test_chunked_upstream_sse_is_decoded_and_relayed_as_a_close_delimited_stream(self):
        events = [b'data: {"choices":[]}\n\n', b"data: [DONE]\n\n"]
        wire = b"".join(f"{len(part):x}\r\n".encode() + part + b"\r\n" for part in events) + b"0\r\n\r\n"
        with LocalUpstream(body=wire, headers={"Content-Type": "text/event-stream",
                                               "Transfer-Encoding": "chunked"}) as upstream:
            with running_gateway(connection_factory=upstream.connection_factory) as (server, receipt):
                status, headers, body = request(server, body=json.dumps({"model": MODEL, "stream": True}).encode())
                self.assertEqual(status, 200)
                self.assertEqual(body, b"".join(events))
                self.assertNotIn("Content-Length", headers)
                self.assertNotIn("Transfer-Encoding", headers)
                self.assertEqual(json.loads(receipt.read_text())["successful_2xx"], 1)

    def test_metadata_refreshes_the_atomic_receipt_without_spending_request_budget(self):
        with running_gateway() as (server, receipt):
            with mock.patch.object(server.gateway, "_write_receipt", wraps=server.gateway._write_receipt) as persist:
                self.assertEqual(request(server, "GET", "/health", body=b"")[0], 200)
                persist.assert_called_once()
            self.assertEqual(json.loads(receipt.read_text())["request_count"], 0)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Internal-only, standard-library model gateway (Python 3.12+).

Deployment (MISTRAL_API_KEY must be injected into this container's environment):
    python /policy/model_gateway.py --host 0.0.0.0 --port 8080 \
        --receipt /receipts/writer.json --max-requests 40 \
        --max-request-bytes 262144 --max-total-request-bytes 1500000 \
        --max-response-bytes 16777216 --deadline-seconds 1200

Give only the trusted gateway external networking and the real credential. Keep
its port on the internal Docker network, never published. Mount /receipts only
in the gateway, outside worker-writable mounts. Worker API base is
http://model-gateway:8080/v1; any SDK-required worker key must be a dummy value.
Every client header, including Authorization, is discarded. Production connects
only to verified-TLS api.mistral.ai; no URL, model, proxy, or key CLI override exists.

Only POST /v1/chat/completions reaches the provider. Model must equal
mistral-large-4. Outgoing n is always 1 and max_tokens is always 1..8192;
missing/null/zero token limits become 8192, positive larger limits are clamped.
Boolean/negative/noninteger limits and alternative token-limit aliases are denied.
Raw and normalized bodies both obey max-request-bytes. Total normalized JSON
bytes are reserved atomically before upstream I/O and never refunded on failure.
Non-metadata attempts consume request slots even when validation fails; rejected
over-budget attempts do not increase request_count. GET /health and /v1/models
are bodyless local metadata, not upstream entitlement or model-identity claims.

Receipts are atomic, mode 0600, and contain only counters, fixed submitted model
IDs, sanitized error-code counts, timestamps and status. model_ids_submitted is
updated only after an HTTP request has actually been sent, never from a provider
self-report. successful_2xx counts fully read upstream 2xx bodies, not client ACKs.
SSE is flushed in bounded chunks with Connection: close and no Content-Length or
Transfer-Encoding. An error after stream headers closes it and records failure;
it never appends fake completion events. Ingress has a 10-second wall-clock cap,
connections are capped at 16, and upstream socket I/O is bounded by 30 seconds and
the shared deadline. Keep an outer container/runner timeout for DNS or OS stalls.

Embedding: ModelGateway(api_key=..., receipt=..., <matching CLI option names
using underscores>) and GatewayServer((host, port), policy). connection_factory
and clock constructor arguments are trusted test hooks, never client/CLI inputs.
"""

import argparse
from datetime import datetime, timezone
import http.client
import http.server
import json
import math
import os
from pathlib import Path
import signal
import socket
import ssl
import sys
import tempfile
import threading
import time
from typing import cast


MODEL = "mistral-large-4"
MAX_REQUEST_BYTES = 262144
MAX_CONNECTIONS = 16
INPUT_TIMEOUT_SECONDS = 10


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonfinite_json_number")


class _Fault(Exception):
    def __init__(self, status, code):
        self.status = status
        self.code = code


class ModelGateway:
    def __init__(self, *, api_key, receipt, max_requests=40, deadline_seconds=1200,
                 max_request_bytes=MAX_REQUEST_BYTES, max_response_bytes=16777216,
                 max_total_request_bytes=1500000, connection_factory=None, clock=time.monotonic):
        limits = (max_requests, max_request_bytes, max_total_request_bytes, max_response_bytes)
        if (not isinstance(api_key, str) or not api_key or len(api_key) > 4096 or
                not api_key.isascii() or any(ord(char) <= 32 or ord(char) == 127 for char in api_key) or
                any(type(value) is not int or value <= 0 for value in limits) or
                type(deadline_seconds) not in (int, float) or deadline_seconds <= 0 or
                not math.isfinite(deadline_seconds)):
            raise ValueError("invalid_gateway_configuration")
        self.api_key = api_key
        self.max_requests = max_requests
        self.max_response_bytes = max_response_bytes
        self.max_request_bytes = max_request_bytes
        self.max_total_request_bytes = max_total_request_bytes
        self.total_request_bytes = 0
        self.connection_factory = connection_factory or http.client.HTTPSConnection
        self.tls_context = ssl.create_default_context()
        self.receipt = Path(receipt)
        self.receipt.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.clock = clock
        self.started = clock()
        self.deadline_seconds = deadline_seconds
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.request_count = 0
        self.upstream_request_count = 0
        self.successful_2xx = 0
        self.model_ids_submitted = set()
        self.errors = {}
        self.closed = False
        self._write_receipt()

    def _write_receipt(self):
        # All callers hold lock once serving starts; the worker cannot mount this path.
        data = {
            "request_count": self.request_count,
            "upstream_request_count": self.upstream_request_count,
            "total_request_bytes": self.total_request_bytes,
            "max_request_bytes": self.max_request_bytes,
            "max_total_request_bytes": self.max_total_request_bytes,
            "model_ids_submitted": sorted(self.model_ids_submitted),
            "successful_2xx": self.successful_2xx,
            "errors": dict(self.errors),
            "started_at": self.started_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(self.clock() - self.started, 6),
            "deadline_seconds": self.deadline_seconds,
            "status": ("expired" if self.time_left() <= 0 else
                       "exhausted" if (self.request_count >= self.max_requests or
                                       self.total_request_bytes >= self.max_total_request_bytes) else
                       "closed" if self.closed else
                       "active" if self.request_count else "ready"),
        }
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.receipt.parent,
                                             prefix=".gateway-receipt-", delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(data, handle, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.receipt)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def refresh(self):
        with self.lock:
            self._write_receipt()

    def close(self):
        with self.lock:
            self.closed = True
            self._write_receipt()

    def time_left(self):
        return self.deadline_seconds - (self.clock() - self.started)

    def io_timeout(self, limit=30):
        remaining = self.time_left()
        if remaining <= 0:
            raise _Fault(408, "deadline_exceeded")
        return min(limit, remaining)

    def admit(self):
        with self.lock:
            if self.time_left() <= 0:
                return "deadline_exceeded"
            if self.request_count >= self.max_requests:
                return "request_budget_exceeded"
            self.request_count += 1
            self._write_receipt()
            return None

    def reserve_bytes(self, size):
        with self.lock:
            self.io_timeout()
            if size > self.max_request_bytes:
                raise _Fault(413, "request_too_large")
            if self.total_request_bytes + size > self.max_total_request_bytes:
                raise _Fault(429, "request_bytes_budget_exceeded")
            # Never refund: a transport failure can occur after the provider accepted work.
            self.total_request_bytes += size
            self._write_receipt()

    def submitted(self):
        with self.lock:
            self.upstream_request_count += 1
            self.model_ids_submitted.add(MODEL)
            self._write_receipt()

    def record_error(self, code):
        with self.lock:
            self.errors[code] = self.errors.get(code, 0) + 1
            self._write_receipt()

    def record_success(self):
        with self.lock:
            self.successful_2xx += 1
            self._write_receipt()


class GatewayServer(http.server.ThreadingHTTPServer):
    daemon_threads = False

    def __init__(self, address, gateway):
        self.gateway = gateway
        self.slots = threading.BoundedSemaphore(MAX_CONNECTIONS)
        super().__init__(address, _Handler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def server_close(self):
        super().server_close()
        self.gateway.close()

    def handle_error(self, request, client_address):
        # Never emit exception messages, request data, or headers.
        pass


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    @property
    def policy(self) -> ModelGateway:
        return cast(GatewayServer, self.server).gateway

    def abort_ingress(self):
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def handle_one_request(self):
        remaining = self.policy.time_left()
        self.ingress_timer = threading.Timer(
            min(INPUT_TIMEOUT_SECONDS, remaining) if remaining > 0 else INPUT_TIMEOUT_SECONDS,
            self.abort_ingress,
        )
        self.ingress_timer.daemon = True
        self.ingress_timer.start()
        self.headers_sent = False
        self.upstream_phase = False
        self.request_version = "HTTP/1.1"
        self.command = ""
        self.requestline = ""
        self.close_connection = True
        try:
            self.raw_requestline = self.rfile.readline(8193)
            if len(self.raw_requestline) > 8192:
                self.send_json(414, {"error": {"code": "request_line_too_large"}})
            elif self.raw_requestline and self.parse_request():
                self.close_connection = True
                if self.command not in {"GET", "POST"}:
                    self.send_json(405, {"error": {"code": "method_not_allowed"}})
                else:
                    getattr(self, "do_" + self.command)()
            self.wfile.flush()
        except _Fault as failure:
            self.respond_failure(failure.status, failure.code)
        except TimeoutError:
            if self.policy.time_left() <= 0:
                self.respond_failure(408, "deadline_exceeded")
                return
            code = "upstream_timeout" if self.upstream_phase else "request_timeout"
            self.respond_failure(504 if self.upstream_phase else 408, code)
        except (OSError, http.client.HTTPException):
            code = "upstream_unavailable" if self.upstream_phase else "invalid_request"
            self.respond_failure(502 if self.upstream_phase else 400, code)
        except Exception:
            self.respond_failure(500, "gateway_error")
        finally:
            self.ingress_timer.cancel()
            self.close_connection = True

    def respond_failure(self, status, code):
        try:
            self.policy.record_error(code)
        except Exception:
            status, code = 503, "receipt_unavailable"
        try:
            if not self.headers_sent:
                body = json.dumps({"error": {"code": code}}, separators=(",", ":")).encode()
                self.send_bytes(status, body, "application/json")
        except (OSError, http.client.HTTPException):
            # Disconnected clients must not produce a traceback.
            pass

    def end_headers(self):
        self.headers_sent = True
        super().end_headers()

    def parse_request(self):
        if not super().parse_request():
            return False
        if not (self.command == "GET" and self.path in {"/health", "/v1/models"}):
            error = self.policy.admit()
            if error:
                self.send_json(408 if error == "deadline_exceeded" else 429, {"error": {"code": error}})
                return False
        if len(self.headers) > 32 or sum(len(k) + len(v) + 4 for k, v in self.headers.items()) > 16384:
            raise _Fault(431, "headers_too_large")
        # BaseHTTPRequestHandler normalizes leading //; route on the literal target.
        self.path = self.raw_requestline.decode("iso-8859-1").split()[1]
        if self.command in {"GET", "POST"} and not self.path.startswith("/"):
            raise _Fault(404, "route_not_allowed")
        hosts = self.headers.get_all("Host", [])
        port = cast(GatewayServer, self.server).server_port
        allowed = {"model-gateway", "localhost", "127.0.0.1"}
        allowed.update(f"{host}:{port}" for host in tuple(allowed))
        if len(hosts) != 1 or hosts[0].lower() not in allowed:
            raise _Fault(400, "invalid_host")
        return True

    def log_message(self, format, *args):
        pass

    def send_json(self, status, data):
        if status >= 400:
            self.policy.record_error(data["error"]["code"])
        else:
            self.policy.refresh()
        body = json.dumps(data, separators=(",", ":")).encode()
        self.send_bytes(status, body, "application/json")

    def send_bytes(self, status, body, content_type):
        self.connection.settimeout(min(INPUT_TIMEOUT_SECONDS, max(0.001, self.policy.time_left())))
        self.send_response_only(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):
        if code == 501:
            self.send_json(405, {"error": {"code": "method_not_allowed"}})
        else:
            self.send_json(code, {"error": {"code": "invalid_http"}})

    def do_GET(self):
        self.ingress_timer.cancel()
        if self.path not in {"/health", "/v1/models"}:
            raise _Fault(404, "route_not_allowed")
        if (self.headers.get_all("Transfer-Encoding") or self.headers.get_all("Content-Encoding") or
                self.headers.get_all("Content-Length", []) not in ([], ["0"])):
            raise _Fault(400, "metadata_body_not_allowed")
        if self.path == "/health":
            self.send_json(200, {"status": "ok", "model": MODEL})
        else:
            # Policy catalog only, not a claim about upstream entitlement or self-reported identity.
            self.send_json(200, {"object": "list", "data": [{"id": MODEL, "object": "model"}]})

    def handle_expect_100(self):
        self.send_json(417, {"error": {"code": "expectation_not_allowed"}})
        return False

    def read_body(self):
        if self.headers.get_all("Transfer-Encoding"):
            raise _Fault(400, "invalid_framing")
        if self.headers.get_all("Content-Encoding"):
            raise _Fault(415, "encoding_not_allowed")
        types = self.headers.get_all("Content-Type", [])
        if len(types) != 1 or types[0].split(";", 1)[0].strip().lower() != "application/json":
            raise _Fault(415, "json_required")
        lengths = self.headers.get_all("Content-Length", [])
        if not lengths:
            raise _Fault(411, "length_required")
        if (len(lengths) != 1 or len(lengths[0]) > 10 or
                not lengths[0].isascii() or not lengths[0].isdecimal()):
            raise _Fault(400, "invalid_length")
        length = int(lengths[0])
        if length > self.policy.max_request_bytes:
            raise _Fault(413, "request_too_large")
        body = self.rfile.read(length)
        if len(body) != length:
            raise _Fault(400, "incomplete_body")
        return body

    def upstream_chunks(self, response, upstream_socket):
        policy = self.policy
        total = 0
        while True:
            timeout = policy.io_timeout()
            if response.isclosed():
                break
            upstream_socket.settimeout(timeout)
            chunk = response.read1(min(65536, policy.max_response_bytes - total + 1))
            policy.io_timeout()
            if not chunk:
                break
            total += len(chunk)
            if total > policy.max_response_bytes:
                raise _Fault(502, "response_too_large")
            yield chunk
        if response.length not in (None, 0):
            raise _Fault(502, "upstream_incomplete_response")

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            raise _Fault(404, "route_not_allowed")
        body = self.read_body()
        self.ingress_timer.cancel()
        try:
            data = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object,
                              parse_constant=_reject_constant)
            if not isinstance(data, dict):
                raise ValueError("json_object_required")
        except (ValueError, UnicodeError, RecursionError):
            raise _Fault(400, "invalid_json") from None
        if data.get("model") != MODEL:
            raise _Fault(400, "model_not_allowed")
        tokens = data.get("max_tokens", 8192)
        if tokens is None:
            tokens = 8192
        copies = data.get("n", 1)
        aliases = {"max_completion_tokens", "max_output_tokens", "max_new_tokens",
                   "max_length", "num_predict", "max_tokens_to_sample"}
        if (type(tokens) is not int or tokens < 0 or type(copies) is not int or
                copies != 1 or aliases.intersection(data)):
            raise _Fault(400, "invalid_generation_parameters")
        data["max_tokens"] = min(tokens or 8192, 8192)
        data["n"] = 1
        data["reasoning_effort"] = "high"
        try:
            body = json.dumps(data, separators=(",", ":"), allow_nan=False).encode("utf-8")
        except (ValueError, RecursionError):
            raise _Fault(400, "invalid_json") from None
        policy = self.policy
        policy.reserve_bytes(len(body))
        self.upstream_phase = True
        connection = policy.connection_factory(
            "api.mistral.ai", timeout=policy.io_timeout(), context=policy.tls_context
        )
        try:
            connection.request("POST", "/v1/chat/completions", body=body, headers={
                "Host": "api.mistral.ai",
                "Authorization": "Bearer " + policy.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            })
            upstream_socket = connection.sock
            policy.submitted()
            upstream_socket.settimeout(policy.io_timeout())
            response = connection.getresponse()
            try:
                if 300 <= response.status < 400:
                    self.send_json(502, {"error": {"code": "upstream_redirect_denied"}})
                elif not 200 <= response.status < 300:
                    self.send_json(502, {"error": {"code": "upstream_error"}})
                else:
                    content_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
                    if (content_type not in {"application/json", "text/event-stream"} or
                            response.getheader("Content-Encoding", "identity").lower() != "identity"):
                        raise _Fault(502, "invalid_upstream_response")
                    if content_type == "text/event-stream":
                        self.send_response_only(response.status)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Connection", "close")
                        self.end_headers()
                        self.close_connection = True
                        for chunk in self.upstream_chunks(response, upstream_socket):
                            self.connection.settimeout(policy.io_timeout(10))
                            self.wfile.write(chunk)
                            self.wfile.flush()
                        policy.record_success()
                    else:
                        body = b"".join(self.upstream_chunks(response, upstream_socket))
                        policy.record_success()
                        self.send_bytes(response.status, body, "application/json")
            finally:
                response.close()
        finally:
            connection.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Internal-only gateway pinned to Mistral Large 4.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--max-requests", type=int, default=40)
    parser.add_argument("--max-request-bytes", type=int, default=262144)
    parser.add_argument("--max-total-request-bytes", type=int, default=1500000)
    parser.add_argument("--max-response-bytes", type=int, default=16777216)
    parser.add_argument("--deadline-seconds", type=float, default=1200)
    arguments = parser.parse_args(argv)
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("mistral_api_key_required", file=sys.stderr)
        return 2
    stop = threading.Event()
    previous = {}
    try:
        policy = ModelGateway(api_key=api_key, receipt=arguments.receipt,
                              max_requests=arguments.max_requests,
                              max_request_bytes=arguments.max_request_bytes,
                              max_total_request_bytes=arguments.max_total_request_bytes,
                              max_response_bytes=arguments.max_response_bytes,
                              deadline_seconds=arguments.deadline_seconds)
        with GatewayServer((arguments.host, arguments.port), policy) as server:
            for number in (signal.SIGINT, signal.SIGTERM):
                previous[number] = signal.signal(number, lambda *_: stop.set())
            server.timeout = 0.2
            while not stop.is_set() and policy.time_left() > 0:
                server.handle_request()
        return 0
    except Exception:
        print("gateway_failed", file=sys.stderr)
        return 1
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


if __name__ == "__main__":
    raise SystemExit(main())

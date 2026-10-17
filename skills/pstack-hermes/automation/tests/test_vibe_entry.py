"""Offline policy/entry tests. Fixtures are synthetic, never inference evidence."""
from __future__ import annotations

import importlib.util
import io
from contextlib import redirect_stdout, redirect_stderr
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import os
import tomllib
import unittest
from unittest.mock import patch


AUTOMATION = Path(__file__).resolve().parents[1]
MODEL = "mistral-large-4"
GATEWAY = "http://model-gateway:8080/v1"


def entry_module():
    path = AUTOMATION / "vibe_entry.py"
    if not path.is_file():
        raise AssertionError("trusted Vibe entry is missing")
    spec = importlib.util.spec_from_file_location("updater_vibe_entry", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def export_fixture():
    """Synthetic schema-1 export: only a validator test, not run evidence."""
    cfg = tomllib.loads((AUTOMATION / "vibe-config.toml").read_text())
    cfg["models"] = {model["alias"]: model for model in cfg["models"]}
    # The release appends defaults. A sole raw/effective model-list check is wrong.
    cfg["models"]["default-medium"] = {"alias": "default-medium", "name": "mistral-vibe-cli-latest", "provider": "mistral"}
    return {"schema_version": 1, "vibe_version": "2.26.1", "outcome": "finished",
            "exit_code": 0, "error": None, "session_id": "synthetic-test-session",
            "usage": {"input_tokens": 12, "output_tokens": 4, "cached_input_tokens": 0, "total_tokens": 16},
            "cost_usd": 0.01, "config": cfg,
            "limits": {"max_turns": 40, "max_price": 2, "max_tokens": 150000, "time_limit_s": 900}}


class ExportTests(unittest.TestCase):
    def test_failure_stage_reflects_only_closed_exit_matched_outcomes(self):
        entry = entry_module()
        self.assertTrue(callable(getattr(entry, "failure_stage", None)), "missing bounded Vibe stop reason")
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            path = Path(tmp) / "export.json"
            self.assertEqual(entry.failure_stage(path, 3), "vibe")
            for outcome, code in (("token_limit", 3), ("turn_limit", 3), ("price_limit", 3),
                                  ("deadline", 3), ("length", 3), ("refusal", 3),
                                  ("terminated", 3), ("infrastructure_failure", 2),
                                  ("config_error", 1), ("usage_error", 1), ("aborted", 4)):
                payload = export_fixture() | {"outcome": outcome, "exit_code": code,
                                               "error": {"message": "PRIVATE ERROR CANARY"}}
                path.write_text(json.dumps(payload))
                self.assertEqual(entry.failure_stage(path, code), "vibe-" + outcome)
                self.assertEqual(entry.failure_stage(path, 99), "vibe")
            for mutation in ({"outcome": "PRIVATE OUTCOME CANARY"}, {"outcome": []},
                             {"outcome": "finished"}, {"schema_version": True},
                             {"vibe_version": "untrusted"}, {"exit_code": True}):
                path.write_text(json.dumps(export_fixture() | {"outcome": "token_limit", "exit_code": 3} | mutation))
                self.assertEqual(entry.failure_stage(path, 3), "vibe")
            path.write_text('{"outcome":"token_limit","outcome":"PRIVATE CANARY"}')
            self.assertEqual(entry.failure_stage(path, 3), "vibe")

    def test_export_reader_rejects_duplicates_nonfinite_json_and_nonregular_files(self):
        entry = entry_module()
        self.assertTrue(hasattr(entry, "read_export"), "strict export reader is missing")
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            root = Path(tmp)
            path = root / "export.json"
            path.write_text(json.dumps(export_fixture()))
            self.assertEqual(entry.read_export(path)["outcome"], "finished")
            for text in ('{"outcome":"finished","outcome":"refusal"}', '{"extra":NaN}', '{"extra":Infinity}'):
                path.write_text(text)
                with self.subTest(json=text), self.assertRaises(ValueError):
                    entry.read_export(path)
            path.unlink()
            path.symlink_to(root / "elsewhere")
            with self.assertRaises((ValueError, OSError)):
                entry.read_export(path)
            path.unlink()
            os.mkfifo(path)
            with self.assertRaises(ValueError):
                entry.read_export(path)

    def test_export_gate_requires_real_completion_and_exact_budgets(self):
        entry = entry_module()
        good = export_fixture()
        entry.validate_export(good, 0)
        for code in (1, 2, 3, 4, -9):
            with self.subTest(process_exit_code=code), self.assertRaises(ValueError):
                entry.validate_export(good, code)
        mutations = [("schema_version", 2), ("schema_version", True),
                     ("vibe_version", "2.26.0"), ("exit_code", 3), ("exit_code", False),
                     ("session_id", None), ("session_id", "  "), ("usage", None),
                     ("error", {"message": "failed"}), ("warnings", ""),
                     ("limits", {}), ("cost_usd", float("nan"))]
        mutations += [("outcome", outcome) for outcome in
                      ("turn_limit", "token_limit", "price_limit", "deadline", "terminated",
                       "length", "refusal", "config_error", "infrastructure_failure", "aborted")]
        for name, value in mutations:
            bad = json.loads(json.dumps(good))
            bad[name] = value
            with self.subTest(field=name, value=value), self.assertRaises(ValueError):
                entry.validate_export(bad, 0)
        for name, value in (("max_turns", 41), ("max_price", 5), ("max_tokens", 250000),
                            ("time_limit_s", 901), ("max_turns", True)):
            bad = json.loads(json.dumps(good))
            bad["limits"][name] = value
            with self.subTest(limit=name), self.assertRaises(ValueError):
                entry.validate_export(bad, 0)
        for usage in ({"input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0, "total_tokens": 0},
                      {"input_tokens": -1, "output_tokens": 4, "cached_input_tokens": 0, "total_tokens": 3},
                      {"input_tokens": 12, "output_tokens": 4, "cached_input_tokens": 0, "total_tokens": 9}):
            bad = json.loads(json.dumps(good))
            bad["usage"] = usage
            with self.subTest(usage=usage), self.assertRaises(ValueError):
                entry.validate_export(bad, 0)
        for empty in (None, []):
            good["warnings"] = empty
            entry.validate_export(good, 0)

    def test_export_gate_requires_a_pinned_route_not_just_an_alias(self):
        entry = entry_module()
        good = export_fixture()
        self.assertEqual(entry.validate_export(good, 0)["model"], MODEL)
        mutations = [
            (("config", "active_model"), "unknown"),
            (("config", "active_model"), ""),
            (("config", "allowed_models"), []),
            (("config", "allowed_models"), ["missing-filter"]),
            (("config", "models", MODEL, "alias"), "mistral-large-latest"),
            (("config", "models", MODEL, "name"), "mistral-large-latest"),
            (("config", "models", MODEL, "provider"), "generic"),
            (("config", "models", MODEL, "thinking"), "off"),
            (("config", "models", MODEL, "thinking"), "high"),
            (("config", "compaction_model", "thinking"), "off"),
            (("config", "vision_model", "thinking"), "off"),
            (("config", "providers", 0, "backend"), "generic"),
            (("config", "providers", 0, "api_base"), "https://api.mistral.ai/v1"),
            (("config", "providers", 0, "api_key_env_var"), "REAL_KEY"),
            (("config", "compaction_model", "name"), "other-model"),
            (("config", "session_logging", "generate_titles"), True),
            (("config", "enable_subagents"), True),
            (("config", "tools", "bash", "permission"), "always"),
            (("warnings",), [{"message": "falling back"}]),
        ]
        for path, value in mutations:
            with self.subTest(path=path, value=value):
                bad = json.loads(json.dumps(good))
                parent = bad
                for key in path[:-1]:
                    parent = parent[key]
                parent[path[-1]] = value
                with self.assertRaises(ValueError):
                    entry.validate_export(bad, 0)


class IsolationTests(unittest.TestCase):
    def test_staging_rejects_nested_agent_controls_symlinks_and_special_files(self):
        entry = entry_module()
        self.assertTrue(hasattr(entry, "validate_staging"), "sanitized staging gate is missing")
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            work = Path(tmp)
            for name in ("old-upstream", "new-upstream", "current-hermes", "candidate"):
                (work / name).mkdir()
            (work / "candidate" / "SKILL.md").write_text("source is inert data")
            entry.validate_staging(work)
            for name in (".vibe", ".agents", ".git", "AGENTS.md", "agents.MD"):
                canary = work / "new-upstream" / name
                canary.write_text("CONTROL CANARY")
                with self.subTest(control=name), self.assertRaises(ValueError):
                    entry.validate_staging(work)
                canary.unlink()
            canary = work / "candidate" / "link"
            canary.symlink_to("/policy/task.txt")
            with self.assertRaises(ValueError):
                entry.validate_staging(work)
            canary.unlink()
            os.mkfifo(canary)
            with self.assertRaises(ValueError):
                entry.validate_staging(work)

    def test_environment_is_fixed_and_rejects_overrides_or_credentials(self):
        entry = entry_module()
        self.assertTrue(hasattr(entry, "clean_environment"), "environment gate is missing")
        env = {"HOME": "/state/home", "VIBE_HOME": "/state/vibe", "PATH": "/usr/local/bin:/usr/bin:/bin"}
        cleaned = entry.clean_environment(env)
        self.assertEqual(cleaned["HOME"], "/state/home")
        self.assertEqual(cleaned["VIBE_HOME"], "/state/vibe")
        self.assertEqual(cleaned["MISTRAL_API_KEY"], "gateway-only-not-a-provider-key")
        for name, value in (("VIBE_ACTIVE_MODEL", "other-model"), ("VIBE_CONFIG", "/work/config"),
                            ("GH_TOKEN", "canary-not-secret"), ("GITHUB_TOKEN", "canary-not-secret"),
                            ("MISTRAL_API_KEY", "canary-not-secret"), ("HOME", "/work"),
                            ("VIBE_HOME", "/work/.vibe"), ("HTTPS_PROXY", "http://attacker"),
                            ("PYTHONPATH", "/work"), ("LD_PRELOAD", "/work/lib.so")):
            with self.subTest(variable=name), self.assertRaises(ValueError):
                entry.clean_environment({**env, name: value})

    def test_fresh_home_copies_only_trusted_policy(self):
        entry = entry_module()
        self.assertTrue(hasattr(entry, "prepare_home"), "fresh policy installation is missing")
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            state = Path(tmp) / "state"
            state.mkdir()
            entry.prepare_home(AUTOMATION, state)
            self.assertEqual((state / "vibe/config.toml").read_bytes(),
                             (AUTOMATION / "vibe-config.toml").read_bytes())
            self.assertEqual((state / "vibe/agents/updater-writer.toml").read_bytes(),
                             (AUTOMATION / "vibe-agent.toml").read_bytes())
            self.assertEqual(list((state / "home").iterdir()), [])
            with self.assertRaises((ValueError, FileExistsError)):
                entry.prepare_home(AUTOMATION, state)

    def test_exact_released_cli_has_no_approval_or_model_override(self):
        entry = entry_module()
        self.assertTrue(hasattr(entry, "build_command"), "real CLI command is missing")
        self.assertEqual(entry.build_command(), [
            "/usr/local/bin/vibe", "--experimental-harness", "--trust", "--workdir", "/work",
            "--agent", "updater-writer", "--prompt-file", "/policy/task.txt",
            "--enabled-tools", "read_file", "--enabled-tools", "write_file",
            "--enabled-tools", "edit", "--enabled-tools", "grep",
            "--max-turns", "40", "--max-price", "2", "--max-tokens", "150000",
            "--time-limit", "900", "--output", "json", "--output-dir", "/state/evidence"])


class LifecycleTests(unittest.TestCase):
    def test_worker_preserves_process_failure_and_never_publishes_raw_cli_output(self):
        entry = entry_module()
        self.assertTrue(hasattr(entry, "run_worker"), "container lifecycle is missing")
        for role, cli_code, outcome, expected in (("writer", 3, "finished", 3),
                                                 ("reviewer", 3, "token_limit", 3),
                                                 ("reviewer", 3, "PRIVATE OUTCOME CANARY", 3),
                                                 ("reviewer", 0, "refusal", 1),
                                                 ("writer", 0, "finished", 0)):
            with self.subTest(role=role, code=cli_code, outcome=outcome):
                with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
                    root = Path(tmp)
                    work, state, policy = root / "work", root / "state", root / "policy"
                    for path in (work, state, policy):
                        path.mkdir()
                    for name in ("old-upstream", "new-upstream", "current-hermes", "candidate"):
                        (work / name).mkdir()
                    for name in ("vibe-config.toml", "vibe-agent.toml"):
                        (policy / name).write_bytes((AUTOMATION / name).read_bytes())
                    (policy / "task.txt").write_text("Trusted synthetic test prompt; no model turn.")
                    payload = export_fixture()
                    payload["outcome"] = outcome
                    if cli_code:
                        payload["exit_code"] = cli_code

                    def fake_cli(command, **kwargs):
                        self.assertEqual(command, entry.build_command())
                        self.assertEqual(kwargs["cwd"], work)
                        self.assertEqual(kwargs["timeout"], 960)
                        self.assertEqual(kwargs["env"]["MISTRAL_API_KEY"], "gateway-only-not-a-provider-key")
                        kwargs["stdout"].write(b"PRIVATE RAW STDOUT CANARY")
                        kwargs["stderr"].write(b"PRIVATE RAW STDERR CANARY")
                        (state / "evidence").mkdir()
                        (state / "evidence/export.json").write_text(json.dumps(payload))
                        return subprocess.CompletedProcess(command, cli_code)

                    async def offline_preflight(*args):
                        print("PRIVATE PYTHON PREFLIGHT CANARY")
                        os.write(1, b"PRIVATE NATIVE STDOUT CANARY")
                        os.write(2, b"PRIVATE NATIVE STDERR CANARY")
                        return {"model": MODEL}

                    stdout, stderr = io.StringIO(), io.StringIO()
                    with patch.dict(os.environ, {}, clear=True), \
                            patch.object(entry, "native_preflight", side_effect=offline_preflight), \
                            patch.object(entry.subprocess, "run", side_effect=fake_cli), \
                            redirect_stdout(stdout), redirect_stderr(stderr):
                        code = entry.run_worker(role, policy=policy, work=work, state=state)
                    self.assertEqual(code, expected)
                    status = json.loads(stdout.getvalue())
                    self.assertEqual(status["exit_code"], expected)
                    self.assertEqual(status["ok"], expected == 0)
                    self.assertEqual(status["role"], role)
                    if cli_code == 3 and outcome == "token_limit":
                        self.assertEqual(status["stage"], "vibe-token_limit")
                    self.assertNotIn("CANARY", stdout.getvalue() + stderr.getvalue())
                    self.assertIn(b"STDOUT CANARY", (state / "local/vibe.stdout").read_bytes())
                    self.assertIn(b"STDERR CANARY", (state / "local/vibe.stderr").read_bytes())
                    private = (state / "local/preflight.log").read_text()
                    self.assertIn("PRIVATE NATIVE STDOUT CANARY", private)
                    self.assertIn("PRIVATE NATIVE STDERR CANARY", private)
                    self.assertIn("PRIVATE PYTHON PREFLIGHT CANARY", private)

    def test_entry_cli_rejects_contamination_before_touching_mounts(self):
        result = subprocess.run([sys.executable, "-I", str(AUTOMATION / "vibe_entry.py"), "--role", "reviewer"],
                                env={"PATH": "/usr/local/bin:/usr/bin:/bin", "GH_TOKEN": "SYNTHETIC CANARY"},
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        status = json.loads(result.stdout)
        self.assertEqual(status, {"schema": 1, "role": "reviewer", "ok": False,
                                  "exit_code": 1, "stage": "startup"})
        self.assertEqual(result.stderr, "")
        self.assertNotIn("CANARY", result.stdout)


class NativePreflightTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("vibe"), "requires pinned Vibe wheel")
    def test_native_preflight_compiles_gateway_route_and_denies_shell_offline(self):
        entry = entry_module()
        self.assertTrue(hasattr(entry, "native_preflight"), "actual native preflight is missing")
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            root = Path(tmp)
            work, state = root / "work", root / "state"
            work.mkdir()
            state.mkdir()
            for name in ("old-upstream", "new-upstream", "current-hermes", "candidate"):
                (work / name).mkdir()
            entry.prepare_home(AUTOMATION, state)
            code = '''
import asyncio, importlib.util, json, socket, sys
from pathlib import Path
connections = []
def deny(*a, **k):
    connections.append("connection attempted")
    raise AssertionError("network forbidden")
socket.socket.connect = socket.socket.connect_ex = deny
spec = importlib.util.spec_from_file_location("entry", sys.argv[1])
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)
from unittest.mock import patch
import mistralai_vibe_local_harness.vibe._local_actions as local_actions
adapters = []
original_executor = local_actions.build_local_action_executor
def capture_adapter(adapter):
    adapters.append(adapter)
    return original_executor(adapter)
with patch.object(local_actions, "build_local_action_executor", side_effect=capture_adapter):
    result = asyncio.run(entry.native_preflight(Path.cwd(), Path(sys.argv[2])))
assert not connections
assert result["model"] == "mistral-large-4"
assert result["base_url"] == "http://model-gateway:8080/v1"
assert result["native_config_compiled"] and result["native_shell_denied"]
assert result.get("review_report_write_allowed") is True, "review report outside /work must be explicitly allowed"
assert result.get("runtime_config_write_denied") is True, "model cannot change its own runtime policy"
assert result["external_hooks"] == 0
import httpx
from mistralai_vibe_local_harness.vibe._credentials import ProviderCredentialSnapshot
from mistralai_vibe_local_harness.vibe.adapters import mistral as mistral_adapter
requests = []
def provider_reply(request):
    requests.append(json.loads(request.content))
    return httpx.Response(200, json={
        "id": "offline-serialization-only", "object": "chat.completion", "created": 0,
        "model": "mistral-large-4", "choices": [{"index": 0, "finish_reason": "stop",
        "message": {"role": "assistant", "content": "synthetic offline response"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
real_client = httpx.AsyncClient
def offline_client(**kwargs):
    return real_client(**kwargs, transport=httpx.MockTransport(provider_reply))
with patch.object(mistral_adapter.httpx, "AsyncClient", side_effect=offline_client):
    adapter = adapters[0]
    asyncio.run(mistral_adapter.execute_mistral_completion(
        [], [], adapter, ProviderCredentialSnapshot(token="offline-dummy", headers={}, revision="offline"),
        adapter.active_model, stream=False))
assert len(requests) == 1
assert requests[0].get("reasoning_effort") == "none", "thinking must explicitly disable provider reasoning"
assert requests[0]["max_tokens"] == 150000, "Unified forwards its session cap; the gateway separately clamps to 8192"
assert requests[0]["model"] == "mistral-large-4"
assert not connections
print(json.dumps(result))
'''
            result = subprocess.run([sys.executable, "-I", "-c", code, str(AUTOMATION / "vibe_entry.py"),
                                     str(state / "vibe")], cwd=work,
                                    env={"HOME": str(state / "home"), "VIBE_HOME": str(state / "vibe"),
                                         "VIBE_TEST_DISABLE_KEYRING": "1", "PATH": "/usr/local/bin:/usr/bin:/bin"},
                                    capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            result_data = json.loads(result.stdout.splitlines()[-1])
            self.assertEqual(result_data["backend"], "mistral")
            self.assertTrue(result_data["native_shell_denied"])


class ImageTests(unittest.TestCase):
    def test_worker_image_checks_release_wheel_hash_and_runs_nonroot(self):
        path = AUTOMATION / "Dockerfile.worker"
        self.assertTrue(path.is_file(), "pinned worker image is missing")
        image = path.read_text()
        self.assertIn("FROM python:3.14-slim", image)
        self.assertIn("mistral-vibe==2.26.1", image)
        self.assertIn("1ceb43e38a2e82cb8c54e1032b011874f8422e998cf87b4a3fdf58704133de55", image)
        self.assertIn("hashlib.sha256", image)
        self.assertIn("--no-deps", image)
        self.assertIn("--only-binary=:all:", image)
        self.assertIn("USER 1000:1000", image)
        self.assertIn('ENTRYPOINT ["python", "-I", "/policy/vibe_entry.py"]', image)
        self.assertNotIn("COPY .", image)
        self.assertNotIn("ARG MISTRAL_API_KEY", image)


class PolicyTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("vibe"), "requires pinned Vibe wheel")
    def test_static_policy_loads_in_the_real_released_schema(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            code = '''
import socket, sys, tomllib
socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network forbidden"))
from vibe.core.config.vibe_schema import VibeConfigSchema
from vibe.core.config.harness_files import init_harness_files_manager
init_harness_files_manager("user", "project")
raw = tomllib.loads(open(sys.argv[1]).read())
assert not set(raw) - set(VibeConfigSchema.model_fields)
cfg = VibeConfigSchema.model_validate(raw)
assert not cfg.validation_warnings
assert cfg.get_active_model().name == "mistral-large-4"
assert cfg.get_compaction_model().name == "mistral-large-4"
bad = cfg.model_dump()
bad["active_model"] = "__unavailable_pin_for_offline_negative_test__"
fallback = VibeConfigSchema.model_validate(bad)
assert fallback.active_model == "" and fallback.validation_warnings, "released fallback hazard changed"
'''
            result = subprocess.run([sys.executable, "-I", "-c", code, str(AUTOMATION / "vibe-config.toml")],
                                    env={"HOME": tmp, "VIBE_HOME": tmp + "/vibe",
                                         "VIBE_TEST_DISABLE_KEYRING": "1", "PATH": "/usr/bin:/bin"},
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_static_policy_pins_the_route_and_disables_secondary_effects(self):
        config_path = AUTOMATION / "vibe-config.toml"
        agent_path = AUTOMATION / "vibe-agent.toml"
        self.assertTrue(config_path.is_file(), "trusted Vibe config is missing")
        self.assertTrue(agent_path.is_file(), "trusted Vibe agent is missing")
        cfg = tomllib.loads(config_path.read_text())
        self.assertEqual(cfg["active_model"], MODEL)
        self.assertEqual(cfg["allowed_models"], [MODEL])
        for name in ("compaction_model", "vision_model"):
            self.assertEqual(cfg[name]["name"], MODEL)
            self.assertEqual(cfg[name]["alias"], MODEL)
            self.assertEqual(cfg[name]["provider"], "mistral")
        self.assertEqual(cfg["auto_compact_threshold"], 0)
        self.assertEqual(cfg["providers"], [{
            "name": "mistral", "backend": "mistral", "api_base": GATEWAY,
            "api_key_env_var": "MISTRAL_API_KEY", "api_style": "openai",
        }])
        self.assertEqual(len(cfg["models"]), 1)
        self.assertEqual({k: cfg["models"][0][k] for k in ("alias", "name", "provider")},
                         {"alias": MODEL, "name": MODEL, "provider": "mistral"})
        self.assertEqual(cfg["models"][0]["auto_compact_threshold"], 0)
        self.assertEqual(cfg["enabled_tools"], ["read_file", "write_file", "edit", "grep"])
        for name in ("bash", "git_bash", "powershell"):
            self.assertEqual(cfg["tools"][name]["permission"], "never")
            self.assertEqual(cfg["tools"][name]["denylist"], ["*"])
        for flag in ("bypass_tool_permissions", "enable_subagents", "enable_background_processes",
                     "managed_shell_tools_enabled", "enable_connectors", "enable_telemetry",
                     "enable_otel", "enable_update_checks", "enable_auto_update",
                     "enable_notifications", "include_project_context",
                     "experimental_enable_registry_skills", "experimental_enable_model_catalog"):
            self.assertIs(cfg[flag], False, flag)
        self.assertIs(cfg["experiments"]["enable"], False)
        self.assertIs(cfg["session_logging"]["generate_titles"], False)
        self.assertEqual(cfg["utility_models"], {"title": "active", "smart_approve": "active"})
        self.assertEqual(cfg["disabled_skills"], ["*"])
        for name in ("mcp_servers", "tool_paths", "skill_paths", "agent_paths"):
            self.assertEqual(cfg[name], [])
        agent = tomllib.loads(agent_path.read_text())
        self.assertEqual(agent["safety"], "neutral")
        self.assertEqual(agent["agent_type"], "agent")
        self.assertIn("untrusted data", agent["instructions"])


if __name__ == "__main__":
    unittest.main()

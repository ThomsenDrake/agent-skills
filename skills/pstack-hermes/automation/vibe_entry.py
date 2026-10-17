"""Fail-closed entry for the pinned Vibe worker (stdlib control code, Python >=3.12).

/work and /policy are sanitized read-only mounts. Only /work/candidate (writer)
or /out (reviewer), plus capped /state, may be writable. The host enforces the
mounts/egress and verifies a separate gateway receipt; worker evidence is not a
server attestation. Never publish the raw CLI logs or session journal.
"""
from __future__ import annotations

import argparse
import asyncio
from collections.abc import Mapping
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tomllib
import traceback
from typing import Any


VIBE_VERSION = "2.26.1"
MODEL = "mistral-large-4"
GATEWAY = "http://model-gateway:8080/v1"
AGENT = "updater-writer"
FILE_TOOLS = ("read_file", "write_file", "edit", "grep")
DISABLED_FLAGS = (
    "bypass_tool_permissions", "enable_subagents", "enable_background_processes",
    "managed_shell_tools_enabled", "enable_connectors", "enable_telemetry",
    "enable_otel", "enable_update_checks", "enable_auto_update",
    "enable_notifications", "include_project_context",
    "experimental_enable_registry_skills", "experimental_enable_model_catalog",
)
LIMITS = {"max_turns": 40, "max_price": 2, "max_tokens": 150000, "time_limit_s": 900}


def _require(condition: bool, message: str) -> None:
    if not condition:
        # Only trusted constant messages: no config, source text, or env values.
        raise ValueError(message)


def validate_config(config: Any) -> dict[str, str]:
    """Validate the released alias-keyed effective config, not just raw TOML."""
    _require(type(config) is dict, "missing effective config")
    try:
        _require(config["active_model"] == MODEL, "active model pin changed")
        _require(config["allowed_models"] == [MODEL], "allowed model pin changed")
        models = config["models"]
        _require(type(models) is dict, "effective models must be alias-keyed")
        model = models[MODEL]
        for field, expected in (("alias", MODEL), ("name", MODEL), ("provider", "mistral"), ("thinking", "low")):
            _require(model[field] == expected, "model route changed")
        # Vibe appends defaults; only models with the exact allowed API name
        # are available. More than one matching alias is not this policy.
        _require([alias for alias, item in models.items() if item["name"] == MODEL] == [MODEL],
                 "available model route is not unique")
        providers = [item for item in config["providers"] if item["name"] == "mistral"]
        _require(len(providers) == 1, "provider route is not unique")
        provider = providers[0]
        for field, expected in (("backend", "mistral"), ("api_base", GATEWAY),
                                ("api_key_env_var", "MISTRAL_API_KEY"), ("api_style", "openai")):
            _require(provider[field] == expected, "provider route changed")
        _require(not provider.get("extra_headers"), "provider headers are forbidden")
        for name in ("compaction_model", "vision_model"):
            secondary = config[name]
            _require(all(secondary[field] == expected for field, expected in
                         (("alias", MODEL), ("name", MODEL), ("provider", "mistral"), ("thinking", "low"))),
                     "secondary model route changed")
        _require(config["utility_models"] == {"title": "active", "smart_approve": "active"},
                 "utility model route changed")
        _require(config["auto_compact_threshold"] == model["auto_compact_threshold"] == 0,
                 "automatic compaction is forbidden")
        _require(model["max_output_tokens"] == 8192, "output token bound changed")
        for flag in DISABLED_FLAGS:
            _require(config[flag] is False, "disabled feature was enabled")
        _require(config["experiments"]["enable"] is False, "experiments are forbidden")
        _require(config["session_logging"]["generate_titles"] is False, "titles are forbidden")
        _require(config["enabled_tools"] == list(FILE_TOOLS), "file tool policy changed")
        _require(config["disabled_skills"] == ["*"], "skills are forbidden")
        for name in ("mcp_servers", "tool_paths", "agent_paths", "skill_paths"):
            _require(config[name] == [], "external extension paths are forbidden")
        _require(config["default_agent"] == AGENT and config["enabled_agents"] == [AGENT],
                 "agent policy changed")
        for name in FILE_TOOLS:
            _require(config["tools"][name]["permission"] == "always", "file permission changed")
        for name in ("read_file", "write_file", "edit"):
            file_config = config["tools"][name]
            _require(file_config["allowlist"] == ["/out/audit.json"], "review file grant changed")
            expected_denials = ["/state", "/state/*"]
            if name != "read_file":
                expected_denials += ["/policy", "/policy/*"]
            _require(file_config["denylist"] == expected_denials, "runtime file denial changed")
        for name in ("bash", "git_bash", "powershell"):
            shell = config["tools"][name]
            _require(shell["permission"] == "never" and shell["denylist"] == ["*"],
                     "shell permission changed")
        _require(not config.get("validation_warnings"), "configuration warning")
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("malformed effective config") from exc
    return {"alias": MODEL, "model": MODEL, "provider": "mistral", "backend": "mistral",
            "base_url": GATEWAY, "vibe_version": VIBE_VERSION}


def clean_environment(incoming: Mapping[str, str]) -> dict[str, str]:
    """Reject contamination, then pass only fixed nonsecret worker settings."""
    fixed = {"HOME": "/state/home", "VIBE_HOME": "/state/vibe",
             "MISTRAL_API_KEY": "gateway-only-not-a-provider-key",
             "PATH": "/usr/local/bin:/usr/bin:/bin", "TMPDIR": "/state/tmp",
             "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
             "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"}
    _require(set(incoming) <= set(fixed) | {"HOSTNAME", "TERM", "VIBE_TEST_DISABLE_KEYRING"},
             "worker environment is not allowlisted")
    for name in ("HOME", "VIBE_HOME", "MISTRAL_API_KEY", "TMPDIR"):
        _require(name not in incoming or incoming[name] == fixed[name], "worker environment override")
    if "VIBE_TEST_DISABLE_KEYRING" in incoming:
        _require(incoming["VIBE_TEST_DISABLE_KEYRING"] == "1", "invalid keyring test override")
        fixed["VIBE_TEST_DISABLE_KEYRING"] = "1"
    return fixed


def validate_staging(work: Path) -> None:
    """Reject discovery/control names anywhere, before --trust is permitted."""
    _require(work.is_dir() and not work.is_symlink(), "invalid staging root")
    expected = {"old-upstream", "new-upstream", "current-hermes", "candidate"}
    _require({path.name for path in work.iterdir()} == expected, "invalid staging layout")
    for name in expected:
        _require((work / name).is_dir(), "missing staging snapshot")
    count = 0
    stack = [work]
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as entries:
            for item in entries:
                count += 1
                _require(count <= 20000, "staging entry limit exceeded")
                _require(item.name.casefold() not in {".vibe", ".agents", ".git", "agents.md"},
                         "staged control file is forbidden")
                info = item.stat(follow_symlinks=False)
                _require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode),
                         "nonregular staged path")
                if stat.S_ISDIR(info.st_mode):
                    child = Path(item.path)
                    _require(len(child.relative_to(work).parts) <= 32, "staging depth limit exceeded")
                    stack.append(child)
                else:
                    _require(info.st_nlink == 1, "hardlinked staged file")


def prepare_home(policy: Path, state: Path) -> None:
    """Never reuse a live home, project config, keyring, hooks, or plugins."""
    (state / "home").mkdir(mode=0o700)
    home = state / "vibe"
    home.mkdir(mode=0o700)
    (home / "agents").mkdir(mode=0o700)
    shutil.copyfile(policy / "vibe-config.toml", home / "config.toml")
    shutil.copyfile(policy / "vibe-agent.toml", home / "agents" / (AGENT + ".toml"))


def build_command() -> list[str]:
    command = ["/usr/local/bin/vibe", "--experimental-harness", "--trust", "--workdir", "/work",
               "--agent", AGENT, "--prompt-file", "/policy/task.txt"]
    for name in FILE_TOOLS:
        command.extend(["--enabled-tools", name])
    command.extend(["--max-turns", "40", "--max-price", "2", "--max-tokens", "150000",
                    "--time-limit", "900", "--output", "json", "--output-dir", "/state/evidence"])
    return command


async def native_preflight(work: Path, vibe_home: Path) -> dict:
    """Compile the actual 2.26.1 Unified route. No turn or inference is sent.

    The four CLI filters are Python ToolManager policy, NOT a claim of four
    model-facing legacy tools. Unified advertises native capabilities and does
    not advertise grep in this release. Check native shell/process denial too.
    """
    validate_staging(work)
    _require(importlib.metadata.version("mistral-vibe") == VIBE_VERSION, "Vibe package pin changed")
    raw = tomllib.loads((vibe_home / "config.toml").read_text(encoding="utf-8"))
    _require(type(raw.get("models")) is list and len(raw["models"]) == 1, "raw model pin changed")
    raw_effective = {**raw, "models": {item["alias"]: item for item in raw["models"]}}
    validate_config(raw_effective)
    from vibe.core.config.vibe_schema import VibeConfigSchema
    from vibe.core.config.harness_files import get_harness_files_manager, init_harness_files_manager
    from vibe.core.hooks.config import load_hooks_from_fs
    from vibe.core.trusted_folders import trusted_folders_manager
    from vibe.core.tools.manager import ToolManager, NoSuchToolError
    from vibe.core.tools.models import ToolPermission
    from vibe.core.agents.manager import AgentManager
    from vibe.app_server._runtime import HarnessProcess, ToolGate, _rust_tool_modes
    from vibe.app_server.protocol import SessionOptions
    from vibe.app_server._unified_harness_backend_adapter import UnifiedSessionSettings
    from mistralai_vibe_local_harness import HarnessSession
    from mistralai_vibe_local_harness.vibe._local_actions import build_local_action_executor
    from mistralai_vibe_local_harness.protocol import RustRuntimeBuiltinToolCallAction, RustRuntimeBuiltinToolCall

    _require(not (set(raw) - set(VibeConfigSchema.model_fields)), "unknown raw config fields")
    trusted_folders_manager.trust_for_session(work)
    init_harness_files_manager("user", "project")
    manager = get_harness_files_manager()
    _require(manager.load_project_docs() == [] and manager.load_user_doc() == "",
             "automatic instruction discovery is forbidden")
    hooks = load_hooks_from_fs(harness_files=manager)
    _require(not hooks.hooks and not hooks.runtime_hooks and not hooks.issues, "external hooks are forbidden")
    for directory in (manager.project_tools_dirs + manager.user_tools_dirs
                      + manager.project_plugins_dirs + manager.user_plugins_dirs):
        _require(not any(directory.iterdir()), "external plugins and tools are forbidden")
    process = HarnessProcess(manager, experimental_harness=True)
    try:
        context = await process.build_unified_session_context(
            SessionOptions(cwd=str(work), agent=AGENT, headless=True, trust_workspace=True,
                           max_turns=LIMITS["max_turns"]), require_api_key=False)
        cfg = context.config_orchestrator.config
        bindings = validate_config(cfg.model_dump(mode="json"))
        _require(not cfg.validation_warnings, "native configuration warning")
        model, provider = cfg.get_active_model(), cfg.get_active_provider()
        _require(cfg.active_model == model.alias == model.name == MODEL, "native model fallback")
        _require(provider.name == provider.backend == "mistral" and provider.api_base == GATEWAY
                 and provider.api_key_env_var == "MISTRAL_API_KEY", "native provider fallback")
        _require(list(cfg.available_models()) == [MODEL]
                 and cfg.available_models()[MODEL].name == MODEL, "native available models changed")
        _require(cfg.get_compaction_model().name == MODEL, "native secondary model fallback")
        agents = AgentManager(context.config_orchestrator, AGENT, harness_files=manager)
        profile = agents.active_profile
        _require(profile.name == AGENT and profile.safety == "neutral" and profile.agent_type == "agent"
                 and not profile.overrides, "native agent policy changed")
        tools = ToolManager(lambda: cfg, defer_mcp=True, cwd=work, harness_files=manager)
        _require(set(tools.available_tools) == set(FILE_TOOLS), "native Python tool filter changed")
        for name in FILE_TOOLS:
            _require(tools.get_tool_config(name).permission == ToolPermission.ALWAYS, "native file permission changed")
        for name in ("bash", "git_bash", "powershell"):
            shell = tools.get_tool_config(name)
            # Migrations repopulate the allowlist, including 'find'. Never rely
            # on an empty allowlist: NEVER, denylist '*', and native DENY bind it.
            _require(shell.permission == ToolPermission.NEVER and shell.denylist == ["*"],
                     "native shell permission changed")
        for name in ("bash", "git_bash", "powershell", "task", "skill", "web_fetch", "web_search"):
            try:
                tools.get(name)
            except NoSuchToolError:
                continue
            raise ValueError("forbidden native Python tool")
        from vibe.core.tools.builtins.write_file import WriteFileArgs
        report_permission = tools.get("write_file").resolve_permission(
            WriteFileArgs(file_path="/out/audit.json", content="{}"))
        _require(report_permission is not None and report_permission.permission == ToolPermission.ALWAYS,
                 "review report outside workdir is not allowed")
        modes = _rust_tool_modes(set(tools.available_tools),
                                 lambda name: tools.get_tool_config(name).permission,
                                 lambda name: tools.get_tool_config(name).allowlist,
                                 gate=ToolGate.PROMPT)
        derivation = context.derive(UnifiedSessionSettings(max_turns=LIMITS["max_turns"],
                                                           max_tokens=LIMITS["max_tokens"]))
        adapter = derivation.adapter_config
        _require(adapter.active_model.model == MODEL and adapter.base_url == GATEWAY,
                 "Unified model route changed")
        _require(adapter.tool_modes == modes and modes["file_system.bash"] == "deny"
                 and modes["skill.read"] == "deny"
                 and all(value == "deny" for name, value in modes.items() if name.startswith("process.")),
                 "Unified effect permissions changed")
        core_json = derivation.core_config.model_dump_json(exclude_none=True)
        core = HarnessSession.create(core_json, "[]")
        core.close()
        execute = build_local_action_executor(adapter)
        denied = await execute(RustRuntimeBuiltinToolCallAction(
            action_id="policy-shell-denial", turn_id="policy-no-inference", call_id="policy-denial",
            call=RustRuntimeBuiltinToolCall(name="file_system.bash", arguments={"command": "true"})))
        _require(denied.type == "tool_failed" and "tool_denied" in denied.model_dump_json(),
                 "native shell was not denied")
        denied_write = await execute(RustRuntimeBuiltinToolCallAction(
            action_id="policy-config-write-denial", turn_id="policy-no-inference", call_id="policy-file-denial",
            call=RustRuntimeBuiltinToolCall(name="file_system.write_file", arguments={
                "path": "/state/vibe/config.toml", "content": "DENIAL PROBE; MUST NEVER BE WRITTEN"})))
        _require(denied_write.type == "tool_failed" and "tool_denied" in denied_write.model_dump_json(),
                 "native runtime policy writes were not denied")
        return {**bindings, "native_config_compiled": True, "native_shell_denied": True,
                "review_report_write_allowed": True, "runtime_config_write_denied": True,
                "external_hooks": 0}
    finally:
        await process.close()


def validate_export(export: Any, process_exit_code: int) -> dict[str, str]:
    """Validate worker-local metadata; never substitutes for the gateway receipt."""
    _require(type(export) is dict, "missing Vibe export")
    _require(type(process_exit_code) is int and process_exit_code == 0, "Vibe process failed")
    _require(type(export.get("schema_version")) is int and export["schema_version"] == 1,
             "unsupported Vibe export schema")
    _require(export.get("vibe_version") == VIBE_VERSION, "Vibe export version changed")
    _require(export.get("outcome") == "finished", "Vibe did not finish")
    _require(type(export.get("exit_code")) is int and export["exit_code"] == 0,
             "Vibe export failed")
    _require(export.get("error") is None, "Vibe export contains an error")
    warnings = export.get("warnings")
    _require(warnings is None or type(warnings) is list and not warnings,
             "Vibe export contains warnings")
    session = export.get("session_id")
    _require(type(session) is str and bool(session.strip()), "missing inference session")
    limits = export.get("limits")
    _require(type(limits) is dict and set(limits) == set(LIMITS), "missing run limits")
    for name, expected in LIMITS.items():
        value = limits[name]
        _require(type(value) in (int, float) and value == expected, "run limit changed")
    usage = export.get("usage")
    fields = ("input_tokens", "output_tokens", "cached_input_tokens", "total_tokens")
    _require(type(usage) is dict and all(type(usage.get(name)) is int and usage[name] >= 0
                                       for name in fields), "missing or invalid usage")
    _require(usage["input_tokens"] > 0 and usage["output_tokens"] > 0
             and usage["total_tokens"] == usage["input_tokens"] + usage["output_tokens"]
             and usage["cached_input_tokens"] <= usage["input_tokens"]
             and usage["total_tokens"] <= LIMITS["max_tokens"], "invalid inference usage")
    cost = export.get("cost_usd")
    _require(type(cost) in (int, float) and math.isfinite(cost) and 0 <= cost <= LIMITS["max_price"],
             "invalid inference cost")
    return validate_config(export.get("config"))


def read_export(path: Path) -> dict:
    """Read bounded regular JSON without symlink/FIFO or parser ambiguities."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        maximum = 2 * 1024 * 1024
        _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= maximum,
                 "invalid Vibe export file")
        data = stream.read(maximum + 1)
        _require(len(data) <= maximum, "Vibe export exceeded size limit")

    def unique(pairs):
        result = {}
        for name, value in pairs:
            _require(name not in result, "duplicate Vibe export key")
            result[name] = value
        return result

    def reject_constant(value):
        raise ValueError("nonfinite Vibe export number")

    result = json.loads(data, object_pairs_hook=unique, parse_constant=reject_constant)
    _require(type(result) is dict, "invalid Vibe export document")
    return result


def failure_stage(path: Path, process_exit_code: int) -> str:
    outcomes = {"usage_error": 1, "config_error": 1, "infrastructure_failure": 2,
                "turn_limit": 3, "token_limit": 3, "price_limit": 3, "deadline": 3,
                "terminated": 3, "length": 3, "refusal": 3, "aborted": 4}
    try:
        export = read_export(path)
        outcome = export.get("outcome")
        if (type(export.get("schema_version")) is int and export["schema_version"] == 1
                and export.get("vibe_version") == VIBE_VERSION
                and type(outcome) is str and outcome in outcomes
                and type(export.get("exit_code")) is int
                and export["exit_code"] == outcomes[outcome] == process_exit_code):
            return "vibe-" + outcome
    except (OSError, ValueError):
        pass
    return "vibe"


@contextmanager
def _private_output(path: Path):
    """Capture Python AND native fd output during the offline preflight."""
    with path.open("x", encoding="utf-8") as log:
        saved = [os.dup(1), os.dup(2)]
        try:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(log.fileno(), 1)
            os.dup2(log.fileno(), 2)
            with redirect_stdout(log), redirect_stderr(log):
                try:
                    yield
                except Exception:
                    traceback.print_exc()
                    raise
        finally:
            log.flush()
            for target, fd in zip((1, 2), saved):
                os.dup2(fd, target)
                os.close(fd)


def run_worker(role: str, *, policy: Path = Path("/policy"), work: Path = Path("/work"),
               state: Path = Path("/state")) -> int:
    """Run one role. Public stdout contains only a bounded, nonsecret status.

    Mount safety, /out reviewer validation, publication, and a server-verified
    model receipt remain the trusted host controller's independent gates.
    """
    stage, exit_code = "startup", 1
    previous_cwd, previous_umask = Path.cwd(), os.umask(0o077)
    try:
        _require(role in ("writer", "reviewer"), "invalid worker role")
        environment = clean_environment(os.environ)
        os.environ.clear()
        os.environ.update(environment)
        validate_staging(work)
        _require((policy / "task.txt").is_file(), "trusted prompt is missing")
        prepare_home(policy, state)
        (state / "tmp").mkdir(mode=0o700)
        local = state / "local"
        local.mkdir(mode=0o700)
        _require(not (state / "evidence").exists(), "run evidence must be fresh")
        os.chdir(work)
        stage = "preflight"
        with _private_output(local / "preflight.log"):
            bindings = asyncio.run(native_preflight(work, state / "vibe"))
        (state / "preflight.json").write_text(json.dumps(bindings, sort_keys=True) + "\n", encoding="utf-8")
        stage = "vibe"
        with (local / "vibe.stdout").open("xb") as stdout, (local / "vibe.stderr").open("xb") as stderr:
            completed = subprocess.run(build_command(), cwd=work, env=environment,
                                       stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                       timeout=960, check=False)
        # The export is mutable worker output. It cannot turn process failure
        # into success. Preserve real Vibe error codes; encode signals as shells do.
        exit_code = completed.returncode if completed.returncode >= 0 else 128 - completed.returncode
        if exit_code == 0:
            stage = "export"
            validate_export(read_export(state / "evidence/export.json"), completed.returncode)
            validate_staging(work)
            stage = "finished"
        else:
            stage = failure_stage(state / "evidence/export.json", exit_code)
    except subprocess.TimeoutExpired:
        exit_code = 124
        stage = "timeout"
    except Exception:
        exit_code = 1
        # Deliberately do not print exception text: third-party errors can
        # contain source, prompts, response bodies, or credential-like strings.
    finally:
        os.chdir(previous_cwd)
        os.umask(previous_umask)
    print(json.dumps({"schema": 1, "role": role, "ok": exit_code == 0,
                      "exit_code": exit_code, "stage": stage}, sort_keys=True))
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pinned file-only Vibe container worker")
    parser.add_argument("--role", choices=("writer", "reviewer"), required=True)
    args = parser.parse_args(argv)
    return run_worker(args.role)


if __name__ == "__main__":
    raise SystemExit(main())

"""Secret-isolated, two-context Docker/Vibe adaptation; never applies or publishes."""
from __future__ import annotations

from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import uuid

import protocol
import run as control

POLICY = Path(__file__).resolve().parent
IMAGE = "pstack-vibe:verified"

MODEL = "mistral-large-4"
BINDINGS = {"alias": MODEL, "model": MODEL, "provider": "mistral", "backend": "mistral",
            "base_url": "http://model-gateway:8080/v1", "vibe_version": "2.26.1"}
USAGE = ("input_tokens", "output_tokens", "cached_input_tokens", "total_tokens")


def validate_run(data: dict) -> dict:
    """Validate the host helper's reduced export; never return session/config/logs."""
    _require(type(data) is dict and set(data) == {"bindings", "usage", "cost_usd"}
             and data["bindings"] == BINDINGS, "invalid run bindings")
    usage = data["usage"]
    _require(type(usage) is dict and set(usage) == set(USAGE)
             and all(type(usage[name]) is int and usage[name] >= 0 for name in USAGE), "invalid run usage")
    _require(usage["input_tokens"] > 0 and usage["output_tokens"] > 0
             and usage["total_tokens"] == usage["input_tokens"] + usage["output_tokens"] <= 150000
             and usage["cached_input_tokens"] <= usage["input_tokens"], "invalid run token accounting")
    _require(type(data["cost_usd"]) in (int, float) and 0 <= data["cost_usd"] <= 2
             and math.isfinite(data["cost_usd"]), "invalid run cost")
    return data


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_receipt(data: dict) -> dict:
    """Accept only a closed, error-free gateway route with the controller's caps."""
    fields = {"request_count", "upstream_request_count", "successful_2xx", "total_request_bytes",
              "max_request_bytes", "max_total_request_bytes", "model_ids_submitted", "errors",
              "started_at", "updated_at", "elapsed_seconds", "deadline_seconds", "status"}
    _require(type(data) is dict and set(data) == fields, "invalid gateway receipt fields")
    counts = (data[name] for name in ("request_count", "upstream_request_count", "successful_2xx"))
    _require(all(type(value) is int and 0 < value <= 40 for value in counts)
             and data["request_count"] == data["upstream_request_count"] == data["successful_2xx"],
             "gateway requests did not all succeed")
    _require(data["model_ids_submitted"] == [MODEL] and type(data["errors"]) is dict
             and not data["errors"] and data["status"] == "closed", "gateway route did not close cleanly")
    for name, expected in (("max_request_bytes", 262144), ("max_total_request_bytes", 1500000)):
        _require(type(data[name]) is int and data[name] == expected, "gateway byte cap changed")
    _require(type(data["total_request_bytes"]) is int
             and 0 < data["total_request_bytes"] <= min(1500000, 262144 * data["request_count"]),
             "invalid gateway byte accounting")
    for name in ("deadline_seconds", "elapsed_seconds"):
        _require(type(data[name]) in (int, float) and 0 <= data[name] <= 1200
                 and math.isfinite(data[name]), "invalid gateway duration")
    _require(data["deadline_seconds"] == 1200 and 0 <= data["elapsed_seconds"] <= 1200,
             "gateway deadline changed or exceeded")
    try:
        start, end = (datetime.fromisoformat(data[name]) for name in ("started_at", "updated_at"))
        _require(start.utcoffset() is not None and end.utcoffset() is not None and end >= start,
                 "invalid gateway timestamps")
    except (TypeError, ValueError):
        raise ValueError("invalid gateway timestamps") from None
    return data


EXPORT_HELPER = """import json,runpy
from pathlib import Path
try:
    policy = runpy.run_path('/policy/vibe_entry.py')
    export = policy['read_export'](Path('/state/evidence/export.json'))
    bindings = policy['validate_export'](export, 0)
    usage = {key: export['usage'][key] for key in
             ('input_tokens', 'output_tokens', 'cached_input_tokens', 'total_tokens')}
    print(json.dumps({'bindings': bindings, 'usage': usage, 'cost_usd': export['cost_usd']}, allow_nan=False))
except Exception:
    raise SystemExit('invalid worker export') from None
"""
HEALTH = ("import json,urllib.request; "
          "r=urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=2); "
          "assert r.status==200 and json.loads(r.read(1024))=="
          "{'status':'ok','model':'mistral-large-4'}")


def _json(text):
    def unique(pairs):
        result = {}
        for name, value in pairs:
            _require(name not in result, "duplicate controller JSON key")
            result[name] = value
        return result
    _require(len(text) <= 8192, "controller stdout exceeded bound")
    data = json.loads(text, object_pairs_hook=unique,
                      parse_constant=lambda _: _require(False, "nonfinite controller JSON"))
    _require(type(data) is dict, "controller stdout is not an object")
    return data


def _docker(args, *, secret=False, timeout=30, check=True):
    names = ("PATH", "HOME", "LANG", "LC_ALL", "DOCKER_HOST", "DOCKER_CONTEXT",
             "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH", "XDG_RUNTIME_DIR")
    env = {name: os.environ[name] for name in names if name in os.environ}
    if secret:
        env["MISTRAL_API_KEY"] = os.environ["MISTRAL_API_KEY"]
    result = subprocess.run(["docker", *args], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, timeout=timeout, env=env, check=False)
    _require(not check or result.returncode == 0, "Docker command failed")
    _require(len(result.stdout) <= 8192, "Docker stdout exceeded bound")
    return result


class _Owned:
    """UUID names AND ownership labels make ambiguous-create cleanup scope-safe."""
    def __init__(self):
        self.token, self.resources = "pstack-updater-" + uuid.uuid4().hex, []
        self.label = "pstack.updater=" + self.token

    def reserve(self, kind):
        name = self.token + "-" + str(len(self.resources))
        self.resources.append((kind, name))
        return name

    def cleanup(self):
        failed = False
        for kind, name in reversed(self.resources):
            field = ".Config.Labels" if kind == "container" else ".Labels"
            inspect = [kind, "inspect", "--format", '{{index ' + field + ' "pstack.updater"}}', name]
            try:
                found = _docker(inspect, check=False)
                if found.returncode == 0 and found.stdout.strip() == self.token:
                    _docker([kind, "rm", *(["--force"] if kind == "container" else []), name])
                    _require(_docker(inspect, check=False).returncode != 0, "Docker resource survived cleanup")
            except Exception:
                failed = True
        _require(not failed, "Docker cleanup failed")


def _task(role, plan, envelope, destination):
    destination.mkdir(mode=0o700)
    for name in ("vibe_entry.py", "vibe-config.toml", "vibe-agent.toml"):
        shutil.copyfile(POLICY / name, destination / name)
    paths = {name: "/work/" + name for name in ("old-upstream", "new-upstream", "current-hermes", "candidate")}
    bots = {"agents/poteto-agent.md": "bots/poteto-agent/SOUL.md",
            "agents/comment-sicko.md": "bots/comment-sicko/SOUL.md"}
    mappings = [{"source_path": source, **{name: root + "/" + (source if "upstream" in name else bots.get(source, source))
                                          for name, root in paths.items()}} for source in plan["changed_paths"]]
    task = {"role": role, "model": MODEL, "paths": paths, "allowed_paths": plan["allowed_paths"],
            "changed_sources": plan["changed_paths"], "maps": mappings, "audit_path": "/out/audit.json",
            "updates": [{key: update[key] for key in ("path", "before_sha256", "after_sha256")}
                        for update in envelope.get("updates", [])]}
    (destination / "task.txt").write_text((POLICY / (role + ".md")).read_text(encoding="utf-8")
                                          + "\n\nController task JSON:\n" + json.dumps(task, sort_keys=True), encoding="utf-8")


def _phase(role, snapshots, policy, receipts, report=None, *, progress=lambda detail: None):
    owned, uid, gid = _Owned(), os.getuid(), os.getgid()
    internal, egress = owned.reserve("network"), owned.reserve("network")
    state, gateway, keeper, worker, helper = (owned.reserve(kind) for kind in
                                              ("volume", "container", "container", "container", "container"))
    hardening = ["--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                 "--memory", "512m", "--cpus", "1", "--pids-limit", "64", "--user", f"{uid}:{gid}"]
    try:
        progress("resources")
        for name, extra in ((internal, ["--internal"]), (egress, [])):
            _docker(["network", "create", "--label", owned.label, "--driver", "bridge", *extra, name])
        _docker(["volume", "create", "--label", owned.label, "--driver", "local", "--opt", "type=tmpfs",
                 "--opt", "device=tmpfs", "--opt", f"o=size=128m,uid={uid},gid={gid},mode=0700", state])
        _docker(["container", "create", "--name", gateway, "--label", owned.label, *hardening,
                 "--network", internal, "--network-alias", "model-gateway", "--env", "MISTRAL_API_KEY",
                 "--mount", f"type=bind,src={POLICY / 'model_gateway.py'},dst=/policy/model_gateway.py,readonly",
                 "--mount", f"type=bind,src={receipts},dst=/receipts", "--entrypoint", "python", IMAGE,
                 "-I", "/policy/model_gateway.py", "--host", "0.0.0.0", "--port", "8080",
                 "--receipt", f"/receipts/{role}.json", "--max-requests", "40", "--max-request-bytes", "262144",
                 "--max-total-request-bytes", "1500000", "--max-response-bytes", "16777216",
                 "--deadline-seconds", "1200"], secret=True)
        _docker(["network", "connect", egress, gateway])
        progress("gateway")
        _docker(["start", gateway])
        for attempt in range(10):
            if _docker(["exec", gateway, "python", "-I", "-c", HEALTH], timeout=3, check=False).returncode == 0:
                break
            time.sleep(0.25)
        else:
            raise ValueError("gateway did not become healthy")
        # Local-driver tmpfs is unmounted at the last running user's exit.
        _docker(["run", "--detach", "--rm", "--name", keeper, "--label", owned.label, "--network", "none",
                 *hardening, "--mount", f"type=volume,src={state},dst=/state,readonly,volume-nocopy",
                 "--entrypoint", "python", IMAGE, "-I", "-c", "import time; time.sleep(1300)"])
        command = control.worker_command(name=worker, network=internal, policy=policy, snapshots=snapshots,
                                         state_volume=state, role=role, uid=uid, gid=gid, report_dir=report)
        command[2:2] = ["--label", owned.label]
        # Prevent image UID 1000 directory metadata from repopulating host-UID tmpfs.
        command = [arg + ",volume-nocopy" if arg.startswith("type=volume,") and "volume-nocopy" not in arg
                   else arg for arg in command]
        progress("worker")
        try:
            completed = _docker(command[1:], timeout=1100, check=False)
            status = _json(completed.stdout)
            if (set(status) == {"schema", "role", "ok", "exit_code", "stage"}
                    and type(status["schema"]) is int and status["schema"] == 1
                    and status["role"] == role and type(status["ok"]) is bool
                    and type(status["exit_code"]) is int and 0 <= status["exit_code"] <= 255
                    and status["stage"] in ("startup", "preflight", "vibe", "export", "finished", "timeout")):
                progress(f"worker.{status['stage']}.exit{status['exit_code']}")
            _require(completed.returncode == 0
                     and type(status.get("schema")) is int and type(status.get("exit_code")) is int
                     and status.get("ok") is True
                     and status == {"schema": 1, "role": role, "ok": True, "exit_code": 0, "stage": "finished"},
                     "worker did not finish successfully")
        finally:
            _docker(["stop", "--time", "30", gateway], timeout=45)
        progress("receipt")
        receipt = validate_receipt(control.read_json(receipts / (role + ".json"), maximum=8192))
        progress("export")
        result = _docker(["run", "--rm", "--name", helper, "--label", owned.label, "--network", "none",
                          *hardening, "--mount", f"type=volume,src={state},dst=/state,readonly",
                          "--entrypoint", "python", IMAGE, "-I", "-c", EXPORT_HELPER], timeout=60)
        return receipt, validate_run(_json(result.stdout))
    finally:
        owned.cleanup()


def adapt(repo: Path, wrapper: dict, out: Path) -> dict:
    """Return the raw reviewed packet and atomically write ONLY out/candidate.json.

    out must be new and outside repo. No apply(), checkpoint, Git write or publication.
    Docker and provider failures emit only a trusted stage and exception class.
    """
    stage = "preflight"
    def phase_progress(detail):
        nonlocal stage
        stage = stage.split(".", 1)[0] + "." + detail
    try:
        repo, out = Path(repo).resolve(), Path(out).absolute()
        _require(os.environ.get("MISTRAL_API_KEY", "").strip() and os.environ.get("PSTACK_VIBE_MODEL") == MODEL,
                 "exact model and provider credential are required")
        _require(os.getuid() > 0 and os.getgid() > 0, "non-root controller required")
        _require(out == out.resolve() and not out.exists() and not out.is_relative_to(repo)
                 and not any(char in str(out) + str(POLICY) for char in ",\n\r"), "unsafe artifact destination")
        _require(type(wrapper) is dict and set(wrapper) == {"schema", "mode", "checkout_ref", "plan", "publication"}
                 and type(wrapper["schema"]) is int and wrapper["schema"] == 1
                 and wrapper["mode"] in ("reconcile", "fixture")
                 and re.fullmatch(r"[0-9a-f]{40}", wrapper["checkout_ref"]) is not None, "invalid trusted wrapper")
        plan = wrapper["plan"]
        _require(plan == protocol.plan(repo) and not plan["noop"] and not plan["blocked_reasons"], "plan is blocked or stale")
        with tempfile.TemporaryDirectory(prefix=".pstack-adapt-", dir=out.parent) as directory:
            root = Path(directory)
            snapshots, receipts, report = root / "snapshots", root / "receipts", root / "report"
            receipts.mkdir(mode=0o700)
            report.mkdir(mode=0o700)
            protocol.materialize(repo, plan, snapshots)
            _task("writer", plan, {}, root / "writer-policy")
            stage = "writer"
            writer_receipt, writer_run = _phase("writer", snapshots, root / "writer-policy", receipts,
                                                progress=phase_progress)
            stage = "candidate"
            envelope = protocol.collect(repo, plan, snapshots / "candidate")
            for update in envelope["updates"]:
                before = protocol._git(repo, "show", f"{plan['base_commit']}:{protocol.ADAPTED}/{update['path']}")
                control.validate_text_update(update["path"], before.decode("utf-8"), update["content"])
            _task("reviewer", plan, envelope, root / "reviewer-policy")
            stage = "reviewer"
            reviewer_receipt, reviewer_run = _phase("reviewer", snapshots, root / "reviewer-policy", receipts, report,
                                                    progress=phase_progress)
            stage = "reviewer.candidate"
            _require(protocol.collect(repo, plan, snapshots / "candidate") == envelope, "candidate changed during review")
            stage = "reviewer.outputs"
            _require({path.name for path in report.iterdir()} == {"audit.json"}, "unexpected reviewer output")
            stage = "reviewer.audit"
            audit = control.validate_audit(control.read_json(report / "audit.json", maximum=128 * 1024), plan, envelope)
            payload = {"schema": 1, "plan": wrapper, "candidate": envelope, "audit": audit,
                       "receipts": {"writer": writer_receipt, "reviewer": reviewer_receipt},
                       "runs": {"writer": writer_run, "reviewer": reviewer_run}}
        stage = "artifact"
        out.mkdir(mode=0o700)
        temporary = out / ".candidate.json.tmp"
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                json.dump(payload, stream, sort_keys=True, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, out / "candidate.json")
        finally:
            temporary.unlink(missing_ok=True)
        return payload
    except Exception as exc:
        raise ValueError(f"adaptation blocked at {stage} ({type(exc).__name__})") from None

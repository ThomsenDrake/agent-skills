"""Trusted updater orchestration. Candidate text never supplies executable policy."""


import json
import os
from pathlib import Path
import stat


def read_json(path: Path, maximum: int = 8 * 1024 * 1024) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def constant(_value):
        raise ValueError("non-finite JSON value")

    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > maximum:
        raise ValueError("JSON input must be one bounded regular file")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("JSON input exceeds the size limit")
    result = json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(result, dict):
        raise ValueError("JSON input must be an object")
    return result


def validate_text_update(path: str, before: str, after: str) -> None:
    if path == "SKILL.md" or path.endswith("/SKILL.md"):
        def header(text):
            if not text.startswith("---\n") or "\n---\n" not in text[4:]:
                raise ValueError("skill frontmatter must be intact")
            return text[:text.index("\n---\n", 4) + 5]
        if header(before) != header(after):
            raise ValueError("automatic updates cannot change skill frontmatter")
    import re
    old_commands = re.findall(r"!`[^`]+`", before)
    new_commands = re.findall(r"!`[^`]+`", after)
    if old_commands != new_commands:
        raise ValueError("automatic updates cannot add or alter shell templates")


FIXTURE_PATH = "skills/pstack/principle-laziness-protocol/SKILL.md"
FIXTURE_MARKER = "PSTACK_UPDATER_SMOKE"


def git_text(repo: Path, *args: str, env=None) -> str:
    import subprocess
    return subprocess.check_output(["git", *args], cwd=repo, env=env, text=True)


def make_fixture(repo: Path) -> str:
    if git_text(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("fixture requires a clean disposable checkout")
    source = repo / FIXTURE_PATH
    if not source.is_file() or source.is_symlink():
        raise ValueError("fixture source must be an existing regular Markdown file")
    content = source.read_text()
    if FIXTURE_MARKER in content:
        raise ValueError("fixture is already applied")
    source.write_text(content + "\nFor audit logs, label reversible choices with `PSTACK_UPDATER_SMOKE`.\n")
    git_text(repo, "add", "--", FIXTURE_PATH)
    env = os.environ | {
        "GIT_AUTHOR_NAME": "Updater Fixture", "GIT_COMMITTER_NAME": "Updater Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        "GIT_AUTHOR_DATE": "2001-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2001-01-01T00:00:00Z",
    }
    git_text(repo, "commit", "-qm", "test: disposable semantic updater fixture", env=env)
    return git_text(repo, "rev-parse", "HEAD").strip()


def worker_command(*, name: str, network: str, policy: Path, snapshots: Path,
                   state_volume: str, role: str, uid: int, gid: int,
                   report_dir: Path | None = None) -> list[str]:
    if role != "writer" or report_dir is not None or uid <= 0 or gid <= 0:
        raise ValueError("worker must be a bounded non-root writer without a report mount")
    for path in (policy, snapshots, report_dir):
        if path is not None and (not path.is_absolute() or any(c in str(path) for c in ",\n\r")):
            raise ValueError("invalid controller mount path")
    args = ["docker", "run", "--rm", "--name", name, "--network", network,
            "--dns", "127.0.0.1", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--pids-limit", "128",
            "--cpus", "2", "--memory", "2g", "--user", f"{uid}:{gid}",
            "--mount", f"type=bind,src={policy},dst=/policy,readonly",
            "--mount", f"type=bind,src={snapshots},dst=/work,readonly",
            "--mount", f"type=volume,src={state_volume},dst=/state",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777"]
    args.extend(["--mount", f"type=bind,src={snapshots / 'candidate'},dst=/work/candidate"])
    # Strip Python-image build metadata too; do not inherit an image's ENV.
    args.extend(["--entrypoint", "/usr/bin/env", "pstack-vibe:verified", "-i",
                 "HOME=/state/home", "VIBE_HOME=/state/vibe", "TMPDIR=/state/tmp",
                 "PATH=/usr/local/bin:/usr/bin:/bin", "LANG=C.UTF-8", "LC_ALL=C.UTF-8",
                 "PYTHONDONTWRITEBYTECODE=1", "PYTHONUNBUFFERED=1",
                 "MISTRAL_API_KEY=gateway-only-not-a-provider-key",
                 "python", "-I", "/policy/vibe_entry.py", "--role", role])
    return args


POLICY = Path(__file__).resolve().parent
REPOSITORY = "ThomsenDrake/agent-skills"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def plan_command(repo: Path, mode: str, repository: str, out: Path) -> dict:
    import protocol
    if repository != REPOSITORY or mode not in ("fixture", "reconcile"):
        raise ValueError("unsupported updater repository or mode")
    if out.is_relative_to(repo) or out.exists():
        raise ValueError("plan output must be a new directory outside the checkout")
    checkout_ref = git_text(repo, "rev-parse", "HEAD").strip()
    if mode == "fixture":
        make_fixture(repo)
    current = protocol.plan(repo)
    if current["blocked_reasons"]:
        raise ValueError("source delta requires manual review: " + "; ".join(current["blocked_reasons"]))
    publication = None
    needs_update = not current["noop"]
    if needs_update and mode == "reconcile":
        import publish as publisher
        publication = publisher.probe(repository, current)
        if publication["blocked_reasons"]:
            raise ValueError("publication is blocked by an explicitly closed pull request")
        needs_update = not publication["skip"]
    wrapper = {"schema": 1, "mode": mode, "checkout_ref": checkout_ref,
               "plan": current, "publication": publication}
    write_json(out / "plan.json", wrapper)
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write(f"needs_update={str(needs_update).lower()}\ncheckout_ref={checkout_ref}\nmode={mode}\n")
    print(json.dumps({"mode": mode, "needs_update": needs_update, "source_tree": current["source_tree"]}))
    return wrapper


def restore_plan(repo: Path, wrapper: dict) -> dict:
    import protocol
    import re
    required = {"schema", "mode", "checkout_ref", "plan", "publication"}
    if (type(wrapper) is not dict or set(wrapper) != required or type(wrapper["schema"]) is not int
            or wrapper["schema"] != 1 or wrapper["mode"] not in ("fixture", "reconcile")
            or not isinstance(wrapper["checkout_ref"], str)
            or not re.fullmatch(r"[0-9a-f]{40}", wrapper["checkout_ref"])
            or type(wrapper["plan"]) is not dict):
        raise ValueError("invalid protected plan wrapper")
    head = git_text(repo, "rev-parse", "HEAD").strip()
    base = wrapper["plan"].get("base_commit")
    if head not in (base, wrapper["checkout_ref"]):
        raise ValueError("checkout differs from the protected plan")
    if wrapper["mode"] == "fixture":
        if head == wrapper["checkout_ref"]:
            make_fixture(repo)
        if git_text(repo, "rev-parse", "HEAD^").strip() != wrapper["checkout_ref"]:
            raise ValueError("fixture does not have the protected workflow revision as its parent")
    elif wrapper["checkout_ref"] != base:
        raise ValueError("reconciliation checkout differs from its publication base")
    current = protocol.plan(repo)
    if current != wrapper["plan"] or current["blocked_reasons"]:
        raise ValueError("protected plan differs from immutable repository objects")
    return current


def packet_candidate(wrapper: dict, packet: dict) -> dict:
    required = {"schema", "plan", "candidate", "receipts", "runs"}
    if (type(packet) is not dict or set(packet) != required or type(packet["schema"]) is not int
            or packet["schema"] != 2 or packet["plan"] != wrapper):
        raise ValueError("candidate artifact differs from the protected plan or schema")
    for key in ("receipts", "runs"):
        if type(packet[key]) is not dict or set(packet[key]) != {"writer"}:
            raise ValueError("candidate artifact requires writer-only evidence")
    envelope = packet["candidate"]
    bindings = ("schema", "base_commit", "base_source_commit", "base_source_tree",
                "source_commit", "source_tree", "adaptation_tree")
    if (type(envelope) is not dict or set(envelope) != {*bindings, "updates"}
            or type(envelope["schema"]) is not int or envelope["schema"] != 1):
        raise ValueError("candidate artifact lacks a closed schema-1 data envelope")
    for key in bindings:
        if envelope[key] != wrapper["plan"][key]:
            raise ValueError("candidate artifact changed a protected source binding")
    if type(envelope["updates"]) is not list or any(
            type(update) is not dict or set(update) != {"path", "content", "before_sha256", "after_sha256"}
            or type(update["path"]) is not str for update in envelope["updates"]):
        raise ValueError("candidate artifact has invalid update shapes")
    edited = {update["path"] for update in envelope["updates"]}
    bot_paths = {"agents/poteto-agent.md": "bots/poteto-agent/SOUL.md",
                 "agents/comment-sicko.md": "bots/comment-sicko/SOUL.md"}
    if not edited or any(bot_paths.get(path, path) not in edited for path in wrapper["plan"]["changed_paths"]):
        raise ValueError("manual review required: candidate must edit every changed source counterpart")
    return envelope


def install_verifier(root: Path, *, runner=None) -> Path:
    import subprocess
    import sys
    runner = runner or subprocess.run
    if root.exists() or any(char in str(root) for char in "\n\r"):
        raise ValueError("verifier needs a new isolated environment")
    pins = read_json(POLICY / "runtime.json")
    import re
    if not re.fullmatch(r"[0-9a-f]{40}", pins["hermes_commit"]):
        raise ValueError("Hermes verifier revision is not immutable")
    home = root.parent / "pstack-installer-home"
    home.mkdir(exist_ok=True)
    environment = {key: value for key, value in os.environ.items()
                   if key in {"PATH", "LANG", "LC_ALL", "TMPDIR", "LD_LIBRARY_PATH",
                              "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"}}
    environment["HOME"] = str(home)
    interpreter = root / "bin/python"
    runner([sys.executable, "-m", "venv", str(root)], env=environment, check=True, timeout=120)
    runner([str(interpreter), "-m", "pip", "--isolated", "install", "--no-cache-dir",
            "--disable-pip-version-check", "--timeout", "30", "--retries", "2",
            "git+https://github.com/NousResearch/hermes-agent.git@" + pins["hermes_commit"]],
           env=environment, check=True, timeout=900)
    runner([str(interpreter), "-m", "pip", "check"], env=environment, check=True, timeout=60)
    if output := os.environ.get("GITHUB_ENV"):
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write(f"PSTACK_VERIFIER_PYTHON={interpreter}\n")
    return interpreter


def run_checks(repo: Path, out: Path, *, interpreter: Path | None = None, runner=None) -> dict:
    import subprocess
    runner = runner or subprocess.run
    interpreter = interpreter or Path(os.environ.get("PSTACK_VERIFIER_PYTHON", "/missing-verifier"))
    if not interpreter.is_absolute() or not interpreter.is_file():
        raise ValueError("the isolated Hermes verifier is not installed")
    package = repo / "skills/pstack-hermes"
    runner([str(interpreter), "-m", "unittest", "discover", "-s", str(package / "tests"), "-v"],
           cwd=repo, check=True, timeout=180)
    runner([str(interpreter), "-m", "unittest", "discover", "-s", str(package / "automation/tests"), "-v"],
           cwd=repo, check=True, timeout=300)
    helpers = package / "poteto-mode/scripts"
    for command in (["bun", "install", "--frozen-lockfile", "--ignore-scripts"],
                    ["bun", "run", "test"], ["bun", "run", "typecheck"]):
        runner(command, cwd=helpers, check=True, timeout=180)
    completed = runner([str(interpreter), str(package / "automation/verify_native.py"),
                        "--package", str(package), "--home", str(out / "hermes-home")],
                       cwd=repo, check=True, timeout=120, capture_output=True, text=True)
    native = json.loads(completed.stdout)
    if (native.get("cli_passed") is not True or native.get("inference_performed") is not False
            or native.get("loaded_skills") != 55 or native.get("loaded_support_files", 0) < 62):
        raise ValueError("native Hermes catalog did not meet the accepted inventory")
    return {"contract_tests": True, "updater_tests": True, "helper_tests": True,
            "helper_typecheck": True, "native": native}


def verify_command(repo: Path, wrapper: dict, packet: dict, out: Path) -> dict:
    envelope = packet_candidate(wrapper, packet)
    current = restore_plan(repo, wrapper)
    if current["noop"] or out.exists() or out.is_relative_to(repo):
        raise ValueError("verification needs a changed source and a new external output directory")
    import engine
    import protocol
    engine.validate_receipt(packet["receipts"]["writer"])
    engine.validate_run(packet["runs"]["writer"])
    # This is a disposable checkout. Only a successful normalized artifact can
    # leave this job; the accepted checkpoint remains on main until human merge.
    protocol.apply(repo, envelope)
    for update in envelope["updates"]:
        before = git_text(repo, "show", current["base_commit"] + ":skills/pstack-hermes/" + update["path"])
        validate_text_update(update["path"], before, update["content"])
    if wrapper["mode"] == "fixture":
        target = repo / FIXTURE_PATH.replace("skills/pstack/", "skills/pstack-hermes/", 1)
        if FIXTURE_MARKER not in target.read_text():
            raise ValueError("live Vibe smoke did not preserve the controlled source marker")
    out.mkdir(parents=True)
    checks = run_checks(repo, out)
    verified = {**packet, "checks": checks}
    write_json(out / "verified.json", verified)
    print(json.dumps({"verified": True, "mode": wrapper["mode"],
                      "loaded_skills": checks["native"]["loaded_skills"]}))
    return verified


def publish_command(repo: Path, verified: dict, repository: str) -> dict:
    if (type(verified.get("plan")) is not dict or verified["plan"].get("mode") != "reconcile"):
        raise ValueError("fixture or invalid artifacts cannot publish")
    if repository != REPOSITORY or set(verified) != {"schema", "plan", "candidate", "receipts", "runs", "checks"}:
        raise ValueError("invalid verifier publication artifact")
    checks = verified["checks"]
    if (type(checks) is not dict or set(checks) != {"contract_tests", "updater_tests", "helper_tests", "helper_typecheck", "native"}
            or any(checks.get(key) is not True for key in ("contract_tests", "updater_tests", "helper_tests", "helper_typecheck"))
            or type(checks["native"]) is not dict or checks["native"].get("cli_passed") is not True
            or checks["native"].get("loaded_skills") != 55 or checks["native"].get("inference_performed") is not False):
        raise ValueError("verifier artifact lacks completed protected checks")
    packet = {key: value for key, value in verified.items() if key != "checks"}
    wrapper = packet["plan"]
    envelope = packet_candidate(wrapper, packet)
    current = restore_plan(repo, wrapper)
    import engine
    import publish as publisher
    engine.validate_receipt(packet["receipts"]["writer"])
    engine.validate_run(packet["runs"]["writer"])
    for update in envelope["updates"]:
        before = git_text(repo, "show", current["base_commit"] + ":skills/pstack-hermes/" + update["path"])
        validate_text_update(update["path"], before, update["content"])
    result = publisher.publish(repo, envelope, repository, expected_probe=wrapper["publication"])
    print(json.dumps(result, sort_keys=True))
    return result


def main(argv=None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Protected pstack Hermes updater controller")
    commands = parser.add_subparsers(dest="command", required=True)
    plan_parser = commands.add_parser("plan")
    plan_parser.add_argument("--repo", type=Path, required=True)
    plan_parser.add_argument("--mode", choices=("reconcile", "fixture"), required=True)
    plan_parser.add_argument("--repository", required=True)
    plan_parser.add_argument("--out", type=Path, required=True)
    for name in ("adapt", "verify"):
        stage = commands.add_parser(name)
        stage.add_argument("--repo", type=Path, required=True)
        stage.add_argument("--plan", type=Path, required=True)
        stage.add_argument("--out", type=Path, required=True)
        if name == "verify":
            stage.add_argument("--candidate", type=Path, required=True)
    publication = commands.add_parser("publish")
    publication.add_argument("--repo", type=Path, required=True)
    publication.add_argument("--verified", type=Path, required=True)
    publication.add_argument("--repository", required=True)
    commands.add_parser("install-verifier")
    args = parser.parse_args(argv)
    if temporary := os.environ.get("RUNNER_TEMP"):
        os.environ["TMPDIR"] = temporary
    if args.command == "plan":
        plan_command(args.repo.resolve(), args.mode, args.repository, args.out.resolve())
    elif args.command == "adapt":
        repo, out = args.repo.resolve(), args.out.resolve()
        wrapper = read_json(args.plan, maximum=128 * 1024)
        current = restore_plan(repo, wrapper)
        if current["noop"]:
            raise ValueError("unchanged source cannot invoke a model")
        if out.exists() or out.is_relative_to(repo):
            raise ValueError("model output needs a new directory outside the checkout")
        import engine
        engine.adapt(repo, wrapper, out)
        if not (out / "candidate.json").is_file():
            raise ValueError("model engine did not produce its candidate artifact")
    elif args.command == "verify":
        verify_command(args.repo.resolve(), read_json(args.plan, maximum=128 * 1024),
                       read_json(args.candidate), args.out.resolve())
    elif args.command == "publish":
        publish_command(args.repo.resolve(), read_json(args.verified), args.repository)
    elif args.command == "install-verifier":
        if not os.environ.get("RUNNER_TEMP"):
            raise ValueError("verifier installation requires an isolated CI runner")
        install_verifier(Path(os.environ["RUNNER_TEMP"]) / "pstack-hermes-verifier")


if __name__ == "__main__":
    main()

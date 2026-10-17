"""Controller contracts; Docker lifecycle tests explicitly mock the unavailable daemon.

No provider calls, real credentials, remote writes, or checkout mutations.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

AUTOMATION = Path(__file__).resolve().parents[1]


def engine(test):
    path = AUTOMATION / "engine.py"
    test.assertTrue(path.is_file(), "missing two-phase engine")
    spec = importlib.util.spec_from_file_location("pstack_engine_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(AUTOMATION))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def receipt():
    return {"request_count": 2, "upstream_request_count": 2, "successful_2xx": 2,
            "total_request_bytes": 1200, "max_request_bytes": 262144,
            "max_total_request_bytes": 1500000, "model_ids_submitted": ["mistral-large-4"],
            "errors": {}, "started_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:05+00:00", "elapsed_seconds": 5.0,
            "deadline_seconds": 1200.0, "status": "closed"}


def metrics():
    return {"bindings": {"alias": "mistral-large-4", "model": "mistral-large-4", "provider": "mistral",
                         "backend": "mistral", "base_url": "http://model-gateway:8080/v1", "vibe_version": "2.26.1"},
            "usage": {"input_tokens": 10, "output_tokens": 5, "cached_input_tokens": 0, "total_tokens": 15},
            "cost_usd": 0.01}


class EvidenceTests(unittest.TestCase):
    def test_export_helper_runs_real_entry_validation_and_reduces_synthetic_export_only(self):
        import contextlib
        import io
        import runpy
        import tomllib
        mod = engine(self)
        entry = runpy.run_path(str(AUTOMATION / "vibe_entry.py"))
        config = tomllib.loads((AUTOMATION / "vibe-config.toml").read_text())
        config["models"] = {item["alias"]: item for item in config["models"]}
        synthetic = {"schema_version": 1, "vibe_version": "2.26.1", "outcome": "finished", "exit_code": 0,
                     "error": None, "session_id": "PRIVATE_SYNTHETIC_SESSION_NOT_RUN_EVIDENCE",
                     "usage": metrics()["usage"], "cost_usd": 0.01, "config": config,
                     "limits": {"max_turns": 40, "max_price": 2, "max_tokens": 150000, "time_limit_s": 900}}
        with tempfile.TemporaryDirectory(dir=os.environ["TMPDIR"]) as directory:
            path = Path(directory) / "export.json"
            path.write_text(json.dumps(synthetic))
            def redirect_read_export(requested):
                self.assertEqual(requested, Path("/state/evidence/export.json"))
                return entry["read_export"](path)
            bindings = {"read_export": redirect_read_export, "validate_export": entry["validate_export"]}
            stdout = io.StringIO()
            with mock.patch.object(runpy, "run_path", return_value=bindings) as read_policy, contextlib.redirect_stdout(stdout):
                exec(compile(mod.EXPORT_HELPER, "trusted-export-helper", "exec"), {})
            read_policy.assert_called_once_with("/policy/vibe_entry.py")
            self.assertEqual(mod.validate_run(json.loads(stdout.getvalue())), metrics())
            self.assertNotIn("PRIVATE_SYNTHETIC", stdout.getvalue())
            self.assertNotIn("config", json.loads(stdout.getvalue()))
            synthetic["usage"] = None
            path.write_text(json.dumps(synthetic))
            stdout = io.StringIO()
            with mock.patch.object(runpy, "run_path", return_value=bindings), contextlib.redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as failure:
                    exec(compile(mod.EXPORT_HELPER, "trusted-export-helper", "exec"), {})
            self.assertEqual(str(failure.exception), "invalid worker export")
            self.assertEqual(stdout.getvalue(), "")

    def test_stdout_json_rejects_duplicates_nonfinite_nonobjects_and_oversize(self):
        mod = engine(self)
        for text in ('{"ok":true,"ok":true}', '{"value":NaN}', '[]', '"raw"', "x" * 8193):
            with self.subTest(text=text[:40]), self.assertRaises(ValueError):
                mod._json(text)

    def test_run_requires_safe_bindings_and_real_bounded_integer_usage(self):
        mod = engine(self)
        self.assertTrue(callable(getattr(mod, "validate_run", None)), "missing host usage gate")
        self.assertEqual(mod.validate_run(metrics()), metrics())
        for mutation in ({"usage": None}, {"bindings": None}, {"bindings": {}},
                         {"session_id": "must-not-export"},
                         {"cost_usd": None}, {"cost_usd": float("nan")}, {"cost_usd": 2.01},
                         {"cost_usd": True}, {"cost_usd": 10 ** 1000}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                mod.validate_run(metrics() | mutation)
        for field in metrics()["bindings"]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                mod.validate_run(metrics() | {"bindings": metrics()["bindings"] | {field: "wrong"}})
        for mutation in ({"input_tokens": 0}, {"output_tokens": 0}, {"total_tokens": 16},
                         {"cached_input_tokens": 11}, {"input_tokens": True}, {"extra": 0},
                         {"input_tokens": 150000, "total_tokens": 150005}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                mod.validate_run(metrics() | {"usage": metrics()["usage"] | mutation})

    def test_receipt_requires_closed_successful_exact_model_route_with_fixed_caps(self):
        mod = engine(self)
        self.assertEqual(mod.validate_receipt(receipt()), receipt())
        for mutation in ({"request_count": True}, {"request_count": 41}, {"request_count": 0},
                         {"upstream_request_count": 1}, {"successful_2xx": 0},
                         {"model_ids_submitted": ["mistral-small-latest"]},
                         {"model_ids_submitted": ["mistral-large-4", "other"]},
                         {"errors": {"upstream_error": 1}}, {"errors": []},
                         {"total_request_bytes": 0}, {"total_request_bytes": 1500001},
                         {"total_request_bytes": 524289}, {"max_request_bytes": 262145},
                         {"max_total_request_bytes": 1500001}, {"deadline_seconds": 1201},
                         {"elapsed_seconds": float("nan")}, {"elapsed_seconds": 1201},
                         {"deadline_seconds": 10 ** 1000}, {"elapsed_seconds": 10 ** 1000},
                         {"status": "active"}, {"status": "exhausted"},
                         {"updated_at": "bad"}, {"started_at": "2026-01-01T00:00:00"},
                         {"updated_at": "2025-01-01T00:00:00+00:00"}, {"extra": "forged"}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                mod.validate_receipt(receipt() | mutation)


class FakeDocker:
    """Explicit Docker CLI mock: exercises lifecycle, not kernel/network isolation."""
    def __init__(self, root):
        self.root, self.calls, self.resources = root, [], {}
        self.tasks, self.worker_exit, self.health_failures = {}, 0, 0
        self.worker_content, self.after_worker = AFTER, lambda role, mounts: None
        self.status_mutation = lambda status: status
        self.report_mutation = lambda report: report
        self.export = metrics()
        self.receipt_mutation = lambda report: report

    @staticmethod
    def mounts(args):
        result = {}
        for index, value in enumerate(args):
            if value == "--mount":
                fields = dict(part.split("=", 1) for part in args[index + 1].split(",") if "=" in part)
                result[fields["dst"]] = Path(fields["src"])
        return result

    def __call__(self, args, **kwargs):
        assert args[0] == "docker", "unexpected executable at mocked Docker boundary"
        assert kwargs["timeout"] <= 1100 and kwargs["stdin"] is subprocess.DEVNULL
        self.calls.append((list(args), kwargs))
        command = args[1:]
        code, stdout = 0, ""
        if command[:2] in (["network", "create"], ["volume", "create"], ["container", "create"]):
            kind = command[0]
            name = command[command.index("--name") + 1] if kind == "container" else command[-1]
            label = command[command.index("--label") + 1].split("=", 1)[1]
            assert (kind, name) not in self.resources
            self.resources[kind, name] = (label, command)
            stdout = name
        elif len(command) > 1 and command[1] == "inspect":
            resource = self.resources.get((command[0], command[-1]))
            code, stdout = (0, resource[0]) if resource else (1, "")
        elif len(command) > 1 and command[1] == "rm":
            self.resources.pop((command[0], command[-1]), None)
        elif command[:2] == ["network", "connect"] or command[0] == "start":
            pass
        elif command[0] == "exec":
            if self.health_failures:
                self.health_failures -= 1
                code = 1
        elif command[0] == "stop":
            gateway_args = self.resources["container", command[-1]][1]
            directory = self.mounts(gateway_args)["/receipts"]
            role = "writer" if "writer.json" in " ".join(gateway_args) else "reviewer"
            (directory / (role + ".json")).write_text(json.dumps(self.receipt_mutation(receipt())))
        elif command[0] == "run":
            mounts = self.mounts(command)
            if "--detach" in command:
                name = command[command.index("--name") + 1]
                label = command[command.index("--label") + 1].split("=", 1)[1]
                self.resources["container", name] = (label, command)
                stdout = name
            elif "--role" in command:
                role = command[-1]
                policy = mounts["/policy"]
                assert {p.name for p in policy.iterdir()} == {
                    "vibe_entry.py", "vibe-config.toml", "vibe-agent.toml", "task.txt"}
                assert {p.name for p in mounts["/work"].iterdir()} == {
                    "old-upstream", "new-upstream", "current-hermes", "candidate"}
                self.tasks[role] = (policy / "task.txt").read_text()
                if role == "writer":
                    (mounts["/work"] / "candidate/alpha/SKILL.md").write_text(self.worker_content)
                else:
                    report = {"passed": True, "security_concerns": [], "logic_errors": [],
                              "suggestions": [], "summary": "Inspected the specific upstream and candidate rules.",
                              "source_dispositions": [{"source_path": "alpha/SKILL.md", "status": "updated",
                                                       "reason": "Candidate includes the specific new upstream rule."}]}
                    (mounts["/out"] / "audit.json").write_text(json.dumps(self.report_mutation(report)))
                self.after_worker(role, mounts)
                code = self.worker_exit
                stdout = json.dumps(self.status_mutation({"schema": 1, "role": role, "ok": code == 0,
                                                          "exit_code": code, "stage": "finished" if code == 0 else "preflight"}))
            else:
                stdout = json.dumps(self.export)
        else:
            raise AssertionError("unhandled mocked Docker command: " + repr(command))
        return subprocess.CompletedProcess(args, code, stdout, "RAW_PROVIDER_ERROR_MUST_NOT_ESCAPE")


BEFORE = "---\nname: alpha\n---\nOld Hermes rule.\n"
AFTER = BEFORE + "Preserve the new upstream rule.\n"


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.mod = engine(self)
        temporary = tempfile.TemporaryDirectory(dir=os.environ["TMPDIR"])
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.out = self.root / "artifact"
        self.plan = {"schema": 1, "base_commit": "a" * 40, "base_source_commit": "b" * 40,
                     "base_source_tree": "c" * 40, "source_commit": "a" * 40,
                     "source_tree": "d" * 40, "adaptation_tree": "e" * 40,
                     "changed_paths": ["alpha/SKILL.md"], "allowed_paths": ["SKILL.md", "alpha/SKILL.md"],
                     "noop": False, "blocked_reasons": []}
        self.wrapper = {"schema": 1, "mode": "reconcile", "checkout_ref": "a" * 40,
                        "plan": self.plan, "publication": None}
        self.docker = FakeDocker(self.root)

    def boundaries(self):
        from contextlib import ExitStack
        self.assertTrue(callable(getattr(self.mod, "adapt", None)), "missing executable adaptation engine")
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(mock.patch.dict(os.environ, {"MISTRAL_API_KEY": "NON_SECRET_HOST_TEST_KEY",
                                                        "PSTACK_VIBE_MODEL": "mistral-large-4",
                                                        "GH_TOKEN": "NON_SECRET_FORBIDDEN_GH"}))
        stack.enter_context(mock.patch.object(self.mod.subprocess, "run", side_effect=self.docker))
        stack.enter_context(mock.patch.object(self.mod.protocol, "plan", return_value=self.plan))
        stack.enter_context(mock.patch.object(self.mod.protocol, "materialize", side_effect=self.materialize))
        self.collect = stack.enter_context(mock.patch.object(self.mod.protocol, "collect", side_effect=self.collect_fixture))
        self.git = stack.enter_context(mock.patch.object(self.mod.protocol, "_git", return_value=BEFORE.encode()))
        self.text_gate = stack.enter_context(mock.patch.object(self.mod.control, "validate_text_update",
                                                               wraps=self.mod.control.validate_text_update))
        self.audit_gate = stack.enter_context(mock.patch.object(self.mod.control, "validate_audit",
                                                                wraps=self.mod.control.validate_audit))
        return stack

    def materialize(self, repo, plan, destination):
        for name in ("old-upstream", "new-upstream", "current-hermes", "candidate"):
            path = destination / name / "alpha/SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text(BEFORE)

    def collect_fixture(self, repo, plan, candidate):
        import hashlib
        after = (candidate / "alpha/SKILL.md").read_text()
        return {**{key: plan[key] for key in ("schema", "base_commit", "base_source_commit", "base_source_tree",
                                            "source_commit", "source_tree", "adaptation_tree")},
                "updates": [{"path": "alpha/SKILL.md", "content": after,
                             "before_sha256": hashlib.sha256(BEFORE.encode()).hexdigest(),
                             "after_sha256": hashlib.sha256(after.encode()).hexdigest()}]}

    def test_mocked_worker_failure_stops_gateway_gracefully_without_artifact_or_raw_errors(self):
        self.boundaries()
        self.docker.worker_exit = 13
        with self.assertRaises(ValueError) as failure:
            self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertIn("writer", str(failure.exception))
        self.assertNotIn("RAW_PROVIDER", str(failure.exception))
        self.assertFalse(self.out.exists())
        self.assertEqual(self.docker.resources, {})
        self.assertTrue(any(args[1] == "stop" for args, _ in self.docker.calls),
                        "even failed workers must stop their credentialed gateway gracefully")
        self.assertEqual(set(self.docker.tasks), {"writer"})

    def test_mocked_worker_failure_reports_bounded_stage_and_exit_without_raw_output(self):
        self.boundaries()
        self.docker.worker_exit = 13
        with self.assertRaisesRegex(ValueError, r"writer\.worker\.preflight\.exit13 \(ValueError\)") as failure:
            self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertNotIn("RAW_PROVIDER", str(failure.exception))
        self.assertEqual(self.docker.resources, {})

    def test_mocked_vibe_stop_reason_remains_a_failed_run(self):
        self.boundaries()
        self.docker.worker_exit = 3
        for outcome in ("token_limit", "turn_limit", "price_limit", "deadline", "terminated", "length", "refusal"):
            self.docker.status_mutation = lambda status: status | {"stage": "vibe-" + outcome}
            with self.subTest(outcome=outcome), self.assertRaisesRegex(
                    ValueError, r"writer\.worker\.vibe-" + outcome + r"\.exit3 \(ValueError\)"):
                self.mod.adapt(self.repo, self.wrapper, self.out)
            self.assertFalse(self.out.exists())
            self.assertEqual(self.docker.resources, {})

    def test_mocked_untrusted_worker_stage_is_never_reflected(self):
        self.boundaries()
        self.docker.status_mutation = lambda status: status | {"stage": "RAW_PRIVATE_SOURCE"}
        with self.assertRaisesRegex(ValueError, r"writer\.worker \(ValueError\)") as failure:
            self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertNotIn("RAW_PRIVATE_SOURCE", str(failure.exception))

    def test_mocked_receipt_failure_identifies_only_the_receipt_gate(self):
        self.boundaries()
        self.docker.receipt_mutation = lambda report: report | {"errors": {"RAW_PRIVATE_ERROR": 1}}
        with self.assertRaisesRegex(ValueError, r"writer\.receipt \(ValueError\)") as failure:
            self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertNotIn("RAW_PRIVATE_ERROR", str(failure.exception))

    def test_mocked_reviewer_output_failure_identifies_only_the_output_gate(self):
        self.boundaries()
        def remove_report(role, mounts):
            if role == "reviewer":
                (mounts["/out"] / "audit.json").unlink()
        self.docker.after_worker = remove_report
        with self.assertRaisesRegex(ValueError, r"reviewer\.outputs \(ValueError\)"):
            self.mod.adapt(self.repo, self.wrapper, self.out)

    def test_mocked_audit_failure_identifies_gate_without_reflecting_findings(self):
        self.boundaries()
        self.docker.report_mutation = lambda report: report | {
            "passed": False, "security_concerns": ["RAW_PRIVATE_FINDING"]}
        with self.assertRaisesRegex(ValueError, r"reviewer\.audit\.verdict \(AuditError\)") as failure:
            self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertNotIn("RAW_PRIVATE_FINDING", str(failure.exception))

    def test_mocked_blocking_audit_reports_only_closed_rejection_code(self):
        self.boundaries()
        self.docker.report_mutation = lambda report: report | {
            "security_concerns": ["RAW_PRIVATE_FINDING"]}
        with self.assertRaisesRegex(ValueError, r"reviewer\.audit\.blockers \(AuditError\)") as failure:
            self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertNotIn("RAW_PRIVATE_FINDING", str(failure.exception))
        self.assertFalse(self.out.exists())

    def test_mocked_worker_status_cannot_substitute_booleans_for_schema_and_exit_integers(self):
        self.boundaries()
        self.docker.status_mutation = lambda status: status | {"schema": True, "exit_code": False}
        with self.assertRaises(ValueError):
            self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertFalse(self.out.exists())
        self.assertEqual(self.docker.resources, {})

    def test_preflight_blocks_missing_key_wrong_model_stale_plan_and_unsafe_output_before_docker(self):
        self.boundaries()
        for key, value in (("MISTRAL_API_KEY", ""), ("MISTRAL_API_KEY", "  "),
                           ("PSTACK_VIBE_MODEL", "mistral-large-latest")):
            with self.subTest(key=key, value=value), mock.patch.dict(os.environ, {key: value}):
                with self.assertRaises(ValueError):
                    self.mod.adapt(self.repo, self.wrapper, self.out)
        with self.assertRaises(ValueError):
            self.mod.adapt(self.repo, self.wrapper | {"plan": self.plan | {"noop": True}}, self.out)
        for output in (self.repo / "artifact", self.root, self.root / "unsafe,mount"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                self.mod.adapt(self.repo, self.wrapper, output)
        link = self.root / "redirect"
        link.symlink_to(self.repo, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.mod.adapt(self.repo, self.wrapper, link / "artifact")
        self.assertEqual(self.docker.calls, [])
        self.assertFalse(self.out.exists())

    def test_task_maps_both_agents_without_writer_prose_or_extra_discovery_files(self):
        plan = self.plan | {"changed_paths": ["agents/poteto-agent.md", "agents/comment-sicko.md"]}
        destination = self.root / "policy"
        self.mod._task("reviewer", plan, {"updates": [{"path": "bots/poteto-agent/SOUL.md",
                       "before_sha256": "1" * 64, "after_sha256": "2" * 64, "content": "WRITER_PROSE_NOT_AUTHORITY"}]},
                       destination)
        task = (destination / "task.txt").read_text()
        parsed = json.loads(task.split("Controller task JSON:\n", 1)[1])
        self.assertEqual(len(parsed["maps"]), 2)
        for mapping, bot in zip(parsed["maps"], ("poteto-agent", "comment-sicko")):
            self.assertEqual(mapping["old-upstream"], f"/work/old-upstream/agents/{bot}.md")
            self.assertEqual(mapping["new-upstream"], f"/work/new-upstream/agents/{bot}.md")
            self.assertEqual(mapping["current-hermes"], f"/work/current-hermes/bots/{bot}/SOUL.md")
            self.assertEqual(mapping["candidate"], f"/work/candidate/bots/{bot}/SOUL.md")
        self.assertNotIn("WRITER_PROSE_NOT_AUTHORITY", task)
        self.assertEqual(set(parsed["updates"][0]), {"path", "before_sha256", "after_sha256"})

    def test_mocked_gateway_health_retries_are_bounded_and_never_start_worker_when_unhealthy(self):
        self.boundaries()
        self.docker.health_failures = 99
        with mock.patch.object(self.mod.time, "sleep"), self.assertRaises(ValueError):
            self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertEqual(sum(args[1] == "exec" for args, _ in self.docker.calls), 10)
        self.assertEqual(self.docker.tasks, {})
        self.assertEqual(self.docker.resources, {})
        self.assertFalse(self.out.exists())

    def test_mocked_worker_timeout_cleans_its_still_running_container(self):
        self.boundaries()
        def timed_out(args, **kwargs):
            result = self.docker(args, **kwargs)
            if "--role" in args:
                name = args[args.index("--name") + 1]
                label = args[args.index("--label") + 1].split("=", 1)[1]
                self.docker.resources["container", name] = (label, args[1:])
                raise subprocess.TimeoutExpired(args, 1100, output="RAW_PROVIDER_MUST_NOT_ESCAPE")
            return result
        with mock.patch.object(self.mod.subprocess, "run", side_effect=timed_out), self.assertRaises(ValueError) as error:
            self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertIn("TimeoutExpired", str(error.exception))
        self.assertNotIn("RAW_PROVIDER", str(error.exception))
        self.assertFalse(self.out.exists())
        self.assertEqual(self.docker.resources, {})

    def test_mocked_partial_create_failure_removes_owned_not_foreign_resources(self):
        self.boundaries()
        def partial(args, **kwargs):
            result = self.docker(args, **kwargs)
            if args[1:3] == ["volume", "create"]:
                self.docker.resources["network", "human-network"] = ("foreign", [])
                raise subprocess.TimeoutExpired(args, 30)
            return result
        with mock.patch.object(self.mod.subprocess, "run", side_effect=partial), self.assertRaises(ValueError):
            self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertEqual(self.docker.resources, {("network", "human-network"): ("foreign", [])})
        self.assertFalse(self.out.exists())

    def test_mocked_forged_gateway_receipt_blocks_export_and_reviewer(self):
        self.boundaries()
        self.docker.receipt_mutation = lambda data: data | {"model_ids_submitted": ["other"]}
        with self.assertRaises(ValueError):
            self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertEqual(set(self.docker.tasks), {"writer"})
        self.assertFalse(any(self.mod.EXPORT_HELPER in args for args, _ in self.docker.calls))
        self.assertEqual(self.docker.resources, {})
        self.assertFalse(self.out.exists())

    def test_mocked_missing_export_usage_blocks_reviewer_and_artifact(self):
        self.boundaries()
        self.docker.export["usage"] = None
        with self.assertRaises(ValueError):
            self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertEqual(set(self.docker.tasks), {"writer"})
        self.assertEqual(self.docker.resources, {})
        self.assertFalse(self.out.exists())

    def test_mocked_protected_candidate_collect_failure_prevents_review(self):
        self.boundaries()
        self.collect.side_effect = ValueError("protected file changed")
        with self.assertRaises(ValueError):
            self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertEqual(set(self.docker.tasks), {"writer"})
        self.audit_gate.assert_not_called()
        self.assertFalse(self.out.exists())
        self.assertEqual(self.docker.resources, {})

    def test_mocked_frontmatter_and_shell_injection_are_blocked_before_review(self):
        self.boundaries()
        for content in (AFTER.replace("name: alpha", "name: hijacked"), AFTER + "!`touch anything`\n"):
            self.docker.worker_content = content
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.mod.adapt(self.repo, self.wrapper, self.out)
            self.assertEqual(set(self.docker.tasks), {"writer"})
            self.assertFalse(self.out.exists())
            self.assertEqual(self.docker.resources, {})

    def test_mocked_review_rejects_findings_missing_source_extra_fields_and_oversize(self):
        self.boundaries()
        for mutation in ({"passed": False}, {"security_concerns": ["unsafe"]}, {"source_dispositions": []},
                         {"extra": "unknown"}, {"summary": "x" * (128 * 1024)}):
            self.docker.report_mutation = lambda report: report | mutation
            with self.subTest(mutation=list(mutation)), self.assertRaises(ValueError):
                self.mod.adapt(self.repo, self.wrapper, self.out)
            self.assertFalse(self.out.exists())
            self.assertEqual(self.docker.resources, {})

    def test_mocked_review_cannot_add_files_directories_or_redirect_the_audit(self):
        self.boundaries()
        for attack in ("file", "directory", "symlink", "duplicate-json"):
            def corrupt(role, mounts):
                if role != "reviewer":
                    return
                audit = mounts["/out"] / "audit.json"
                if attack == "file":
                    (audit.parent / "extra.txt").write_text("extra")
                elif attack == "directory":
                    (audit.parent / "extra").mkdir()
                elif attack == "symlink":
                    audit.unlink()
                    audit.symlink_to(self.root / "nonexistent")
                else:
                    audit.write_text('{"passed":true,"passed":true}')
            self.docker.after_worker = corrupt
            with self.subTest(attack=attack), self.assertRaises(ValueError):
                self.mod.adapt(self.repo, self.wrapper, self.out)
            self.assertFalse(self.out.exists())
            self.assertEqual(self.docker.resources, {})

    def test_mocked_post_review_candidate_mutation_is_detected_by_second_collect(self):
        self.boundaries()
        def mutate(role, mounts):
            if role == "reviewer":
                (mounts["/work"] / "candidate/alpha/SKILL.md").write_text(AFTER + "late mutation\n")
        self.docker.after_worker = mutate
        with self.assertRaises(ValueError):
            self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertEqual(self.collect.call_count, 2)
        self.assertFalse(self.out.exists())
        self.assertEqual(self.docker.resources, {})

    def test_mocked_tmpfs_state_has_a_networkless_keeper_until_after_export_helper(self):
        self.boundaries()
        self.mod.adapt(self.repo, self.wrapper, self.out)
        calls = [args for args, _ in self.docker.calls]
        keepers = [args for args in calls if "--detach" in args]
        self.assertEqual(len(keepers), 2, "local-driver tmpfs would otherwise disappear when worker exits")
        for keeper in keepers:
            joined = " ".join(keeper)
            self.assertIn("--network none", joined)
            self.assertIn("dst=/state,readonly,volume-nocopy", joined)
            self.assertIn("--read-only", keeper)
            self.assertNotIn("--env", keeper)
            name = keeper[keeper.index("--name") + 1]
            start = calls.index(keeper)
            finish = next(index for index, args in enumerate(calls) if args[1:3] == ["container", "rm"] and args[-1] == name)
            between = calls[start + 1:finish]
            self.assertTrue(any("--role" in args for args in between))
            self.assertTrue(any(self.mod.EXPORT_HELPER in args for args in between))
        self.assertEqual(self.docker.resources, {})

    def test_mocked_docker_two_contexts_emit_only_reviewed_data_after_all_gates(self):
        self.boundaries()
        payload = self.mod.adapt(self.repo, self.wrapper, self.out)
        self.assertEqual(json.loads((self.out / "candidate.json").read_text()), payload)
        self.assertEqual({p.name for p in self.out.iterdir()}, {"candidate.json"})
        self.assertEqual(set(payload), {"schema", "plan", "candidate", "audit", "receipts", "runs"})
        self.assertEqual(payload["plan"], self.wrapper)
        self.assertEqual(payload["candidate"]["updates"][0]["content"], AFTER)
        self.assertEqual(payload["runs"], {"writer": metrics(), "reviewer": metrics()})
        self.assertEqual(payload["receipts"], {"writer": receipt(), "reviewer": receipt()})
        self.assertEqual(self.collect.call_count, 2)
        self.text_gate.assert_called_once_with("alpha/SKILL.md", BEFORE, AFTER)
        self.audit_gate.assert_called_once()
        self.assertIn("show", self.git.call_args.args)
        self.assertIn("a" * 40 + ":skills/pstack-hermes/alpha/SKILL.md", self.git.call_args.args)
        self.assertEqual(self.docker.resources, {}, "all uniquely-owned Docker resources must be removed")
        self.assertFalse(any(path.name.startswith(".pstack-") for path in self.root.iterdir()))
        for role, task in self.docker.tasks.items():
            self.assertIn("/work/old-upstream/alpha/SKILL.md", task)
            self.assertIn("/work/new-upstream/alpha/SKILL.md", task)
            self.assertIn("/work/current-hermes/alpha/SKILL.md", task)
            self.assertIn("/work/candidate/alpha/SKILL.md", task)
            self.assertNotIn("NON_SECRET_HOST_TEST_KEY", task)
        calls = [args for args, _kwargs in self.docker.calls]
        workers = [args for args in calls if "--role" in args]
        self.assertEqual([args[-1] for args in workers], ["writer", "reviewer"])
        volumes = [next(value for value in args if value.startswith("type=volume")) for args in workers]
        self.assertNotEqual(*volumes)
        for volume in volumes:
            self.assertIn("volume-nocopy", volume, "image /state ownership must not overwrite host-UID tmpfs options")
        gateways = [args for args in calls if args[1:3] == ["container", "create"]]
        self.assertEqual(len(gateways), 2)
        for args, kwargs in self.docker.calls:
            self.assertNotIn("NON_SECRET_HOST_TEST_KEY", " ".join(args))
            self.assertNotIn("GH_TOKEN", kwargs["env"])
            self.assertEqual("MISTRAL_API_KEY" in kwargs["env"], args in gateways)
        for args in gateways:
            joined = " ".join(args)
            for required in ("--env MISTRAL_API_KEY", "--read-only", "--cap-drop ALL", "no-new-privileges",
                             "--memory 512m", "--cpus 1", "--pids-limit 64", "--network-alias model-gateway",
                             "--max-requests 40", "--max-request-bytes 262144",
                             "--max-total-request-bytes 1500000", "--max-response-bytes 16777216",
                             "--deadline-seconds 1200", "dst=/policy/model_gateway.py,readonly"):
                self.assertIn(required, joined)
            self.assertNotIn("--publish", args)
            self.assertNotIn("/work", self.docker.mounts(args))
        internal = [args for args in calls if args[1:3] == ["network", "create"] and "--internal" in args]
        external = [args for args in calls if args[1:3] == ["network", "create"] and "--internal" not in args]
        self.assertEqual(len(internal), 2)
        self.assertEqual(len(external), 2)
        helpers = [args for args in calls if self.mod.EXPORT_HELPER in args]
        for args in helpers:
            joined = " ".join(args)
            for required in ("--network none", "--read-only", "dst=/state,readonly", "validate_export", "read_export"):
                self.assertIn(required, joined)
            self.assertNotIn("--env", args)
        created_volumes = [args for args in calls if args[1:3] == ["volume", "create"]]
        self.assertEqual(len(created_volumes), 2)
        for args in created_volumes:
            self.assertIn("type=tmpfs", args)
            self.assertIn("device=tmpfs", args)
            self.assertIn(f"o=size=128m,uid={os.getuid()},gid={os.getgid()},mode=0700", args)


if __name__ == "__main__":
    unittest.main()

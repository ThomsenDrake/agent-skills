"""End-to-end orchestration contracts, without remote side effects."""
import importlib.util
from pathlib import Path
import unittest

AUTOMATION = Path(__file__).resolve().parents[1]


def controller(test):
    path = AUTOMATION / "run.py"
    test.assertTrue(path.is_file(), "missing trusted orchestration controller")
    spec = importlib.util.spec_from_file_location("updater_run", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    import sys
    if str(AUTOMATION) not in sys.path:
        sys.path.insert(0, str(AUTOMATION))
    return module


class InputTests(unittest.TestCase):
    def test_text_updates_cannot_add_metadata_effects_or_shell_templates(self):
        run = controller(self)
        self.assertTrue(callable(getattr(run, "validate_text_update", None)), "missing inert Markdown gate")
        before = "---\nname: test\ndescription: Use when testing.\ncompatibility: Hermes\n---\nOld rule.\n"
        run.validate_text_update("test/SKILL.md", before, before.replace("Old rule", "New rule"))
        for after in (before.replace("compatibility: Hermes", "compatibility: Hermes\ndeps: [unsafe]"),
                      before.replace("name: test", "name: changed"), before + "!`execute something`\n"):
            with self.subTest(after=after), self.assertRaises(ValueError):
                run.validate_text_update("test/SKILL.md", before, after)
        run.validate_text_update("test/references/rule.md", "Old rule.", "New rule.")

    def test_json_reader_rejects_ambiguous_or_redirected_input(self):
        run = controller(self)
        self.assertTrue(callable(getattr(run, "read_json", None)), "missing strict JSON reader")
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text('{"schema": 1}')
            self.assertEqual(run.read_json(path), {"schema": 1})
            for content in ('{"a": 1, "a": 2}', '{"value": NaN}', '[]', '\x00', 'x' * 100):
                path.write_text(content)
                with self.subTest(content=content[:40]), self.assertRaises(ValueError):
                    run.read_json(path, maximum=80)
            path.write_text('{}')
            link = Path(directory) / "redirect.json"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                run.read_json(link)


class FixtureTests(unittest.TestCase):
    def test_fixture_is_reproducible_and_changes_only_disposable_source(self):
        run = controller(self)
        self.assertTrue(callable(getattr(run, "make_fixture", None)), "missing real semantic smoke fixture")
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = root / "seed"
            seed.mkdir()
            def git(where, *args):
                return subprocess.check_output(["git", *args], cwd=where, text=True, stderr=subprocess.DEVNULL).strip()
            git(seed, "init", "-q")
            path = seed / "skills/pstack/principle-laziness-protocol/SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text("---\nname: principle-laziness-protocol\n---\nPrefer the smaller change.\n")
            git(seed, "add", ".")
            git(seed, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "seed")
            heads = []
            for name in ("first", "second"):
                clone = root / name
                git(root, "clone", "-q", str(seed), str(clone))
                heads.append(run.make_fixture(clone))
                changed = git(clone, "diff", "--name-only", "HEAD^", "HEAD")
                self.assertEqual(changed, "skills/pstack/principle-laziness-protocol/SKILL.md")
                self.assertIn("PSTACK_UPDATER_SMOKE", (clone / path.relative_to(seed)).read_text())
                with self.assertRaises(ValueError):
                    run.make_fixture(clone)
            self.assertEqual(heads[0], heads[1])
            self.assertNotIn("PSTACK_UPDATER_SMOKE", path.read_text())


class ContainerTests(unittest.TestCase):
    def test_worker_has_no_host_credentials_shell_or_unbounded_write_mounts(self):
        run = controller(self)
        self.assertTrue(callable(getattr(run, "worker_command", None)), "missing container containment")
        args = dict(name="fixture-worker", network="internal-only", policy=Path("/fixture/policy"),
                    snapshots=Path("/fixture/inputs"), state_volume="fixture-state", uid=1001, gid=1001)
        writer = run.worker_command(role="writer", **args)
        joined = " ".join(writer)
        for required in ("--read-only", "--cap-drop ALL", "no-new-privileges", "--pids-limit 128",
                         "--memory 2g", "--cpus 2", "--user 1001:1001", "--dns 127.0.0.1",
                         "dst=/work,readonly", "dst=/policy,readonly", "dst=/work/candidate",
                         "/usr/bin/env", "-i", "gateway-only-not-a-provider-key"):
            self.assertIn(required, joined)
        self.assertNotIn("GH_TOKEN", joined)
        self.assertNotIn("--privileged", writer)
        reviewer = run.worker_command(role="reviewer", report_dir=Path("/fixture/report"), **args)
        self.assertNotIn("dst=/work/candidate", " ".join(reviewer))
        self.assertIn("dst=/out", " ".join(reviewer))
        with self.assertRaises(ValueError):
            run.worker_command(role="writer", **(args | {"uid": 0}))
        with self.assertRaises(ValueError):
            run.worker_command(role="writer", **(args | {"policy": Path("/unsafe,mount")}))


class PlanCliTests(unittest.TestCase):
    def test_plan_cli_skips_identical_source_and_reconstructs_fixture(self):
        import json
        import os
        import shutil
        import subprocess
        import sys
        import tempfile
        root = Path(tempfile.mkdtemp(prefix="pstack-plan-cli-"))
        checkout = root / "repo"
        source = AUTOMATION.parents[2]
        subprocess.run(["git", "clone", "-q", str(source), str(checkout)], check=True)
        # Derive the seed from Git, not the applied proposal working tree.
        fixture_source = checkout / "skills/pstack/principle-laziness-protocol/SKILL.md"
        if "PSTACK_UPDATER_SMOKE" in fixture_source.read_text():
            subprocess.run(["git", "reset", "--hard", "HEAD^"], cwd=checkout,
                           check=True, stdout=subprocess.DEVNULL)
        shutil.copytree(AUTOMATION, checkout / "skills/pstack-hermes/automation", dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "engine.py", "test_engine.py"))
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()
        tree = subprocess.check_output(["git", "rev-parse", "HEAD:skills/pstack"], cwd=checkout, text=True).strip()
        (checkout / "skills/pstack-hermes/UPSTREAM.json").write_text(
            json.dumps({"schema": 1, "source_commit": head, "source_tree": tree}) + "\n")
        subprocess.run(["git", "add", "skills/pstack-hermes"], cwd=checkout, check=True)
        subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                        "commit", "-qm", "fixture: trusted controller snapshot"], cwd=checkout, check=True)
        env = os.environ | {"GITHUB_OUTPUT": str(root / "outputs")}
        script = str(AUTOMATION / "run.py")
        for mode, expected in (("reconcile", False), ("fixture", True)):
            out = root / mode
            result = subprocess.run([sys.executable, script, "plan", "--repo", str(checkout),
                                     "--mode", mode, "--repository", "ThomsenDrake/agent-skills",
                                     "--out", str(out)], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((out / "plan.json").is_file(), "plan CLI did not produce a bound artifact")
            wrapper = json.loads((out / "plan.json").read_text())
            self.assertEqual(wrapper["mode"], mode)
            self.assertEqual(wrapper["plan"]["noop"], not expected)
            self.assertIsNone(wrapper["publication"])
            self.assertIn("needs_update=" + str(expected).lower(), (root / "outputs").read_text())
            if mode == "reconcile":
                denied = subprocess.run([sys.executable, script, "adapt", "--repo", str(checkout),
                                         "--plan", str(out / "plan.json"), "--out", str(root / "forbidden-model")],
                                        env=env, capture_output=True, text=True)
                self.assertNotEqual(denied.returncode, 0)
                self.assertIn("unchanged source cannot invoke a model", denied.stderr)
                self.assertFalse((root / "forbidden-model").exists())
            run = controller(self)
            self.assertTrue(callable(getattr(run, "restore_plan", None)), "missing cross-job immutable plan check")
            self.assertEqual(run.restore_plan(checkout, wrapper), wrapper["plan"])
            import copy
            for field, value in (("checkout_ref", "f" * 40), ("mode", "unknown"), ("schema", True)):
                changed = copy.deepcopy(wrapper)
                changed[field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    run.restore_plan(checkout, changed)
            changed = copy.deepcopy(wrapper)
            changed["plan"]["source_tree"] = "f" * 40
            with self.assertRaises(ValueError):
                run.restore_plan(checkout, changed)


class PacketTests(unittest.TestCase):
    def test_artifact_cannot_change_the_protected_plan_or_drop_evidence_roles(self):
        run = controller(self)
        self.assertTrue(callable(getattr(run, "packet_candidate", None)), "missing artifact provenance binding")
        import copy
        plan = {"schema": 1, "changed_paths": ["unslop/SKILL.md"], "base_commit": "a" * 40,
                "base_source_commit": "b" * 40, "base_source_tree": "c" * 40,
                "source_commit": "a" * 40, "source_tree": "d" * 40, "adaptation_tree": "e" * 40}
        wrapper = {"schema": 1, "mode": "reconcile", "checkout_ref": "a" * 40, "plan": plan, "publication": {}}
        envelope = {key: plan[key] for key in ("schema", "base_commit", "base_source_commit", "base_source_tree",
                                              "source_commit", "source_tree", "adaptation_tree")}
        envelope["updates"] = [{"path": "unslop/SKILL.md"}]
        audit = {"passed": True, "security_concerns": [], "logic_errors": [], "suggestions": [],
                 "summary": "The inspected rule is represented in the edited target.",
                 "source_dispositions": [{"source_path": "unslop/SKILL.md", "status": "updated",
                                          "reason": "The edited target implements the source rule."}]}
        packet = {"schema": 1, "plan": wrapper, "candidate": envelope, "audit": audit,
                  "receipts": {"writer": {}, "reviewer": {}}, "runs": {"writer": {}, "reviewer": {}}}
        self.assertEqual(run.packet_candidate(wrapper, packet), envelope)
        for mutation in ("plan", "candidate", "receipts", "runs", "schema", "extra", "audit"):
            changed = copy.deepcopy(packet)
            if mutation == "plan":
                changed["plan"]["mode"] = "fixture"
            elif mutation == "candidate":
                changed["candidate"]["base_commit"] = "f" * 40
            elif mutation in ("receipts", "runs"):
                del changed[mutation]["reviewer"]
            elif mutation == "schema":
                changed[mutation] = True
            elif mutation == "extra":
                changed[mutation] = "unexpected"
            else:
                changed["audit"]["passed"] = False
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                run.packet_candidate(wrapper, changed)


class InstallerTests(unittest.TestCase):
    def test_verifier_installer_pins_source_and_exposes_only_its_python(self):
        run = controller(self)
        self.assertTrue(callable(getattr(run, "install_verifier", None)), "missing real verifier installation")
        import os
        import tempfile
        root = Path(tempfile.mkdtemp(prefix="pstack-installer-unit-"))
        calls = []
        def record(argv, **options):
            calls.append((argv, options))
        output = root / "github-env"
        old = os.environ.get("GITHUB_ENV")
        os.environ["GITHUB_ENV"] = str(output)
        try:
            interpreter = run.install_verifier(root / "venv", runner=record)
        finally:
            if old is None:
                os.environ.pop("GITHUB_ENV", None)
            else:
                os.environ["GITHUB_ENV"] = old
        self.assertEqual(interpreter, root / "venv/bin/python")
        self.assertEqual(len(calls), 3)
        self.assertIn("venv", calls[0][0])
        pins = run.read_json(AUTOMATION / "runtime.json")
        self.assertIn("git+https://github.com/NousResearch/hermes-agent.git@" + pins["hermes_commit"], calls[1][0])
        self.assertIn("--no-cache-dir", calls[1][0])
        self.assertNotIn("MISTRAL_API_KEY", calls[1][1]["env"])
        self.assertNotIn("GITHUB_TOKEN", calls[1][1]["env"])
        self.assertNotIn("ACTIONS_RUNTIME_TOKEN", calls[1][1]["env"])
        self.assertEqual(calls[-1][0][-2:], ["pip", "check"])
        self.assertIn(str(interpreter), output.read_text())


class CheckRunnerTests(unittest.TestCase):
    def test_checks_run_protected_tests_helpers_and_native_loader(self):
        run = controller(self)
        self.assertTrue(callable(getattr(run, "run_checks", None)), "missing executable verification gates")
        import json
        import subprocess
        import sys
        import tempfile
        from types import SimpleNamespace
        out = Path(tempfile.mkdtemp(prefix="pstack-check-runner-unit-"))
        calls = []
        def record(argv, **options):
            calls.append((argv, options))
            return SimpleNamespace(stdout=json.dumps({"loaded_skills": 55, "loaded_support_files": 62,
                                                      "inference_performed": False, "cli_passed": True}))
        report = run.run_checks(AUTOMATION.parents[2], out, interpreter=Path(sys.executable), runner=record)
        self.assertEqual(len(calls), 6)
        self.assertIn(str(AUTOMATION.parent / "tests"), calls[0][0])
        self.assertIn(str(AUTOMATION / "tests"), calls[1][0])
        self.assertEqual(calls[2][0], ["bun", "install", "--frozen-lockfile", "--ignore-scripts"])
        self.assertEqual(calls[3][0], ["bun", "run", "test"])
        self.assertEqual(calls[4][0], ["bun", "run", "typecheck"])
        self.assertIn(str(AUTOMATION / "verify_native.py"), calls[5][0])
        self.assertTrue(report["native"]["cli_passed"])
        def failure(argv, **options):
            raise subprocess.CalledProcessError(1, argv)
        with self.assertRaises(subprocess.CalledProcessError):
            run.run_checks(AUTOMATION.parents[2], out, interpreter=Path(sys.executable), runner=failure)


class CommandGuardTests(unittest.TestCase):
    def test_cli_exposes_real_pipeline_stages(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, str(AUTOMATION / "run.py"), "--help"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        for stage in ("plan", "adapt", "verify", "publish", "install-verifier"):
            self.assertIn(stage, result.stdout)

    def test_verifier_rejects_unbound_artifact_before_any_repository_access(self):
        run = controller(self)
        self.assertTrue(callable(getattr(run, "verify_command", None)), "missing fresh-job verifier")
        with self.assertRaisesRegex(ValueError, "artifact"):
            run.verify_command(Path("/nonexistent-checkout"), {}, {}, Path("/nonexistent-output"))

    def test_fixture_artifact_cannot_reach_publisher(self):
        run = controller(self)
        self.assertTrue(callable(getattr(run, "publish_command", None)), "missing publication guard")
        with self.assertRaisesRegex(ValueError, "fixture"):
            run.publish_command(Path("/nonexistent-checkout"), {"plan": {"mode": "fixture"}},
                                "ThomsenDrake/agent-skills")


class AuditTests(unittest.TestCase):
    def test_review_verdict_is_strict_and_fail_closed(self):
        run = controller(self)
        plan = {"changed_paths": ["unslop/SKILL.md"]}
        def good():
            return {"passed": True, "security_concerns": [], "logic_errors": [],
                    "suggestions": [], "summary": "Inspected the semantic delta.",
                    "source_dispositions": [{"source_path": "unslop/SKILL.md", "status": "updated",
                                             "reason": "The mapped output preserves the new source rule."}]}
        envelope = {"updates": [{"path": "unslop/SKILL.md"}]}
        self.assertEqual(run.validate_audit(good(), plan, envelope), good())
        for change in ({"passed": False}, {"passed": "true"}, {"security_concerns": ["unsafe"]},
                       {"logic_errors": ["missing rule"]}, {"suggestions": "not a list"},
                       {"summary": ""}, {"unknown": True}, {"source_dispositions": None}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                run.validate_audit(good() | change, plan, envelope)

    def test_review_disposition_requires_a_real_mapped_edit_or_specific_equivalence(self):
        run = controller(self)
        plan = {"changed_paths": ["unslop/SKILL.md"]}
        base = {"passed": True, "security_concerns": [], "logic_errors": [], "suggestions": [],
                "summary": "Inspected the specific semantic change."}
        entry = {"source_path": "unslop/SKILL.md", "status": "updated", "reason": "The new rule is represented here."}
        with self.assertRaisesRegex(ValueError, "edit"):
            run.validate_audit(base | {"source_dispositions": [entry]}, plan, {"updates": []})
        for change in ({"status": "guessed"}, {"reason": "okay"}, {"unknown": 1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                run.validate_audit(base | {"source_dispositions": [entry | change]}, plan,
                                   {"updates": [{"path": "unslop/SKILL.md"}]})
        entry["status"] = "already-present"
        self.assertTrue(run.validate_audit(base | {"source_dispositions": [entry]}, plan, {"updates": []})["passed"])

    def test_review_cannot_omit_a_source_delta(self):
        run = controller(self)
        plan = {"changed_paths": ["unslop/SKILL.md"]}
        report = {"passed": True, "security_concerns": [], "logic_errors": [],
                  "suggestions": [], "summary": "Inspected the semantic delta.",
                  "source_dispositions": []}
        with self.assertRaisesRegex(ValueError, "source"):
            run.validate_audit(report, plan, {"updates": []})


class AuditCodeTests(unittest.TestCase):
    def setUp(self):
        self.control = controller(self)
        self.plan = {"changed_paths": ["unslop/SKILL.md"]}
        self.envelope = {"updates": [{"path": "unslop/SKILL.md"}]}
        self.report = {"passed": True, "security_concerns": [], "logic_errors": [], "suggestions": [],
                       "summary": "Inspected the semantic delta.",
                       "source_dispositions": [{"source_path": "unslop/SKILL.md", "status": "updated",
                                                "reason": "The mapped output preserves the new source rule."}]}

    def assert_audit_code(self, report, code, *, plan=None, envelope=None):
        import copy
        before = copy.deepcopy(report)
        with self.assertRaises(ValueError) as caught:
            self.control.validate_audit(report, self.plan if plan is None else plan,
                                    self.envelope if envelope is None else envelope)
        self.assertEqual(getattr(caught.exception, "code", None), code)
        self.assertIsInstance(caught.exception, self.control.AuditError)
        self.assertEqual(caught.exception.args, (code,))
        self.assertEqual(str(caught.exception), code)
        self.assertEqual(report, before, "rejection must not normalize the report")

    def test_audit_error_has_only_closed_constant_codes(self):
        self.assertTrue(hasattr(self.control, "AuditError"), "missing coded audit rejection")
        codes = frozenset({"schema", "verdict", "lists", "blockers", "summary", "source-list",
                           "source-coverage", "disposition", "mapped-edit", "equivalence"})
        self.assertEqual(self.control.AUDIT_REJECTION_CODES, codes)
        self.assertIsInstance(self.control.AUDIT_REJECTION_CODES, frozenset)
        for code in sorted(codes):
            with self.subTest(code=code):
                error = self.control.AuditError(code)
                self.assertIsInstance(error, ValueError)
                self.assertEqual(error.code, code)
                self.assertIs(type(error.code), str)
                self.assertEqual(error.args, (code,))
                self.assertEqual(str(error), code)
                with self.assertRaises(AttributeError):
                    error.code = "schema"
                with self.assertRaises(AttributeError):
                    del error.code

        class NoCoercion:
            def __str__(self):
                raise AssertionError("must not stringify invalid codes")

            def __repr__(self):
                raise AssertionError("must not represent invalid codes")

            def __hash__(self):
                raise AssertionError("must not hash invalid codes")

        class StringSubclass(str):
            pass

        raw = "UNTRUSTED_AUDIT_TEXT\n" + "x" * 5000
        for code in (raw, "unknown", "SCHEMA", " schema", "schema\n", "", None, True, 1,
                     b"schema", [], {}, NoCoercion(), StringSubclass("schema")):
            with self.assertRaises(ValueError) as caught:
                self.control.AuditError(code)
            self.assertIs(type(caught.exception), ValueError)
            self.assertEqual(caught.exception.args, ("invalid audit rejection code",))
            self.assertNotIn("UNTRUSTED_AUDIT_TEXT", str(caught.exception))
            self.assertNotIn("UNTRUSTED_AUDIT_TEXT", repr(caught.exception))

    def test_audit_schema_code_rejects_wrong_or_unknown_fields(self):
        for report in (None, [], "UNTRUSTED_AUDIT_TEXT", True,
                       self.report | {"UNTRUSTED_AUDIT_TEXT": True, "passed": False}):
            with self.subTest(kind=type(report).__name__):
                self.assert_audit_code(report, "schema")
        for key in self.report:
            with self.subTest(missing=key):
                self.assert_audit_code({k: v for k, v in self.report.items() if k != key}, "schema")

    def test_audit_verdict_code_requires_literal_true(self):
        for value in (False, None, 1, 1.0, "true", "True", "UNTRUSTED_AUDIT_TEXT", [], {}):
            with self.subTest(value=value):
                self.assert_audit_code(self.report | {"passed": value}, "verdict")
        self.assertIs(self.control.validate_audit(self.report, self.plan, self.envelope), self.report)

    def test_audit_lists_code_preserves_string_array_limits(self):
        for key in ("security_concerns", "logic_errors", "suggestions"):
            for value in (None, {}, "UNTRUSTED_AUDIT_TEXT", [{"finding": "not a string"}], [1],
                          ["x" * 4001], [""] * 65):
                with self.subTest(key=key, kind=type(value).__name__):
                    self.assert_audit_code(self.report | {key: value}, "lists")
        for value in ([], [""] * 64, ["x" * 4000] * 64):
            report = self.report | {"suggestions": value}
            self.assertIs(self.control.validate_audit(report, self.plan, self.envelope), report)

    def test_audit_blockers_code_cannot_accept_nonempty_blocking_lists(self):
        for key in ("security_concerns", "logic_errors"):
            for value in (["UNTRUSTED_AUDIT_TEXT"], [""], ["x" * 4000] * 64):
                with self.subTest(key=key):
                    self.assert_audit_code(self.report | {key: value}, "blockers")

    def test_audit_summary_code_preserves_text_bounds(self):
        for value in (None, {}, [], 12, "", "x" * 11, "UNTRUSTED_AUDIT_TEXT" * 250):
            with self.subTest(kind=type(value).__name__):
                self.assert_audit_code(self.report | {"summary": value}, "summary")
        for value in ("x" * 12, "x" * 4000):
            report = self.report | {"summary": value}
            self.assertIs(self.control.validate_audit(report, self.plan, self.envelope), report)

    def test_audit_source_list_code_rejects_non_arrays(self):
        for value in (None, {}, "UNTRUSTED_AUDIT_TEXT", True, 1):
            with self.subTest(kind=type(value).__name__):
                self.assert_audit_code(self.report | {"source_dispositions": value}, "source-list")

    def test_audit_source_coverage_code_requires_exact_paths_once(self):
        entry = self.report["source_dispositions"][0]
        for value in ([], [entry, entry], [entry | {"source_path": "UNTRUSTED_AUDIT_TEXT"}],
                      [entry | {"source_path": "/unslop/SKILL.md"}],
                      [entry | {"source_path": "unslop/../unslop/SKILL.md"}],
                      [entry | {"source_path": 1}], [{"status": "updated", "reason": "missing path"}],
                      [None], [entry, entry | {"source_path": "extra/SKILL.md"}]):
            with self.subTest(entries=len(value)):
                self.assert_audit_code(self.report | {"source_dispositions": value}, "source-coverage")
        self.assert_audit_code(self.report, "source-coverage",
                               plan={"changed_paths": ["unslop/SKILL.md", "other/SKILL.md"]})
        other = entry | {"source_path": "other/SKILL.md"}
        report = self.report | {"source_dispositions": [other, entry]}
        plan = {"changed_paths": ["unslop/SKILL.md", "other/SKILL.md"]}
        envelope = {"updates": [{"path": path} for path in plan["changed_paths"]]}
        self.assertIs(self.control.validate_audit(report, plan, envelope), report)

    def test_audit_disposition_code_preserves_exact_fields_status_and_reason(self):
        entry = self.report["source_dispositions"][0]
        invalid = [entry | {"status": value} for value in
                   (None, True, 1, [], {}, "UNTRUSTED_AUDIT_TEXT", "Updated", "updated ")]
        invalid += [entry | {"reason": value} for value in (None, [], {}, 12, "", "x" * 11, "x" * 4001)]
        invalid += [entry | {"UNTRUSTED_AUDIT_TEXT": True},
                    {k: v for k, v in entry.items() if k != "reason"},
                    {k: v for k, v in entry.items() if k != "status"}]
        for value in invalid:
            self.assert_audit_code(self.report | {"source_dispositions": [value]}, "disposition")
        # Coverage remains complete even with an extra malformed non-path entry.
        self.assert_audit_code(self.report | {"source_dispositions": [entry, None]}, "disposition")
        for value in ("x" * 12, "x" * 4000):
            report = self.report | {"source_dispositions": [entry | {"reason": value}]}
            self.assertIs(self.control.validate_audit(report, self.plan, self.envelope), report)

    def test_audit_mapped_edit_code_requires_exact_controller_mapping(self):
        entry = self.report["source_dispositions"][0]
        for source, target in (("unslop/SKILL.md", "unslop/SKILL.md"),
                               ("agents/poteto-agent.md", "bots/poteto-agent/SOUL.md"),
                               ("agents/comment-sicko.md", "bots/comment-sicko/SOUL.md")):
            with self.subTest(source=source):
                report = self.report | {"source_dispositions": [entry | {"source_path": source}]}
                plan = {"changed_paths": [source]}
                self.assert_audit_code(report, "mapped-edit", plan=plan, envelope={"updates": []})
                self.assert_audit_code(report, "mapped-edit", plan=plan,
                                       envelope={"updates": [{"path": "UNTRUSTED_AUDIT_TEXT"}]})
                envelope = {"updates": [{"path": target}]}
                self.assertIs(self.control.validate_audit(report, plan, envelope), report)
                if source != target:
                    self.assert_audit_code(report, "mapped-edit", plan=plan,
                                           envelope={"updates": [{"path": source}]})

    def test_audit_equivalence_code_cannot_claim_edited_target_already_present(self):
        entry = self.report["source_dispositions"][0] | {"status": "already-present"}
        for source, target in (("unslop/SKILL.md", "unslop/SKILL.md"),
                               ("agents/poteto-agent.md", "bots/poteto-agent/SOUL.md"),
                               ("agents/comment-sicko.md", "bots/comment-sicko/SOUL.md")):
            with self.subTest(source=source):
                report = self.report | {"source_dispositions": [entry | {"source_path": source}]}
                plan = {"changed_paths": [source]}
                self.assert_audit_code(report, "equivalence", plan=plan,
                                       envelope={"updates": [{"path": target}]})
                self.assertIs(self.control.validate_audit(report, plan, {"updates": []}), report)


class ReviewerContractTests(unittest.TestCase):
    def test_reviewer_output_contract_states_exact_schema_and_bounds(self):
        import json
        text = (AUTOMATION / "reviewer.md").read_text()
        sample = json.loads(text.split("```json\n", 1)[1].split("```", 1)[0])
        self.assertEqual(set(sample), {"passed", "security_concerns", "logic_errors", "suggestions",
                                       "summary", "source_dispositions"})
        self.assertIs(type(sample["passed"]), bool)
        self.assertEqual(set(sample["source_dispositions"][0]), {"source_path", "status", "reason"})
        for required in (
                "exactly these six fields", "literal JSON boolean", "never a string or number",
                "`security_concerns`, `logic_errors`, and `suggestions`",
                "each an array of 0..64 strings, not objects", "Each string is at most 4000 characters",
                "`summary`: a string of 12..4000 characters",
                "objects with exactly `source_path`, `status`, and `reason`, and no other fields",
                "`reason`: a string of 12..4000 characters",
                "the exact controller-listed changed path, without normalization",
                "`agents/poteto-agent.md` maps to `bots/poteto-agent/SOUL.md`",
                "`agents/comment-sicko.md` maps to `bots/comment-sicko/SOUL.md`",
                "`already-present` with a mapped edit also blocks acceptance"):
            with self.subTest(required=required):
                self.assertIn(required, text)


    def test_reviewer_must_write_and_read_back_the_report_without_scope_expansion(self):
        text = (AUTOMATION / "reviewer.md").read_text()
        for required in ("Write only `/out/audit.json`", "with the native file tools",
                         "then read back `/out/audit.json` with the native file tools",
                         "JSON CLI output is not report creation",
                         "Tool or permission errors do not authorize broader tools, writes, or scope",
                         "Fail closed without shell workarounds",
                         "Do not fabricate a tool run", "independent same-model review context",
                         "not independent model-family evidence"):
            with self.subTest(required=required):
                self.assertIn(required, text)


if __name__ == "__main__":
    unittest.main()

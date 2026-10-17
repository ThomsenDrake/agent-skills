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


if __name__ == "__main__":
    unittest.main()

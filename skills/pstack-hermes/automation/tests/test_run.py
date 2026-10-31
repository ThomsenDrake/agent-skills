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
        for role, report_dir in (("reviewer", Path("/fixture/report")),
                                 ("reviewer", None), ("writer", Path("/fixture/report"))):
            with self.subTest(role=role, report_dir=report_dir), self.assertRaises(ValueError):
                run.worker_command(role=role, report_dir=report_dir, **args)
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
    def setUp(self):
        import hashlib
        self.control = controller(self)
        plan = {"schema": 1, "changed_paths": ["unslop/SKILL.md"], "base_commit": "a" * 40,
                "base_source_commit": "b" * 40, "base_source_tree": "c" * 40,
                "source_commit": "a" * 40, "source_tree": "d" * 40, "adaptation_tree": "e" * 40}
        self.wrapper = {"schema": 1, "mode": "reconcile", "checkout_ref": "a" * 40,
                        "plan": plan, "publication": {}}
        self.envelope = {key: plan[key] for key in ("schema", "base_commit", "base_source_commit", "base_source_tree",
                                                   "source_commit", "source_tree", "adaptation_tree")}
        self.before = "---\nname: unslop\ndescription: Remove unnecessary text.\n---\nOld rule.\n"
        after = self.before.replace("Old rule.", "New rule.")
        self.envelope["updates"] = [{"path": "unslop/SKILL.md", "content": after,
                                     "before_sha256": hashlib.sha256(self.before.encode()).hexdigest(),
                                     "after_sha256": hashlib.sha256(after.encode()).hexdigest()}]
        self.packet = {"schema": 2, "plan": self.wrapper, "candidate": self.envelope,
                       "receipts": {"writer": {}}, "runs": {"writer": {}}}

    def stage_evidence(self):
        import engine
        self.wrapper["plan"]["noop"] = False
        self.packet["receipts"]["writer"] = {
            "request_count": 1, "upstream_request_count": 1, "successful_2xx": 1,
            "total_request_bytes": 100, "max_request_bytes": 262144, "max_total_request_bytes": 1500000,
            "model_ids_submitted": [engine.MODEL], "errors": {}, "status": "closed",
            "started_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:01+00:00",
            "elapsed_seconds": 1, "deadline_seconds": 1200}
        self.packet["runs"]["writer"] = {
            "bindings": dict(engine.BINDINGS), "cost_usd": 0.01,
            "usage": {"input_tokens": 10, "output_tokens": 5, "cached_input_tokens": 0, "total_tokens": 15}}
        return {"contract_tests": True, "updater_tests": True, "helper_tests": True, "helper_typecheck": True,
                "native": {"cli_passed": True, "inference_performed": False,
                           "loaded_skills": 55, "loaded_support_files": 62}}

    def test_schema_two_accepts_only_writer_evidence(self):
        import copy
        before = copy.deepcopy(self.packet)
        self.assertIs(self.control.packet_candidate(self.wrapper, self.packet), self.envelope)
        self.assertEqual(self.packet, before)

    def test_legacy_mixed_missing_or_extra_evidence_is_rejected(self):
        import copy
        for schema in (1, True, "2", 2.0):
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                self.control.packet_candidate(self.wrapper, self.packet | {"schema": schema})
        legacy = copy.deepcopy(self.packet)
        legacy["schema"] = 1
        legacy["audit"] = {}
        for key in ("receipts", "runs"):
            legacy[key]["reviewer"] = {}
        with self.assertRaises(ValueError):
            self.control.packet_candidate(self.wrapper, legacy)
        for key in self.packet:
            with self.subTest(missing=key), self.assertRaises(ValueError):
                self.control.packet_candidate(self.wrapper, {k: v for k, v in self.packet.items() if k != key})
        for key in ("audit", "reviewer", "unexpected"):
            with self.subTest(extra=key), self.assertRaises(ValueError):
                self.control.packet_candidate(self.wrapper, self.packet | {key: {}})
        for key in ("receipts", "runs"):
            for evidence in ({}, {"reviewer": {}}, {"writer": {}, "reviewer": {}},
                             {"writer": {}, "extra": {}}, None, []):
                with self.subTest(key=key, evidence=evidence), self.assertRaises(ValueError):
                    self.control.packet_candidate(self.wrapper, self.packet | {key: evidence})

    def test_artifact_cannot_change_the_protected_plan_or_source_bindings(self):
        import copy
        changed = copy.deepcopy(self.packet)
        changed["plan"]["mode"] = "fixture"
        with self.assertRaises(ValueError):
            self.control.packet_candidate(self.wrapper, changed)
        for key in self.envelope:
            if key == "updates":
                continue
            changed = copy.deepcopy(self.packet)
            changed["candidate"][key] = "f" * 40
            with self.subTest(binding=key), self.assertRaises(ValueError):
                self.control.packet_candidate(self.wrapper, changed)

    def test_candidate_envelope_and_updates_have_closed_shapes(self):
        import copy
        cases = [None, self.envelope | {"audit": {}}, self.envelope | {"schema": True}]
        cases += [{k: v for k, v in self.envelope.items() if k != key} for key in self.envelope]
        update = self.envelope["updates"][0]
        cases += [self.envelope | {"updates": value} for value in (None, {}, "updates", [None])]
        cases += [self.envelope | {"updates": [update | {"audit": {}}]}]
        cases += [self.envelope | {"updates": [{k: v for k, v in update.items() if k != key}]}
                  for key in update]
        for envelope in cases:
            packet = copy.deepcopy(self.packet)
            packet["candidate"] = envelope
            with self.subTest(envelope=envelope), self.assertRaises(ValueError):
                self.control.packet_candidate(self.wrapper, packet)

    def test_verifier_runs_protected_checks_before_emitting_writer_only_artifact(self):
        from contextlib import redirect_stdout
        import engine
        import io
        import tempfile
        from unittest import mock
        checks = self.stage_evidence()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, out = root / "repo", root / "verified"
            with (mock.patch.object(self.control, "restore_plan", return_value=self.wrapper["plan"]),
                  mock.patch("protocol.apply") as apply,
                  mock.patch.object(self.control, "git_text", return_value=self.before),
                  mock.patch.object(engine, "validate_receipt", wraps=engine.validate_receipt) as receipt,
                  mock.patch.object(engine, "validate_run", wraps=engine.validate_run) as metrics,
                  mock.patch.object(self.control, "run_checks", return_value=checks) as protected,
                  redirect_stdout(io.StringIO())):
                verified = self.control.verify_command(repo, self.wrapper, self.packet, out)
            apply.assert_called_once_with(repo, self.envelope)
            receipt.assert_called_once_with(self.packet["receipts"]["writer"])
            metrics.assert_called_once_with(self.packet["runs"]["writer"])
            protected.assert_called_once_with(repo, out)
            self.assertEqual(set(verified), {"schema", "plan", "candidate", "receipts", "runs", "checks"})
            self.assertEqual(verified, self.packet | {"checks": checks})
            self.assertEqual(self.control.read_json(out / "verified.json"), verified)

    def test_publisher_accepts_checked_writer_only_artifact_with_original_probe(self):
        from contextlib import redirect_stdout
        import engine
        import io
        from unittest import mock
        checks = self.stage_evidence()
        verified = self.packet | {"checks": checks}
        repo = Path("/unused-publication-checkout")
        with (mock.patch.object(self.control, "restore_plan", return_value=self.wrapper["plan"]),
              mock.patch.object(self.control, "git_text", return_value=self.before),
              mock.patch.object(engine, "validate_receipt", wraps=engine.validate_receipt) as receipt,
              mock.patch.object(engine, "validate_run", wraps=engine.validate_run) as metrics,
              mock.patch("publish.publish", return_value={"action": "created"}) as publisher,
              redirect_stdout(io.StringIO())):
            result = self.control.publish_command(repo, verified, self.control.REPOSITORY)
        self.assertEqual(result, {"action": "created"})
        receipt.assert_called_once_with(self.packet["receipts"]["writer"])
        metrics.assert_called_once_with(self.packet["runs"]["writer"])
        publisher.assert_called_once_with(repo, self.envelope, self.control.REPOSITORY,
                                          expected_probe=self.wrapper["publication"])

    def test_publisher_requires_completed_protected_checks_not_writer_claims(self):
        import copy
        from unittest import mock
        checks = self.stage_evidence()
        invalid = [None, {}, checks | {"audit": {}}]
        for key in ("contract_tests", "updater_tests", "helper_tests", "helper_typecheck"):
            for value in (False, None, "true", 1):
                invalid.append(checks | {key: value})
            invalid.append({k: v for k, v in checks.items() if k != key})
        invalid += [checks | {"native": value} for value in (None, {},
                    checks["native"] | {"cli_passed": False},
                    checks["native"] | {"loaded_skills": 54},
                    checks["native"] | {"inference_performed": True})]
        with (mock.patch.object(self.control, "restore_plan") as restore,
              mock.patch("publish.publish") as publisher):
            for evidence in invalid:
                verified = copy.deepcopy(self.packet) | {"checks": evidence}
                with self.subTest(evidence=evidence), self.assertRaisesRegex(ValueError, "protected checks"):
                    self.control.publish_command(Path("/unused-checkout"), verified, self.control.REPOSITORY)
            restore.assert_not_called()
            publisher.assert_not_called()
        for mutation in ("missing-checks", "audit", "old-schema"):
            verified = copy.deepcopy(self.packet) | {"checks": checks}
            if mutation == "missing-checks":
                del verified["checks"]
            elif mutation == "audit":
                verified["audit"] = {}
            else:
                verified["schema"] = 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.control.publish_command(Path("/unused-checkout"), verified, self.control.REPOSITORY)

    def test_failed_protected_checks_never_emit_a_verified_artifact(self):
        import subprocess
        import tempfile
        from unittest import mock
        self.stage_evidence()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, out = root / "repo", root / "verified"
            with (mock.patch.object(self.control, "restore_plan", return_value=self.wrapper["plan"]),
                  mock.patch("protocol.apply"),
                  mock.patch.object(self.control, "git_text", return_value=self.before),
                  mock.patch.object(self.control, "run_checks", side_effect=subprocess.CalledProcessError(1, "protected")) as protected):
                with self.assertRaises(subprocess.CalledProcessError):
                    self.control.verify_command(repo, self.wrapper, self.packet, out)
            protected.assert_called_once_with(repo, out)
            self.assertFalse((out / "verified.json").exists())

    def test_writer_receipt_and_run_are_validated_before_any_effects(self):
        import copy
        import tempfile
        from unittest import mock
        checks = self.stage_evidence()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, out = root / "repo", root / "verified"
            with (mock.patch.object(self.control, "restore_plan", return_value=self.wrapper["plan"]),
                  mock.patch("protocol.apply") as apply,
                  mock.patch.object(self.control, "run_checks") as protected,
                  mock.patch("publish.publish") as publisher):
                for key in ("receipts", "runs"):
                    packet = copy.deepcopy(self.packet)
                    packet[key]["writer"] = {}
                    with self.subTest(evidence=key):
                        with self.assertRaises(ValueError):
                            self.control.verify_command(repo, self.wrapper, packet, out)
                        with self.assertRaises(ValueError):
                            self.control.publish_command(repo, packet | {"checks": checks}, self.control.REPOSITORY)
                apply.assert_not_called()
                protected.assert_not_called()
                publisher.assert_not_called()
                self.assertFalse(out.exists())

    def test_empty_adaptation_cannot_verify_or_publish_a_checkpoint(self):
        from unittest import mock
        checks = self.stage_evidence()
        self.packet["candidate"]["updates"] = []
        with (mock.patch.object(self.control, "restore_plan") as restore,
              mock.patch("protocol.apply") as apply,
              mock.patch("publish.publish") as publisher):
            with self.assertRaisesRegex(ValueError, "manual review"):
                self.control.verify_command(Path("/unused-checkout"), self.wrapper, self.packet, Path("/unused-output"))
            with self.assertRaisesRegex(ValueError, "manual review"):
                self.control.publish_command(Path("/unused-checkout"), self.packet | {"checks": checks}, self.control.REPOSITORY)
            restore.assert_not_called()
            apply.assert_not_called()
            publisher.assert_not_called()

    def test_each_changed_source_requires_its_exact_mapped_edit(self):
        import copy
        mappings = (("unslop/SKILL.md", "unslop/SKILL.md"),
                    ("agents/poteto-agent.md", "bots/poteto-agent/SOUL.md"),
                    ("agents/comment-sicko.md", "bots/comment-sicko/SOUL.md"))
        for source, target in mappings:
            wrapper = copy.deepcopy(self.wrapper)
            wrapper["plan"]["changed_paths"] = [source]
            packet = copy.deepcopy(self.packet)
            packet["plan"] = wrapper
            update = packet["candidate"]["updates"][0] | {"path": target}
            packet["candidate"]["updates"] = [update]
            with self.subTest(source=source):
                self.assertIs(self.control.packet_candidate(wrapper, packet), packet["candidate"])
                for updates in ([], [update | {"path": "SKILL.md"}]):
                    packet["candidate"]["updates"] = updates
                    with self.subTest(updates=updates), self.assertRaisesRegex(ValueError, "manual review"):
                        self.control.packet_candidate(wrapper, packet)
                if source != target:
                    packet["candidate"]["updates"] = [update | {"path": source}]
                    with self.assertRaisesRegex(ValueError, "manual review"):
                        self.control.packet_candidate(wrapper, packet)
        wrapper = copy.deepcopy(self.wrapper)
        wrapper["plan"]["changed_paths"].append("agents/poteto-agent.md")
        packet = copy.deepcopy(self.packet)
        packet["plan"] = wrapper
        with self.assertRaisesRegex(ValueError, "manual review"):
            self.control.packet_candidate(wrapper, packet)
        packet["candidate"]["updates"].append(packet["candidate"]["updates"][0]
                                               | {"path": "bots/poteto-agent/SOUL.md"})
        self.assertIs(self.control.packet_candidate(wrapper, packet), packet["candidate"])


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
        self.assertIn("--editable", calls[1][0])
        self.assertIn("git+https://github.com/NousResearch/hermes-agent.git@" + pins["hermes_commit"] + "#egg=hermes-agent", calls[1][0])
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
    def test_automated_audit_gate_is_removed_not_reported_as_passed(self):
        run = controller(self)
        for name in ("AuditError", "AUDIT_REJECTION_CODES", "validate_audit"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(run, name), "automated audit must not remain an acceptance gate")

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


if __name__ == "__main__":
    unittest.main()

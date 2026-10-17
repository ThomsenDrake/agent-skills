"""Contracts for trusted orchestration and the credential boundary."""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "skills/pstack-hermes"


class BootstrapTests(unittest.TestCase):
    def test_runtime_pins_vibe_model_actions_and_hermes_revision(self):
        path = PACKAGE / "automation/runtime.json"
        self.assertTrue(path.is_file(), "missing reviewed runtime pins")
        config = json.loads(path.read_text())
        self.assertEqual(config["vibe_version"], "2.26.1")
        self.assertEqual(config["model"], "mistral-large-4")
        self.assertRegex(config["hermes_commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(set(config["actions"]), {"actions/checkout", "actions/setup-python",
                         "actions/upload-artifact", "actions/download-artifact", "oven-sh/setup-bun"})
        for value in config["actions"].values():
            self.assertRegex(value, r"^[0-9a-f]{40}$")

    def test_baseline_manifest_pins_the_accepted_source_tree(self):
        path = PACKAGE / "UPSTREAM.json"
        self.assertTrue(path.is_file(), "missing accepted-source checkpoint")
        manifest = json.loads(path.read_text())
        self.assertEqual(manifest["schema"], 1)
        self.assertEqual(set(manifest), {"schema", "source_commit", "source_tree"})
        self.assertRegex(manifest["source_commit"], r"^[0-9a-f]{40}$")
        actual = subprocess.check_output(
            ["git", "rev-parse", manifest["source_commit"] + ":skills/pstack"],
            cwd=ROOT, text=True,
        ).strip()
        self.assertEqual(manifest["source_tree"], actual)


class WorkflowTests(unittest.TestCase):
    def test_worker_image_and_offline_policy_checks_are_separate_from_secret_use(self):
        from ruamel.yaml import YAML
        data = YAML(typ="safe").load((ROOT / ".github/workflows/update-pstack-hermes.yml").read_text())
        steps = data["jobs"]["adapt"]["steps"]
        build = next(step for step in steps if step.get("name") == "Build the pinned file-only Vibe worker")
        self.assertIn("--platform linux/amd64", build["run"])
        checks = [step for step in steps if step.get("name") == "Run released Vibe policy checks offline"]
        self.assertEqual(len(checks), 1, "missing offline released-runtime check")
        self.assertIn("--network none", checks[0]["run"])
        self.assertIn("test_vibe_entry.py", checks[0]["run"])
        self.assertNotIn("MISTRAL_API_KEY", str(checks[0].get("env", {})))

    def test_install_index_explains_repository_proposals_not_profile_updates(self):
        text = (PACKAGE / "SKILL.md").read_text()
        self.assertIn("proposes", text)
        self.assertIn("does not update installed profiles", text)
        readme = (ROOT / "README.md").read_text()
        self.assertIn("Automatic pstack-hermes updates", readme)
        self.assertIn("Mistral Large 4", readme)
        self.assertIn("manual", readme.lower())

    def test_fixture_dispatch_cannot_run_the_vendor_sync(self):
        from ruamel.yaml import YAML
        data = YAML(typ="safe").load((ROOT / ".github/workflows/update-pstack.yml").read_text())
        dispatch = data["on"]["workflow_dispatch"]
        self.assertIsInstance(dispatch, dict, "missing non-destructive verification dispatch")
        self.assertEqual(dispatch["inputs"]["verify_updater"]["type"], "boolean")
        self.assertFalse(dispatch["inputs"]["verify_updater"]["default"])
        self.assertIn("!inputs.verify_updater", data["jobs"]["sync"]["if"])
        fixture = data["jobs"]["verify-updater"]
        self.assertIn("inputs.verify_updater", fixture["if"])
        self.assertEqual(fixture["uses"], "./.github/workflows/update-pstack-hermes.yml")
        self.assertEqual(fixture["with"]["mode"], "fixture")

    def test_pipeline_has_completion_trigger_and_separate_publisher_authority(self):
        path = ROOT / ".github/workflows/update-pstack-hermes.yml"
        self.assertTrue(path.is_file(), "missing deployed updater workflow")
        from ruamel.yaml import YAML
        data = YAML(typ="safe").load(path.read_text())
        self.assertEqual(data["permissions"], {})
        self.assertIn("Update pstack from cursor/plugins", data["on"]["workflow_run"]["workflows"])
        self.assertIn("workflow_dispatch", data["on"])
        self.assertIn("schedule", data["on"])
        self.assertFalse(data["concurrency"]["cancel-in-progress"])
        jobs = data["jobs"]
        self.assertEqual(set(jobs), {"plan", "adapt", "verify", "publish"})
        for name in ("plan", "adapt", "verify"):
            self.assertEqual(jobs[name]["permissions"]["contents"], "read")
        self.assertEqual(jobs["publish"]["permissions"]["contents"], "write")
        self.assertEqual(jobs["publish"]["permissions"]["pull-requests"], "write")
        self.assertIn("needs.verify.result == 'success'", jobs["publish"]["if"])
        self.assertIn("fixture", jobs["publish"]["if"])
        for job in jobs.values():
            for step in job["steps"]:
                if step.get("uses", "").startswith("actions/checkout@"):
                    self.assertRegex(step["uses"], r"@[0-9a-f]{40}$")
                    self.assertFalse(step["with"]["persist-credentials"])
        verify_text = str(jobs["verify"])
        self.assertNotIn("secrets.MISTRAL_API_KEY", verify_text)
        self.assertIn("artifact-ids", verify_text)
        self.assertNotIn("secrets.MISTRAL_API_KEY", str(jobs["publish"]))


class PromptTests(unittest.TestCase):
    def test_reviewer_contract_is_independent_and_fail_closed(self):
        path = PACKAGE / "automation/reviewer.md"
        self.assertTrue(path.is_file(), "missing independent review contract")
        text = path.read_text()
        for required in ("independent", "audit.json", '"passed"', '"security_concerns"',
                         '"logic_errors"', '"source_dispositions"', "untrusted data", "Do not edit", "same-model"):
            self.assertIn(required, text)

    def test_writer_prompt_separates_runtime_tools_from_output_contract(self):
        path = PACKAGE / "automation/writer.md"
        self.assertTrue(path.is_file(), "missing Vibe-native update contract")
        text = path.read_text()
        for required in ("Vibe", "untrusted data", "old-upstream", "new-upstream",
                         "current-hermes", "candidate", "Do not run shell commands",
                         "Do not change tests", "same-model", "goal", "context"):
            self.assertIn(required, text)


if __name__ == "__main__":
    unittest.main()

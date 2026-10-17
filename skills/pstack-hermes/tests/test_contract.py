"""Offline acceptance checks for the Hermes adaptation.

Run from the repository root with Hermes's Python:
python -m unittest discover -s skills/pstack-hermes/tests -v
"""
import ast
import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest import mock

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT.with_name("pstack")


class LayoutTests(unittest.TestCase):
    def test_preserves_all_54_skill_directories(self):
        expected = {p.parent.name for p in UPSTREAM.glob("*/SKILL.md")}
        actual = {p.parent.name for p in ROOT.glob("*/SKILL.md")}
        self.assertEqual(len(expected), 54)
        self.assertEqual(actual, expected)


class MetadataTests(unittest.TestCase):
    def test_bot_copy_recipe_excludes_dependencies_and_test_caches(self):
        text = (ROOT / "bots/README.md").read_text()
        blocks = re.findall(r"```python\n(.*?)```", text, re.DOTALL)
        patterns = set()
        for block in blocks:
            if "shutil.copytree" not in block:
                continue
            for node in ast.walk(ast.parse(block)):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "shutil"
                        and node.func.attr == "ignore_patterns"):
                    patterns.update(ast.literal_eval(arg) for arg in node.args)
        required = {"node_modules", "__pycache__", "*.pyc", ".pytest_cache",
                    ".mypy_cache", ".ruff_cache"}
        self.assertFalse(required - patterns,
                         f"copy recipe misses exclusions: {sorted(required - patterns)}")

    def test_helper_docs_identify_the_actual_forge_support(self):
        text = (ROOT / "poteto-mode/scripts/README.md").read_text()
        self.assertTrue("The watcher is GitHub-only through `gh`" in text,
                        "watcher incorrectly promises an Origin fallback")
        self.assertTrue("The orchestrator can use optional Origin" in text,
                        "optional Origin support belongs to the orchestrator")

    def test_every_skill_has_loadable_hermes_metadata(self):
        skills = sorted(ROOT.rglob("SKILL.md"))
        self.assertEqual(len(skills), 55)
        names = []
        for path in skills:
            with self.subTest(skill=str(path.relative_to(ROOT))):
                text = path.read_text()
                self.assertTrue(text.startswith("---\n"))
                _, header, body = text.split("---\n", 2)
                metadata = YAML(typ="safe").load(header)
                self.assertEqual(metadata["name"], path.parent.name)
                description = metadata["description"]
                self.assertIsInstance(description, str)
                self.assertLessEqual(len(description), 57)
                self.assertTrue(description.startswith("Use when "))
                self.assertTrue(description.endswith("."))
                self.assertIn("Hermes", metadata["compatibility"])
                self.assertTrue(body.strip())
                self.assertNotIn("disable-model-invocation", metadata)
                names.append(metadata["name"])
        self.assertEqual(len(names), len(set(names)))

    def test_prose_has_no_cursor_harness_contract(self):
        forbidden = re.compile(
            r"~/\.cursor|~/\.agents|\.cursor/(?:rules|skills|plugins)|"
            r"subagent_type|run_in_background|AskQuestion|AskUserQuestion|"
            r"\bTask\s*\(|\bTask tool|\bcursor-team-kit\b|"
            r"claude-opus-5-5|grok-4\.7-(?:xhigh|high|medium)|"
            r"[\u2013\u2014]"
        )
        for path in sorted(ROOT.rglob("*.md")):
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertIsNone(forbidden.search(path.read_text()))

    def test_bot_skeletons_exist(self):
        for name in ("poteto-agent", "comment-sicko"):
            soul = ROOT / "bots" / name / "SOUL.md"
            with self.subTest(bot=name):
                self.assertTrue(soul.is_file())
                text = soul.read_text()
                for heading in ("## One job", "## Anti-jobs", "## Voice", "## Wake"):
                    self.assertIn(heading, text)

    def test_retains_every_upstream_support_file(self):
        for source in sorted(UPSTREAM.rglob("*")):
            relative = source.relative_to(UPSTREAM)
            if not source.is_file() or relative.parts[0] == "agents":
                continue
            with self.subTest(file=str(relative)):
                target = ROOT / relative
                self.assertTrue(target.is_file())
                if source.suffix.lower() != ".md":
                    self.assertEqual(source.read_bytes(), target.read_bytes(),
                                     f"{relative}: retained bytes differ")
                    self.assertEqual(source.stat().st_mode & 0o111,
                                     target.stat().st_mode & 0o111,
                                     f"{relative}: retained executable bits differ")


class SourceIntegrityTests(unittest.TestCase):
    def test_retained_support_check_rejects_byte_or_executable_drift(self):
        for kind in ("bytes", "executable bits"):
            with self.subTest(drift=kind):
                with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as scratch:
                    fixture = Path(scratch) / "pstack-hermes"
                    shutil.copytree(UPSTREAM, fixture)
                    target = fixture / "show-me-your-work/scripts/log.sh"
                    if kind == "bytes":
                        target.write_bytes(target.read_bytes() + b"\ncontract mutation\n")
                    else:
                        target.chmod((target.stat().st_mode & 0o777) ^ 0o100)
                    with mock.patch(f"{__name__}.ROOT", fixture):
                        with self.assertRaisesRegex(AssertionError, f"retained {kind} differ"):
                            MetadataTests().test_retains_every_upstream_support_file()


class ReviewContractTests(unittest.TestCase):
    def test_poteto_mode_describes_default_panel_without_fake_diversity(self):
        text = (ROOT / "poteto-mode/SKILL.md").read_text()
        self.assertTrue("multi-model adversarial" not in text,
                        "default adversarial roles are not model diversity")
        self.assertIn("adversarial panel with optional verified model diversity", text)

    def test_every_delegated_pr_has_parent_owned_review_before_publication(self):
        problems = []
        opening = (ROOT / "poteto-mode/playbooks/opening-a-pr.md").read_text()
        for required in (
            "Every delegated PR", "before any PR-facing publication",
            "After the code delegate returns", "skill_view(name='interrogate')",
            "skill_view(name='no-comments')", "independent reviewer leaves",
            "Do not ask a code leaf to run `interrogate` or `no-comments`",
            "report the publication gate blocked",
        ):
            if required not in opening:
                problems.append(f"opening-a-pr: missing {required!r}")
        if "runs design review when required" in opening:
            problems.append("mandatory delegated-PR review was weakened to optional design review")
        if re.search(r"A bounded code delegate[^\n]*skill_view\(name='no-comments'", opening):
            problems.append("code leaf still owns a recursive no-comments dispatch")
        for relative in (
            "poteto-mode/SKILL.md",
            "poteto-mode/playbooks/opening-a-pr.md",
            "poteto-mode/playbooks/autopilot-full.md",
            "poteto-mode/playbooks/multi-phase-plan.md",
        ):
            if "parent-owned delegated-PR gate" not in (ROOT / relative).read_text():
                problems.append(f"{relative}: missing mandatory parent-owned gate")
        self.assertFalse(problems, "\n".join(problems))


class SafetyTests(unittest.TestCase):
    def test_merge_recipes_bind_the_accepted_head(self):
        problems = []
        recipe = "gh pr merge <pr> --squash --match-head-commit <verified-head-sha>"
        for relative in (
            "poteto-mode/playbooks/shipping.md",
            "poteto-mode/playbooks/autopilot-full.md",
            "poteto-mode/playbooks/multi-phase-plan.md",
        ):
            text = (ROOT / relative).read_text()
            for required in (recipe, "accepted current verdict", "stop and reverify",
                             "Do not arm auto-merge", "immutable head semantics"):
                if required not in text:
                    problems.append(f"{relative}: missing {required!r}")
        for path in ROOT.rglob("*.md"):
            for command in re.findall(r"gh pr merge[^'\"`\n]*", path.read_text()):
                if "--match-head-commit <verified-head-sha>" not in command:
                    problems.append(f"{path.relative_to(ROOT)}: unpinned merge command")
                if "--admin" in command or "--auto" in command:
                    problems.append(f"{path.relative_to(ROOT)}: bypass/deferred merge command")
        shipping = (ROOT / "poteto-mode/playbooks/shipping.md").read_text()
        if "--json state,mergedAt,baseRefName,headRefOid,mergeCommit" not in shipping:
            problems.append("shipping must read back the exact merged PR")
        self.assertFalse(problems, "\n".join(problems))

    def test_oneshot_launches_require_explicit_bypass_authorization(self):
        reference = ROOT / "references/one-shot-safety.md"
        problems = []
        if not reference.is_file():
            problems.append("missing shared one-shot safety reference")
        else:
            text = reference.read_text()
            for required in (
                "HERMES_YOLO_MODE=1", "HERMES_ACCEPT_HOOKS=1",
                "not a security sandbox", "approval-preserving interactive",
                "No flag makes `-z` preserve approvals",
            ):
                if required not in text:
                    problems.append(f"safety reference lacks {required!r}")
        # Include indirect profile-process recipes, not only literal -z commands.
        call_sites = {
            "swarm/SKILL.md", "figure-it-out/SKILL.md",
            "interrogate/SKILL.md", "blast-radius/SKILL.md",
            "show-me-your-work/SKILL.md", "setup-pstack/references/config-readback.md",
            "bots/poteto-agent/SOUL.md", "bots/comment-sicko/SOUL.md",
            "poteto-mode/playbooks/feature.md", "poteto-mode/playbooks/bug-fix.md",
        }
        for path in ROOT.rglob("*.md"):
            if re.search(r"\bhermes\b[^\n]*\s(?:-z|--oneshot)\b", path.read_text()):
                call_sites.add(str(path.relative_to(ROOT)))
        gate = "skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')"
        for relative in sorted(call_sites):
            text = (ROOT / relative).read_text()
            required = (
                gate, "bypasses command and hook approval gates",
                "explicit authorization for that bypass", "review inherited hooks",
                "restricted execution boundaries", "scoped credentials", "minimal toolsets",
                "Model-diversity or unattended-work requests are not bypass authorization",
                "bounded parent-driven delegates", "approval-preserving interactive session",
                "report blocked",
            )
            missing = [item for item in required if item not in text]
            if missing:
                problems.append(f"{relative}: missing one-shot preconditions")
        plan = (ROOT / "poteto-mode/playbooks/multi-phase-plan.md").read_text()
        template = re.search(r"````markdown\n(.*?)````", plan, re.DOTALL)
        self.assertIsNotNone(template, "missing executable-plan template")
        if template is not None and gate not in template.group(1):
            problems.append("copied plan loses the profile-process launch gate")
        evidence = (ROOT / "references/verification.md").read_text()
        if "No OS sandbox was verified" not in evidence:
            problems.append("smoke record must disclose its actual isolation limit")
        self.assertFalse(problems, "\n".join(problems))


if __name__ == "__main__":
    unittest.main()

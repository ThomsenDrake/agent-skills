import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sync  # noqa: E402

# Ignore the developer's git config, such as commit signing.
os.environ.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

GENERATOR = textwrap.dedent("""\
    const TERMS = [
      { key: "`AskQuestion`", re: /AskQuestion/ },
      { key: "todolist", re: /\\btodo ?list\\b/i },
      { key: "`environment: \\"cloud\\"`", re: /environment: "(cloud|local)"/ },
    ];
    """)

INDEX = textwrap.dedent("""\
    ---
    name: pstack
    description: Index.
    ---
    # pstack

    This copy follows upstream pstack v1.0.0 at commit 0000000.
    """)


def sh(cwd, *args):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def write(root, files):
    for path, text in files.items():
        target = Path(root, path)
        if text is None:
            target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(text))


def commit(repo, message):
    sh(repo, "git", "add", "-A")
    sh(repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)
    return sh(repo, "git", "rev-parse", "HEAD").strip()


ALPHA = ("Ask with AskQuestion first{first}.\n\nOne.\n\nTwo.\n\nThree.\n\nKeep this line{keep}.\n\n"
         "See [guide](../../docs/guide/01.md) and [agent](../../agents/poteto-agent.md).\n")


def skill(name, body, extra=""):
    return f"---\nname: {name}\ndescription: The {name} skill.\n{extra}---\n\n# {name}\n\n{body}"


NEUTRAL = {
    "Ask with AskQuestion first, always.": "Ask the user first, always.",
    "Prefer AskQuestion over free text.": "Prefer a multiple-choice question over free text.",
}
CONFLICT = re.compile(r"^<<<<<<< .*?\n.*?^=======\n(.*?)^>>>>>>> .*?\n", re.S | re.M)


class Stub:
    """Stands in for Mistral: takes upstream's side of each conflict and rewrites the known Cursor phrases."""

    def __init__(self):
        self.calls = []

    def __call__(self, messages):
        user = messages[1]["content"]
        self.calls.append(re.search(r"<path>(.*)</path>", user).group(1))
        text = CONFLICT.sub(r"\1", re.search(r"<draft>\n(.*?)</draft>", user, re.S).group(1))
        for cursor, neutral in NEUTRAL.items():
            text = text.replace(cursor, neutral)
        return f"<file>\n{text}</file>"


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.up, self.repo = root / "up", root / "repo"
        self.up.mkdir()
        self.repo.mkdir()
        sh(self.up, "git", "init", "-q", "-b", "main")
        write(self.up, {
            "pstack/plugin.json": '{"name": "pstack", "version": "1.0.0"}\n',
            "pstack/LICENSE": "MIT\n",
            "pstack/docs/guide/01.md": "guide\n",
            "pstack/agents/poteto-agent.md": "---\nname: poteto-agent\n---\nRead [mode](../skills/alpha/SKILL.md).\n",
            "pstack/skills/alpha/SKILL.md": skill("Alpha", ALPHA.format(first="", keep=""), "disable-model-invocation: true\n"),
            "pstack/skills/epsilon/SKILL.md": skill("epsilon", "Use AskQuestion here.\n\nA.\n\nB.\n\nC.\n\nEnd line.\n"),
            "pstack/skills/beta/SKILL.md": skill("beta", "Beta line one.\n"),
            "pstack/skills/beta/ref.md": "Reference text for beta.\nSecond line.\nThird line.\n",
            "pstack/skills/gamma/SKILL.md": skill("gamma", "Gamma.\n"),
            "pstack/skills/gamma/notes.md": "Old notes.\n",
            "pstack/skills/kit/run.sh": "#!/bin/sh\necho hi\n",
            "scripts/generate-pstack-harness-trees.mjs": GENERATOR,
        })
        os.chmod(self.up / "pstack/skills/kit/run.sh", 0o755)
        self.c1 = commit(self.up, "v1")

        sh(self.repo, "git", "init", "-q", "-b", "main")
        write(self.repo, {"skills/pstack/SKILL.md": INDEX,
                          "README.md": "| [`pstack`] | [cursor/plugins pstack](https://x) v1.0.0 |\n"})
        sync.bootstrap(self.repo, self.c1, self.up)
        for path, cursor, neutral in (("alpha", "Ask with AskQuestion first.", "Ask the user first."),
                                      ("epsilon", "Use AskQuestion here.", "Ask the user here.")):
            target = self.repo / "skills/pstack" / path / "SKILL.md"
            target.write_text(target.read_text().replace(cursor, neutral))
        self.base = commit(self.repo, "neutral v1")

    def tearDown(self):
        self.tmp.cleanup()

    def upstream_v2(self):
        write(self.up, {
            "pstack/plugin.json": '{"name": "pstack", "version": "1.1.0"}\n',
            "pstack/skills/alpha/SKILL.md": skill("Alpha", ALPHA.format(first=", always", keep=", now longer"),
                                                  "disable-model-invocation: true\n"),
            "pstack/skills/epsilon/SKILL.md": skill("epsilon", "Use AskQuestion here.\n\nA.\n\nB.\n\nC.\n\nEnd line, changed.\n"),
            "pstack/skills/beta/SKILL.md": skill("beta", "Beta line one.\nBeta line two.\n"),
            "pstack/skills/beta/ref.md": None,
            "pstack/skills/beta/reference.md": "Reference text for beta.\nSecond line.\nThird line.\n",
            "pstack/skills/gamma/notes.md": None,
            "pstack/skills/delta/SKILL.md": skill("delta", "Prefer AskQuestion over free text.\n"),
        })
        return commit(self.up, "v2")

    def build(self, model=None, env_key=None):
        out = Path(self.tmp.name) / f"out{len(list(Path(self.tmp.name).glob('out*')))}"
        old = os.environ.pop("MISTRAL_API_KEY", None)
        if env_key:
            os.environ["MISTRAL_API_KEY"] = env_key
        try:
            return sync.build(self.repo, out, self.up, model=model), out
        finally:
            os.environ.pop("MISTRAL_API_KEY", None)
            if old is not None:
                os.environ["MISTRAL_API_KEY"] = old

    def read(self, path):
        return (self.repo / "skills/pstack" / path).read_text()


class TransformTests(unittest.TestCase):
    def test_frontmatter_moves_fields_outside_the_spec_under_metadata(self):
        text = "---\nname: Poteto Mode\ndescription: >-\n  Folded\n  text.\nicon: crown\ndisable-model-invocation: true\n---\nBody\n"
        out = sync.normalize_frontmatter(text, "poteto-mode")
        self.assertEqual(out, "---\nname: poteto-mode\ndescription: >-\n  Folded\n  text.\nmetadata:\n"
                              '  icon: "crown"\n  disable-model-invocation: "true"\n---\nBody\n')
        self.assertEqual(sync.normalize_frontmatter(out, "poteto-mode"), out)

    def test_frontmatter_keeps_existing_metadata_and_spec_fields(self):
        text = "---\nname: x\ndescription: d\ncompatibility: any\nmetadata:\n  a: \"1\"\nb: two\n---\n"
        self.assertEqual(sync.normalize_frontmatter(text, "x"),
                         '---\nname: x\ndescription: d\ncompatibility: any\nmetadata:\n  a: "1"\n  b: "two"\n---\n')

    def test_subagent_briefs_keep_their_name_and_move_cursor_fields_under_metadata(self):
        text = "---\nname: poteto-agent\ndescription: d\nis_background: true\nmodel: claude-opus-5-5-xhigh-fast\n---\nBody\n"
        out = sync.transform("agents/poteto-agent.md", text.encode(), {}).decode()
        self.assertEqual(out, '---\nname: poteto-agent\ndescription: d\nmetadata:\n  is_background: "true"\n'
                              '  model: "claude-opus-5-5-xhigh-fast"\n---\nBody\n')

    def test_links_follow_the_new_layout_or_go_to_github(self):
        paths = {"pstack/agents/poteto-agent.md": "file", "pstack/docs/guide/01.md": "file", "pstack/docs/guide": "dir",
                 "pstack/skills/beta/SKILL.md": "file", "pstack/skills/alpha/ref.md": "file"}
        text = ("[a](../../agents/poteto-agent.md) [g](../../docs/guide/01.md#top) [d](../../docs/guide/) "
                "[b](../beta/SKILL.md) [r](ref.md) [x](missing.md) [w](https://e.com)")
        self.assertEqual(sync.rewrite_links("alpha/SKILL.md", text, paths),
                         "[a](../agents/poteto-agent.md) "
                         "[g](https://github.com/cursor/plugins/blob/main/pstack/docs/guide/01.md#top) "
                         "[d](https://github.com/cursor/plugins/tree/main/pstack/docs/guide) "
                         "[b](../beta/SKILL.md) [r](ref.md) [x](missing.md) [w](https://e.com)")
        self.assertEqual(sync.rewrite_links("agents/poteto-agent.md", "[m](../skills/beta/SKILL.md)", paths),
                         "[m](../beta/SKILL.md)")

    def test_upstream_terms_are_read_and_pstack_vocabulary_is_skipped(self):
        patterns = [t.pattern for t in sync.compile_terms(GENERATOR)]
        self.assertIn("AskQuestion", patterns)
        self.assertIn('environment: "(cloud|local)"', patterns)
        self.assertNotIn("\\btodo ?list\\b", patterns)

    def test_only_new_marker_lines_count(self):
        terms = sync.compile_terms()
        old = b"Use AskQuestion.\nplain\n"
        self.assertEqual(sync.new_markers("a.md", b"Use AskQuestion.\nUse ~/.cursor/x\n", old, terms), ["Use ~/.cursor/x"])
        self.assertEqual(sync.new_markers("make-bot-ui/SKILL.md", b"Cursor\n", None, terms), [])
        self.assertEqual(sync.new_markers("a.md", b"model claude-opus-5-5 xhigh\n", None, terms), [])
        self.assertEqual(sync.new_markers("a.md", b"model claude-opus-5-5-xhigh-fast\n", None, terms),
                         ["model claude-opus-5-5-xhigh-fast"])


class BuildTests(Fixture):
    def test_bootstrap_writes_transformed_upstream(self):
        alpha = self.read("alpha/SKILL.md")
        self.assertIn('name: alpha\ndescription: The Alpha skill.\nmetadata:\n  disable-model-invocation: "true"', alpha)
        self.assertIn("[agent](../agents/poteto-agent.md)", alpha)
        self.assertIn("https://github.com/cursor/plugins/blob/main/pstack/docs/guide/01.md", alpha)
        self.assertTrue(os.access(self.repo / "skills/pstack/kit/run.sh", os.X_OK))
        self.assertEqual(json.loads(self.read("UPSTREAM.json"))["commit"], self.c1)

    def test_unchanged_upstream_is_a_noop(self):
        report, out = self.build(model=Stub())
        self.assertEqual(report["status"], "noop")
        self.assertFalse((out / "patch.diff").exists())

    def test_update_merges_clean_changes_and_sends_the_rest_to_the_model(self):
        c2 = self.upstream_v2()
        stub = Stub()
        report, out = self.build(model=stub)
        self.assertEqual(report["status"], "ok", report)
        self.assertEqual(sorted(stub.calls), ["skills/pstack/alpha/SKILL.md", "skills/pstack/delta/SKILL.md"])
        alpha = self.read("alpha/SKILL.md")
        self.assertIn("Ask the user first, always.", alpha)
        self.assertIn("Keep this line, now longer.", alpha)
        self.assertNotIn("AskQuestion", alpha)
        self.assertIn("Ask the user here.\n\nA.\n\nB.\n\nC.\n\nEnd line, changed.\n", self.read("epsilon/SKILL.md"))
        self.assertIn("Prefer a multiple-choice question", self.read("delta/SKILL.md"))
        self.assertIn("Beta line two.", self.read("beta/SKILL.md"))
        self.assertTrue((self.repo / "skills/pstack/beta/reference.md").exists())
        self.assertFalse((self.repo / "skills/pstack/beta/ref.md").exists())
        self.assertFalse((self.repo / "skills/pstack/gamma/notes.md").exists())
        self.assertEqual(json.loads(self.read("UPSTREAM.json")), {"repository": "cursor/plugins", "commit": c2, "version": "1.1.0"})
        self.assertIn(f"upstream pstack v1.1.0 at commit {c2[:7]}", self.read("SKILL.md"))
        self.assertIn("pstack](https://x) v1.1.0", (self.repo / "README.md").read_text())
        self.assertTrue((out / "patch.diff").read_bytes())

    def test_a_reply_that_keeps_cursor_text_is_retried_then_left_for_review(self):
        self.upstream_v2()
        bad = "<file>\n" + skill("delta", "Prefer AskQuestion over free text.\n") + "</file>"

        class Stubborn(Stub):
            def __call__(self, messages):
                if "delta/SKILL.md" in re.search(r"<path>(.*)</path>", messages[1]["content"]).group(1):
                    self.calls.append("delta")
                    return bad
                return super().__call__(messages)

        mixed = Stubborn()
        report, _ = self.build(model=mixed)
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(mixed.calls.count("delta"), sync.ATTEMPTS_PER_FILE)
        flagged = {f["path"]: f["review"] for f in report["files"] if f["review"]}
        self.assertEqual(list(flagged), ["delta/SKILL.md"])
        self.assertIn("Cursor-specific", flagged["delta/SKILL.md"])
        self.assertTrue(any("delta/SKILL.md: Cursor-specific line" in p for p in report["problems"]))

    def test_without_a_key_model_work_is_left_for_review(self):
        self.upstream_v2()
        report, _ = self.build(model=None)
        self.assertEqual(report["status"], "needs_review")
        reasons = {f["path"]: f["review"] for f in report["files"] if f["review"]}
        self.assertEqual(sorted(reasons), ["alpha/SKILL.md", "delta/SKILL.md"])
        self.assertIn("conflict markers", " ".join(report["problems"]))

    def test_a_script_change_that_conflicts_is_not_sent_to_the_model(self):
        script = self.repo / "skills/pstack/kit/run.sh"
        script.write_text("#!/bin/sh\necho neutral\n")
        commit(self.repo, "adapt script")
        write(self.up, {"pstack/skills/kit/run.sh": "#!/bin/sh\necho upstream\n"})
        commit(self.up, "v2 script")
        stub = Stub()
        report, _ = self.build(model=stub)
        self.assertEqual(stub.calls, [])
        self.assertEqual(report["status"], "needs_review")
        self.assertIn("not Markdown", {f["path"]: f["review"] for f in report["files"]}["kit/run.sh"])


class PublishTests(Fixture):
    def setUp(self):
        super().setUp()
        self.remote = Path(self.tmp.name) / "remote.git"
        sh(self.tmp.name, "git", "init", "-q", "--bare", "-b", "main", str(self.remote))
        sh(self.repo, "git", "remote", "add", "origin", str(self.remote))
        sh(self.repo, "git", "push", "-q", "origin", "main")
        bin_dir = Path(self.tmp.name) / "bin"
        bin_dir.mkdir()
        self.gh_log = Path(self.tmp.name) / "gh.log"
        fake = bin_dir / "gh"
        fake.write_text(f'#!/bin/sh\necho "$@" >> {self.gh_log}\ncase "$*" in *"pr list"*) echo "[]";; esac\n')
        fake.chmod(0o755)
        self.path = os.environ["PATH"]
        os.environ["PATH"] = f"{bin_dir}{os.pathsep}{self.path}"

    def tearDown(self):
        os.environ["PATH"] = self.path
        super().tearDown()

    def fresh_main(self):
        clone = Path(self.tmp.name) / f"clone{len(list(Path(self.tmp.name).glob('clone*')))}"
        sh(self.tmp.name, "git", "clone", "-q", str(self.remote), str(clone))
        return clone

    def test_a_clean_build_lands_on_main(self):
        self.upstream_v2()
        _, out = self.build(model=Stub())
        sync.publish(self.fresh_main(), out, "ThomsenDrake/agent-skills")
        log = sh(self.remote, "git", "log", "--format=%an %s", "-1", "main")
        self.assertIn("github-actions[bot] chore(pstack): sync agent-neutral pstack v1.1.0", log)
        self.assertIn("pr list", self.gh_log.read_text())
        self.assertNotIn("pr create", self.gh_log.read_text())

    def test_a_build_that_needs_review_opens_a_pull_request(self):
        self.upstream_v2()
        _, out = self.build(model=None)
        main_before = sh(self.remote, "git", "rev-parse", "main")
        sync.publish(self.fresh_main(), out, "ThomsenDrake/agent-skills")
        self.assertEqual(sh(self.remote, "git", "rev-parse", "main"), main_before)
        self.assertTrue(sh(self.remote, "git", "rev-parse", f"refs/heads/{sync.BRANCH}").strip())
        self.assertIn(f"pr create --repo ThomsenDrake/agent-skills --base main --head {sync.BRANCH}", self.gh_log.read_text())

    def test_a_branch_with_human_commits_is_left_alone(self):
        self.upstream_v2()
        _, out = self.build(model=None)
        sync.publish(self.fresh_main(), out, "ThomsenDrake/agent-skills")
        human = self.fresh_main()
        sh(human, "git", "checkout", "-q", sync.BRANCH)
        (human / "fix.txt").write_text("manual fix\n")
        commit(human, "manual fix")
        sh(human, "git", "push", "-q", "origin", sync.BRANCH)
        branch_before = sh(self.remote, "git", "rev-parse", sync.BRANCH)
        sync.publish(self.fresh_main(), out, "ThomsenDrake/agent-skills")
        self.assertEqual(sh(self.remote, "git", "rev-parse", sync.BRANCH), branch_before)


if __name__ == "__main__":
    unittest.main()

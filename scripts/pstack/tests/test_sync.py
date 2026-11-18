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

# Ignore the developer's git config, such as commit signing, and keep test output out of a real job summary.
os.environ.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
for variable in ("GITHUB_STEP_SUMMARY", "GITHUB_OUTPUT", "MISTRAL_API_KEY"):
    os.environ.pop(variable, None)

GENERATOR = textwrap.dedent("""\
    const TERMS = [
      { key: "`AskQuestion`", re: /AskQuestion/ },
      { key: "todolist", re: /\\btodo ?list\\b/i },
      { key: "`environment: \\"cloud\\"`", re: /environment: "(cloud|local)"/ },
      { key: "fresh", re: /FreshCursorThing/ },
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

ALPHA = ("Ask with AskQuestion first{first}.\n\nOne.\n\nTwo.\n\nThree.\n\nKeep this line{keep}.\n\n"
         "See [guide](../../docs/guide/01.md) and [agent](../../agents/poteto-agent.md).\n")
EPSILON = "Use AskQuestion here.\n\nA.\n\nB.\n\nC.\n\nEnd line{end}.\n"
NEUTRAL = {
    "Ask with AskQuestion first, always.": "Ask the user first, always.",
    "Prefer AskQuestion over free text.": "Prefer a multiple-choice question over free text.",
}
CONFLICT = re.compile(r"^<<<<<<< .*?\n.*?^=======\n(.*?)^>>>>>>> .*?\n", re.S | re.M)
REPOSITORY = "ThomsenDrake/agent-skills"


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


def commit(repo, message, name="t"):
    sh(repo, "git", "add", "-A")
    sh(repo, "git", "-c", f"user.name={name}", "-c", "user.email=t@t", "commit", "-q", "-m", message)
    return sh(repo, "git", "rev-parse", "HEAD").strip()


def skill(name, body, extra=""):
    return f"---\nname: {name}\ndescription: The {name} skill.\n{extra}---\n\n# {name}\n\n{body}"


def draft_of(messages):
    return re.search(r"<draft>\n(.*?)</draft>", messages[1]["content"], re.S).group(1)


def path_of(messages):
    return re.search(r"<path>(.*)</path>", messages[1]["content"]).group(1)


class Stub:
    """Stands in for Mistral: takes upstream's side of each conflict and rewrites the known Cursor phrases."""

    def __init__(self):
        self.calls = []

    def answer(self, messages):
        text = CONFLICT.sub(r"\1", draft_of(messages))
        for cursor, neutral in NEUTRAL.items():
            text = text.replace(cursor, neutral)
        return text

    def __call__(self, messages):
        self.calls.append(path_of(messages))
        return f"<file>\n{self.answer(messages)}</file>"


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
            "pstack/agents/poteto-agent.md": "---\nname: poteto-agent\nmodel: claude-opus-5-5-xhigh-fast\n---\nRead [mode](../skills/alpha/SKILL.md).\n",
            "pstack/skills/alpha/SKILL.md": skill("Alpha", ALPHA.format(first="", keep=""), "disable-model-invocation: true\n"),
            "pstack/skills/epsilon/SKILL.md": skill("epsilon", EPSILON.format(end="")),
            "pstack/skills/beta/SKILL.md": skill("beta", "Beta line one.\n"),
            "pstack/skills/beta/ref.md": "Reference text for beta.\nSecond line.\nThird line.\n",
            "pstack/skills/gamma/SKILL.md": skill("gamma", "Gamma.\n"),
            "pstack/skills/gamma/notes.md": "Old notes.\n",
            "pstack/skills/kit/SKILL.md": skill("kit", "Run scripts/run.sh.\n"),
            "pstack/skills/kit/run.sh": "#!/bin/sh\necho hi\n",
            "pstack/skills/kit/tools/a.sh": "echo a\n",
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

    def upstream(self, files, message="next", version=None):
        if version:
            files = {**files, "pstack/plugin.json": f'{{"name": "pstack", "version": "{version}"}}\n'}
        write(self.up, files)
        return commit(self.up, message)

    def upstream_v2(self):
        return self.upstream({
            "pstack/skills/alpha/SKILL.md": skill("Alpha", ALPHA.format(first=", always", keep=", now longer"),
                                                  "disable-model-invocation: true\n"),
            "pstack/skills/epsilon/SKILL.md": skill("epsilon", EPSILON.format(end=", changed")),
            "pstack/skills/beta/SKILL.md": skill("beta", "Beta line one.\nBeta line two.\n"),
            "pstack/skills/beta/ref.md": None,
            "pstack/skills/beta/reference.md": "Reference text for beta.\nSecond line.\nThird line.\n",
            "pstack/skills/gamma/notes.md": None,
            "pstack/skills/delta/SKILL.md": skill("delta", "Prefer AskQuestion over free text.\n"),
        }, "v2", version="1.1.0")

    def build(self, model=None):
        out = Path(self.tmp.name) / f"out{len(list(Path(self.tmp.name).glob('out*')))}"
        return sync.build(self.repo, out, self.up, model=model), out

    def reset(self):
        sh(self.repo, "git", "reset", "-q", "--hard", self.base)
        sh(self.repo, "git", "clean", "-qfd")

    def read(self, path):
        return (self.repo / "skills/pstack" / path).read_text()

    def reviews(self, report):
        return {f["path"]: f["review"] for f in report["files"] if f["review"]}


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

    def test_block_and_list_values_become_strings_under_metadata(self):
        text = "---\nname: x\ndescription: d\nnotes: |\n  one\n  two\ntags:\n  - a\n  - b\n---\n"
        self.assertEqual(sync.normalize_frontmatter(text, "x"),
                         '---\nname: x\ndescription: d\nmetadata:\n  notes: "one\\ntwo"\n  tags: "[\\"a\\", \\"b\\"]"\n---\n')

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
        parsed = sync.parse_upstream_terms(GENERATOR)
        self.assertEqual([t.pattern for t in parsed], ["AskQuestion", 'environment: "(cloud|local)"', "FreshCursorThing"])
        patterns = [t.pattern for t in sync.compile_terms(parsed)]
        self.assertIn("FreshCursorThing", patterns)
        self.assertIn("pstack-models\\.mdc", patterns)
        self.assertIsNone(sync.parse_upstream_terms("const OTHER = [];"))

    def test_only_new_marker_lines_count(self):
        terms = sync.compile_terms()
        old = b"Use AskQuestion.\nplain\n"
        self.assertEqual(sync.new_markers("a.md", b"Use AskQuestion.\nUse ~/.cursor/x\n", old, terms), ["Use ~/.cursor/x"])
        self.assertEqual(sync.new_markers("make-bot-ui/SKILL.md", b"Cursor\n", None, terms), [])
        self.assertEqual(sync.new_markers("a.md", b"model claude-opus-5-5 xhigh\n", None, terms), [])
        self.assertEqual(sync.new_markers("a.md", b"model claude-opus-5-5-xhigh-fast\n", None, terms),
                         ["model claude-opus-5-5-xhigh-fast"])
        self.assertEqual(sync.new_markers("a/run.sh", b'cat "$HOME/.cursor/rules/x"\n', None, terms),
                         ['cat "$HOME/.cursor/rules/x"'])
        self.assertEqual(sync.new_markers("a.md", b"Cursor users can also install upstream's native plugin.\n", None, terms), [])

    def test_only_a_line_anchored_file_block_is_taken(self):
        reply = "I will return it between <file> and </file> lines.\n<file>\nfirst\n</file>\n<file>\nsecond\n</file>\n"
        self.assertEqual(sync.extract_file(reply), "second\n")
        self.assertIsNone(sync.extract_file("Here it is: <file>text</file>"))


class OutputTests(unittest.TestCase):
    DRAFT = "---\nname: x\ndescription: Use AskQuestion.\nmetadata:\n  a: \"1\"\n---\n\n# x\n\n" + "\n".join(
        f"Line {i}." for i in range(1, 80)) + "\nPrefer AskQuestion over free text.\n"

    def job(self):
        flagged = ["description: Use AskQuestion.", "Prefer AskQuestion over free text."]
        return {"path": "x/SKILL.md", "draft": self.DRAFT.encode(), "new": self.DRAFT.encode(), "accepted": None,
                "flagged": flagged, "current": None}

    def good(self):
        return self.DRAFT.replace("Use AskQuestion.", "Ask the user.").replace(
            "Prefer AskQuestion over free text.", "Prefer a multiple-choice question over free text.")

    def problems(self, text):
        return " ".join(sync.output_problems(self.job(), text, sync.compile_terms()))

    def test_a_faithful_reply_passes(self):
        self.assertEqual(self.problems(self.good()), "")

    def test_a_reply_that_changes_an_unflagged_line_fails(self):
        self.assertIn("neither flagged nor in a conflict", self.problems(self.good().replace("Line 7.", "Line seven.")))

    def test_a_reply_wrapped_in_a_code_fence_fails(self):
        self.assertIn("code fence", self.problems("```markdown\n" + self.good() + "```\n"))

    def test_a_reply_without_frontmatter_fails(self):
        self.assertIn("must start with the draft's frontmatter", self.problems(self.good().split("---\n", 2)[2]))

    def test_a_reply_that_changes_a_frontmatter_field_fails(self):
        self.assertIn("`metadata` changed", self.problems(self.good().replace('a: "1"', 'a: "2"')))

    def test_a_truncated_reply_fails(self):
        self.assertIn("times the new upstream length", self.problems(self.good()[:300]))


class BuildTests(Fixture):
    def test_bootstrap_writes_transformed_upstream(self):
        alpha = self.read("alpha/SKILL.md")
        self.assertIn('name: alpha\ndescription: The Alpha skill.\nmetadata:\n  disable-model-invocation: "true"', alpha)
        self.assertIn("[agent](../agents/poteto-agent.md)", alpha)
        self.assertIn("https://github.com/cursor/plugins/blob/main/pstack/docs/guide/01.md", alpha)
        self.assertIn('metadata:\n  model: "claude-opus-5-5-xhigh-fast"', self.read("agents/poteto-agent.md"))
        self.assertTrue(os.access(self.repo / "skills/pstack/kit/run.sh", os.X_OK))
        self.assertEqual(json.loads(self.read("UPSTREAM.json"))["commit"], self.c1)

    def test_unchanged_upstream_is_a_noop(self):
        report, out = self.build(model=Stub())
        self.assertEqual(report["status"], "noop")
        self.assertFalse((out / "patch.diff").exists())

    def test_an_upstream_change_outside_pstack_is_a_noop(self):
        self.upstream({"README.md": "other plugin\n"})
        report, _ = self.build(model=Stub())
        self.assertEqual(report["status"], "noop")

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

        class Stubborn(Stub):
            def __call__(self, messages):
                if path_of(messages).endswith("delta/SKILL.md"):
                    self.calls.append("delta")
                    return f"<file>\n{draft_of(messages)}</file>"
                return super().__call__(messages)

        stub = Stubborn()
        report, _ = self.build(model=stub)
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(stub.calls.count("delta"), sync.ATTEMPTS_PER_FILE)
        self.assertEqual(list(self.reviews(report)), ["delta/SKILL.md"])
        self.assertIn("Cursor-specific", self.reviews(report)["delta/SKILL.md"])

    def test_a_truncated_reply_is_left_for_review(self):
        self.upstream({"pstack/skills/delta/SKILL.md": skill("delta", "Prefer AskQuestion over free text.\n" + "Detail.\n" * 80)})

        class Truncating(Stub):
            def __call__(self, messages):
                self.calls.append(path_of(messages))
                return f"<file>\n{self.answer(messages)[:250]}\n</file>"

        report, _ = self.build(model=Truncating())
        self.assertEqual(report["status"], "needs_review")
        self.assertIn("times the new upstream length", self.reviews(report)["delta/SKILL.md"])

    def test_a_reply_without_a_file_block_is_asked_again(self):
        self.upstream_v2()

        class Chatty(Stub):
            def __call__(self, messages):
                if len(messages) == 2:
                    self.calls.append(path_of(messages))
                    return "Sure, here is the file you asked for."
                return super().__call__(messages)

        stub = Chatty()
        report, _ = self.build(model=stub)
        self.assertEqual(report["status"], "ok", report)
        self.assertEqual(len(stub.calls), 4)

    def test_model_failures_leave_files_for_review_and_still_write_the_report(self):
        self.upstream_v2()
        for failure in (sync.SyncError("model request failed: HTTP 503"), ConnectionResetError("reset by peer")):
            with self.subTest(failure=type(failure).__name__):
                self.reset()

                def broken(messages, failure=failure):
                    raise failure

                report, out = self.build(model=broken)
                self.assertEqual(report["status"], "needs_review")
                self.assertTrue((out / "report.json").exists())
                self.assertEqual(sorted(self.reviews(report)), ["alpha/SKILL.md", "delta/SKILL.md"])

    def test_without_a_key_model_work_is_left_for_review(self):
        self.upstream_v2()
        report, _ = self.build(model=None)
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(sorted(self.reviews(report)), ["alpha/SKILL.md", "delta/SKILL.md"])
        self.assertIn("conflict markers", " ".join(report["problems"]))

    def test_a_script_change_that_conflicts_is_not_sent_to_the_model(self):
        script = self.repo / "skills/pstack/kit/run.sh"
        script.write_text("#!/bin/sh\necho neutral\n")
        commit(self.repo, "adapt script")
        self.upstream({"pstack/skills/kit/run.sh": "#!/bin/sh\necho upstream\n"})
        stub = Stub()
        report, _ = self.build(model=stub)
        self.assertEqual(stub.calls, [])
        self.assertEqual(report["status"], "needs_review")
        self.assertIn("not Markdown", self.reviews(report)["kit/run.sh"])

    def test_a_script_that_gains_cursor_text_is_left_for_review(self):
        self.upstream({"pstack/skills/kit/run.sh": '#!/bin/sh\necho hi\ncat "$HOME/.cursor/rules/x.mdc"\n'})
        report, _ = self.build(model=Stub())
        self.assertEqual(report["status"], "needs_review")
        self.assertIn("adds Cursor-specific text", self.reviews(report)["kit/run.sh"])

    def test_an_unadapted_script_keeps_its_mode_and_mode_changes_apply(self):
        self.upstream({"pstack/skills/kit/run.sh": "#!/bin/sh\necho changed\n"})
        os.chmod(self.up / "pstack/skills/kit/tools/a.sh", 0o755)
        commit(self.up, "mode")
        report, _ = self.build(model=Stub())
        self.assertEqual(report["status"], "ok", report)
        self.assertTrue(os.access(self.repo / "skills/pstack/kit/run.sh", os.X_OK))
        self.assertTrue(os.access(self.repo / "skills/pstack/kit/tools/a.sh", os.X_OK))
        self.assertIn("mode changed upstream", {f["path"]: f["action"] for f in report["files"]}["kit/tools/a.sh"])

    def test_an_adapted_file_keeps_its_wording_when_upstream_renames_it(self):
        sh(self.up, "git", "mv", "pstack/skills/epsilon", "pstack/skills/zeta")
        write(self.up, {"pstack/skills/zeta/SKILL.md": skill("epsilon", EPSILON.format(end=", changed"))})
        commit(self.up, "rename")
        report, _ = self.build(model=None)
        self.assertEqual(report["renames"], {"zeta/SKILL.md": "epsilon/SKILL.md"})
        zeta = self.read("zeta/SKILL.md")
        self.assertIn("name: zeta", zeta)
        self.assertIn("Ask the user here.", zeta)
        self.assertIn("End line, changed.", zeta)
        self.assertFalse((self.repo / "skills/pstack/epsilon").exists())
        self.assertIn("including the skill(s) epsilon", " ".join(report["problems"]))

    def test_upstream_moving_pstack_stops_the_sync_instead_of_deleting_the_adaptation(self):
        sh(self.up, "git", "mv", "pstack", "plugins")
        commit(self.up, "move")
        with self.assertRaisesRegex(sync.SyncError, "no longer has pstack/skills"):
            self.build(model=Stub())
        self.assertTrue((self.repo / "skills/pstack/alpha/SKILL.md").exists())

    def test_a_folder_that_becomes_a_file_does_not_crash_the_build(self):
        sh(self.up, "git", "rm", "-q", "-r", "pstack/skills/kit/tools")
        self.upstream({"pstack/skills/kit/tools": "now a file\n"})
        report, _ = self.build(model=Stub())
        self.assertEqual(report["status"], "ok", report)
        self.assertEqual(self.read("kit/tools"), "now a file\n")

    def test_a_deleted_skill_waits_for_review(self):
        sh(self.up, "git", "rm", "-q", "-r", "pstack/skills/gamma")
        commit(self.up, "drop gamma")
        report, _ = self.build(model=Stub())
        self.assertEqual(report["status"], "needs_review")
        self.assertIn("including the skill(s) gamma", " ".join(report["problems"]))

    def test_a_missing_term_list_or_version_is_reported(self):
        sh(self.up, "git", "rm", "-q", "scripts/generate-pstack-harness-trees.mjs", "pstack/plugin.json")
        self.upstream({"pstack/skills/beta/SKILL.md": skill("beta", "Beta line one.\nMore.\n")})
        report, _ = self.build(model=Stub())
        self.assertEqual(report["status"], "needs_review")
        problems = " ".join(report["problems"])
        self.assertIn("term list", problems)
        self.assertIn("has no version", problems)


class PublishTests(Fixture):
    def setUp(self):
        super().setUp()
        self.remote = Path(self.tmp.name) / "remote.git"
        sh(self.tmp.name, "git", "init", "-q", "--bare", "-b", "main", str(self.remote))
        sh(self.repo, "git", "remote", "add", "origin", str(self.remote))
        sh(self.repo, "git", "push", "-q", "origin", "main")
        self.state = Path(self.tmp.name) / "gh"
        self.state.mkdir()
        bin_dir = Path(self.tmp.name) / "bin"
        bin_dir.mkdir()
        self.log = self.state / "log"
        fake = bin_dir / "gh"
        fake.write_text(textwrap.dedent(f"""\
            #!/bin/sh
            echo "$@" >> {self.log}
            case "$*" in
              *"pr list"*"--state open"*) cat {self.state}/open.json 2>/dev/null || echo "[]";;
              *"pr list"*"--state closed"*) cat {self.state}/closed.json 2>/dev/null || echo "[]";;
              *"pr view"*) cat {self.state}/comments.txt 2>/dev/null || true;;
              *"pr create"*) echo https://github.com/x/y/pull/9;;
            esac
            """))
        fake.chmod(0o755)
        self.path = os.environ["PATH"]
        os.environ["PATH"] = f"{bin_dir}{os.pathsep}{self.path}"

    def tearDown(self):
        os.environ["PATH"] = self.path
        super().tearDown()

    def prs(self, state, prs):
        (self.state / f"{state}.json").write_text(json.dumps(prs))

    def calls(self):
        return self.log.read_text() if self.log.exists() else ""

    def clone(self):
        clone = Path(self.tmp.name) / f"clone{len(list(Path(self.tmp.name).glob('clone*')))}"
        sh(self.tmp.name, "git", "clone", "-q", str(self.remote), str(clone))
        return clone

    def rev(self, ref):
        return sh(self.remote, "git", "rev-parse", ref).strip()

    def publish(self, out):
        sync.publish(self.clone(), out, REPOSITORY)

    def needs_review_artifact(self):
        self.upstream_v2()
        return self.build(model=None)[1]

    def push_human_commit(self):
        human = self.clone()
        sh(human, "git", "checkout", "-q", sync.BRANCH)
        (human / "fix.txt").write_text("manual fix\n")
        commit(human, "manual fix", name="Drake")
        sh(human, "git", "push", "-q", "origin", sync.BRANCH)
        return self.rev(sync.BRANCH)

    def test_a_clean_build_lands_on_main(self):
        self.upstream_v2()
        _, out = self.build(model=Stub())
        self.publish(out)
        self.assertIn("github-actions[bot] chore(pstack): sync agent-neutral pstack v1.1.0",
                      sh(self.remote, "git", "log", "--format=%an %s", "-1", "main"))
        self.assertNotIn("pr create", self.calls())

    def test_a_clean_build_closes_a_bot_only_review_pr(self):
        self.publish(self.needs_review_artifact())
        self.reset()
        _, ok = self.build(model=Stub())
        self.prs("open", [{"number": 7, "title": "t", "isCrossRepository": False}])
        self.publish(ok)
        self.assertIn(f"pr close 7 --repo {REPOSITORY} --delete-branch", self.calls())

    def test_a_clean_build_leaves_a_review_pr_with_human_commits_open(self):
        self.publish(self.needs_review_artifact())
        self.push_human_commit()
        self.reset()
        _, ok = self.build(model=Stub())
        self.prs("open", [{"number": 7, "title": "t", "isCrossRepository": False}])
        self.publish(ok)
        self.assertNotIn("pr close", self.calls())
        self.assertIn("pr comment 7", self.calls())

    def test_a_build_that_needs_review_opens_a_pull_request(self):
        main_before = self.rev("main")
        self.publish(self.needs_review_artifact())
        self.assertEqual(self.rev("main"), main_before)
        self.assertTrue(self.rev(f"refs/heads/{sync.BRANCH}"))
        self.assertIn(f"pr create --repo {REPOSITORY} --base main --head {sync.BRANCH}", self.calls())

    def test_a_bot_only_branch_is_rebuilt_and_its_pr_updated(self):
        self.publish(self.needs_review_artifact())
        first = self.rev(sync.BRANCH)
        self.upstream({"pstack/skills/beta/SKILL.md": skill("beta", "Beta line one.\nBeta line three.\n")}, "v3")
        self.reset()
        _, out = self.build(model=None)
        self.prs("open", [{"number": 7, "title": "t", "isCrossRepository": False}])
        self.publish(out)
        self.assertNotEqual(self.rev(sync.BRANCH), first)
        self.assertIn("pr edit 7", self.calls())

    def test_an_open_pr_with_human_commits_is_left_alone(self):
        out = self.needs_review_artifact()
        self.publish(out)
        human = self.push_human_commit()
        self.prs("open", [{"number": 7, "title": "t", "isCrossRepository": False}])
        self.publish(out)
        self.assertEqual(self.rev(sync.BRANCH), human)
        self.assertIn("pr comment 7", self.calls())
        marker = json.loads((out / "report.json").read_text())["upstream"]["new"][:7]
        (self.state / "comments.txt").write_text(f"Upstream is now at `{marker}`")
        self.publish(out)
        self.assertEqual(self.calls().count("pr comment 7"), 1)

    def test_human_commits_on_a_branch_whose_pr_is_gone_do_not_block_the_next_update(self):
        out = self.needs_review_artifact()
        self.publish(out)
        human = self.push_human_commit()
        self.publish(out)
        self.assertNotEqual(self.rev(sync.BRANCH), human)
        self.assertEqual(self.calls().count("pr create"), 2)

    def test_a_pr_closed_without_merging_is_not_reopened_for_the_same_upstream_commit(self):
        out = self.needs_review_artifact()
        report = json.loads((out / "report.json").read_text())
        title = f"pstack: sync v1.1.0 from cursor/plugins@{report['upstream']['new'][:7]} (needs review)"
        self.prs("closed", [{"number": 5, "title": title, "mergedAt": None, "isCrossRepository": False}])
        self.publish(out)
        self.assertNotIn("pr create", self.calls())
        self.assertFalse(sh(self.remote, "git", "branch", "--list", sync.BRANCH).strip())

    def test_prs_from_forks_are_ignored(self):
        self.prs("open", [{"number": 3, "title": "t", "isCrossRepository": True}])
        self.publish(self.needs_review_artifact())
        self.assertIn("pr create", self.calls())
        self.assertNotIn("pr edit 3", self.calls())

    def test_publish_rechecks_the_patch_against_current_main(self):
        self.upstream_v2()
        report, out = self.build(model=Stub())
        self.assertEqual(report["status"], "ok")
        moved = self.clone()
        sh(moved, "git", "rm", "-q", "skills/pstack/agents/poteto-agent.md")
        commit(moved, "drop the brief alpha links to", name="Drake")
        sh(moved, "git", "push", "-q", "origin", "main")
        main_before = self.rev("main")
        self.publish(out)
        self.assertEqual(self.rev("main"), main_before)
        self.assertIn("pr create", self.calls())

    def test_a_patch_outside_the_adaptation_is_refused(self):
        self.upstream_v2()
        _, out = self.build(model=Stub())
        patch = (out / "patch.diff").read_text()
        (out / "patch.diff").write_text(patch.replace("a/README.md", "a/.github/x.yml").replace("b/README.md", "b/.github/x.yml"))
        with self.assertRaisesRegex(sync.SyncError, "outside skills/pstack"):
            self.publish(out)


if __name__ == "__main__":
    unittest.main()

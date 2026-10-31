"""Offline publisher tests: real Git repositories; fake only the GitHub API."""
from collections.abc import Callable
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, unquote, urlsplit


AUTOMATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AUTOMATION))
import protocol

SPEC = importlib.util.spec_from_file_location("pstack_publisher", AUTOMATION / "publish.py")
assert SPEC is not None and SPEC.loader is not None
publisher = importlib.util.module_from_spec(SPEC)
if (AUTOMATION / "publish.py").exists():
    SPEC.loader.exec_module(publisher)

REPOSITORY = "ThomsenDrake/agent-skills"
BRANCH = "automation/pstack-hermes-update"
BOT = "github-actions[bot]"
EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
SOURCE = "skills/pstack"
ADAPTED = "skills/pstack-hermes"


class FakeGitHub:
    """A GitHub wire-boundary double backed by the real bare origin."""
    def __init__(self, origin):
        self.origin = origin
        self.calls = []
        self.prs = []
        self.before_request: Callable | None = None

    def git(self, *args):
        return subprocess.run(["git", "--git-dir", str(self.origin), *args],
                              check=True, capture_output=True).stdout.decode().strip()

    def head(self, branch=BRANCH):
        result = subprocess.run(["git", "--git-dir", str(self.origin),
                                 "rev-parse", "--verify", "refs/heads/" + branch],
                                capture_output=True)
        return result.stdout.decode().strip() if result.returncode == 0 else None

    def commit_json(self, sha):
        values = self.git("show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce%x00%T%x00%P%x00%B", sha).split("\0", 6)
        an, ae, cn, ce, tree, parents, message = values
        return {"sha": sha, "author": {"login": BOT if ae == EMAIL else "human"},
                "committer": {"login": BOT if ce == EMAIL else "human"},
                "commit": {"author": {"name": an, "email": ae},
                           "committer": {"name": cn, "email": ce},
                           "tree": {"sha": tree}, "message": message},
                "parents": [{"sha": parent} for parent in parents.split()]}

    def add_pr(self, *, state="open", merged=False, author=BOT, body=""):
        number = len(self.prs) + 1
        pr = {"number": number, "state": state, "merged_at": "2026-01-01T00:00:00Z" if merged else None,
              "user": {"login": author}, "base": {"ref": "main", "repo": {"full_name": REPOSITORY}},
              "head": {"ref": BRANCH, "sha": self.head(), "repo": {"full_name": REPOSITORY}},
              "body": body, "html_url": f"https://github.com/{REPOSITORY}/pull/{number}"}
        self.prs.append(pr)
        return pr

    def __call__(self, args, *, input=None):
        method = args[args.index("--method") + 1]
        endpoint = next(arg for arg in args if arg.startswith("repos/"))
        self.calls.append((method, endpoint, input))
        if self.before_request:
            self.before_request(method, endpoint)
        url = urlsplit(endpoint)
        suffix = unquote(url.path.removeprefix("repos/" + REPOSITORY))
        query = parse_qs(url.query)
        if method == "GET" and suffix == "":
            return {"default_branch": "main", "full_name": REPOSITORY}
        if method == "GET" and suffix.startswith("/git/ref/heads/"):
            branch = suffix.removeprefix("/git/ref/heads/")
            sha = self.head(branch)
            if sha is None:
                raise publisher.GitHubNotFound("branch not found")
            return {"ref": "refs/heads/" + branch, "object": {"type": "commit", "sha": sha}}
        if method == "GET" and suffix.startswith("/git/trees/"):
            sha = suffix.removeprefix("/git/trees/")
            entries = []
            for record in self.git("ls-tree", "-z", sha).split("\0"):
                if record:
                    info, path = record.split("\t", 1)
                    mode, kind, oid = info.split()
                    entries.append({"mode": mode, "type": kind, "sha": oid, "path": path})
            return {"sha": sha, "tree": entries, "truncated": False}
        if method == "GET" and suffix.startswith("/commits/"):
            return self.commit_json(suffix.removeprefix("/commits/"))
        if method == "GET" and suffix == "/pulls":
            matching = [pr for pr in self.prs if pr["head"]["ref"] == BRANCH and pr["base"]["ref"] == "main"]
            page = int(query.get("page", ["1"])[0])
            return json.loads(json.dumps(matching[(page - 1) * 100:page * 100]))
        if method == "GET" and suffix.startswith("/pulls/"):
            pr = self.prs[int(suffix.rsplit("/", 1)[1]) - 1]
            result = json.loads(json.dumps(pr))
            if pr["state"] == "open":
                result["head"]["sha"] = self.head()
            return result
        if method == "POST" and suffix == "/pulls":
            assert input is not None
            data = json.loads(input)
            assert data["head"] == BRANCH and data["base"] == "main"
            assert data["draft"] is False and data["maintainer_can_modify"] is False
            return json.loads(json.dumps(self.add_pr(body=data["body"])))
        if method == "PATCH" and suffix.startswith("/pulls/"):
            pr = self.prs[int(suffix.rsplit("/", 1)[1]) - 1]
            assert input is not None
            data = json.loads(input)
            assert set(data) == {"title", "body"}
            pr.update(data)
            return json.loads(json.dumps(pr))
        raise AssertionError(f"unexpected GitHub operation: {method} {endpoint}")


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ["TMPDIR"])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.origin = self.root / "origin.git"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Fixture Human")
        self.git("config", "user.email", "human@example.invalid")
        self.put(f"{SOURCE}/SKILL.md", "# Upstream\n")
        self.put(f"{SOURCE}/alpha/SKILL.md", "# Upstream alpha\n")
        self.put(f"{SOURCE}/alpha/guide.md", "# Upstream guide\n")
        self.put(f"{ADAPTED}/SKILL.md", "# Hermes\n")
        self.put(f"{ADAPTED}/alpha/SKILL.md", "# Hermes alpha\n")
        self.put(f"{ADAPTED}/alpha/guide.md", "# Hermes guide\n")
        self.put(f"{ADAPTED}/automation/controller.py", "# protected\n")
        self.put("README.md", "# Outside\n")
        upstream = self.commit("initial source")
        self.put(f"{ADAPTED}/UPSTREAM.json", json.dumps({
            "schema": 1, "source_commit": upstream,
            "source_tree": self.git("rev-parse", f"{upstream}:{SOURCE}"),
        }) + "\n")
        self.commit("checkpoint")
        self.put(f"{SOURCE}/alpha/SKILL.md", "# Changed upstream alpha\n")
        self.base = self.commit("new upstream Markdown")
        subprocess.run(["git", "init", "--bare", "-q", str(self.origin)], check=True)
        self.git("remote", "add", "origin", f"https://github.com/{REPOSITORY}.git")
        self.git("push", str(self.origin), "HEAD:refs/heads/main")
        self.api = FakeGitHub(self.origin)
        self.plan = protocol.plan(self.repo)

    def git(self, *args, input=None, env=None):
        return subprocess.run(["git", "-C", str(self.repo), *args], input=input,
                              env=env, check=True, capture_output=True).stdout.decode().strip()

    def put(self, relative, text):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD")

    def test_empty_probe_records_exact_branch_expectation_read_only(self):
        result = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        self.assertEqual(result, {
            "schema": 1, "repository": REPOSITORY, "default_branch": "main",
            "base_commit": self.plan["base_commit"],
            "source_tree": self.plan["source_tree"], "adaptation_tree": self.plan["adaptation_tree"],
            "expected_bot_branch_head": None, "pr_number": None,
            "skip": False, "blocked_reasons": [],
        })
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
        self.assertEqual(self.git("status", "--porcelain"), "")

    def seed_bot(self, *, plan=None, updates=None):
        plan = plan or self.plan
        env = {**os.environ, "GIT_AUTHOR_NAME": BOT, "GIT_AUTHOR_EMAIL": EMAIL,
               "GIT_COMMITTER_NAME": BOT, "GIT_COMMITTER_EMAIL": EMAIL,
               "GIT_INDEX_FILE": str(self.root / "seed-index")}
        self.git("read-tree", plan["base_commit"], env=env)
        contents = {f"{ADAPTED}/UPSTREAM.json": json.dumps({
            "schema": 1, "source_commit": plan["source_commit"], "source_tree": plan["source_tree"],
        }, indent=2) + "\n"}
        contents.update({f"{ADAPTED}/{path}": text for path, text in (updates or {}).items()})
        for path, text in contents.items():
            oid = self.git("hash-object", "-w", "--stdin", input=text.encode())
            self.git("update-index", "--add", "--cacheinfo", "100644," + oid + "," + path, env=env)
        tree = self.git("write-tree", env=env)
        self.metadata = {"schema": 1, "repository": REPOSITORY, "base_commit": plan["base_commit"],
                         "source_commit": plan["source_commit"], "source_tree": plan["source_tree"],
                         "adaptation_tree": plan["adaptation_tree"], "result_tree": tree}
        message = "chore(pstack-hermes): adapt upstream Markdown\n\nPstack-Hermes-Publication: " + json.dumps(self.metadata, sort_keys=True, separators=(",", ":")) + "\n"
        sha = self.git("commit-tree", tree, "-p", plan["base_commit"], input=message.encode(), env=env)
        self.git("push", str(self.origin), sha + ":refs/heads/" + BRANCH)
        return sha

    def metadata_body(self):
        return "<!-- pstack-hermes-publication:" + json.dumps(self.metadata, sort_keys=True, separators=(",", ":")) + " -->"

    def test_probe_deduplicates_both_source_and_adaptation_trees_not_main_commit(self):
        head = self.seed_bot()
        self.api.add_pr(body=self.metadata_body())
        result = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        self.assertTrue(result["skip"], "identical source and adaptation basis must skip before model spending")
        self.assertEqual(result["pr_number"], 1)
        self.assertEqual(result["expected_bot_branch_head"], head)
        self.put("README.md", "Unrelated accepted main change\n")
        self.commit("unrelated main advance")
        self.git("push", str(self.origin), "HEAD:refs/heads/main")
        same_trees = protocol.plan(self.repo)
        self.assertNotEqual(same_trees["base_commit"], self.plan["base_commit"])
        self.assertTrue(publisher.probe(REPOSITORY, same_trees, gh_runner=self.api)["skip"])
        self.put(f"{ADAPTED}/automation/controller.py", "# changed trusted policy\n")
        self.commit("Hermes adaptation basis changes")
        self.git("push", str(self.origin), "HEAD:refs/heads/main")
        new_basis = protocol.plan(self.repo)
        self.assertEqual(new_basis["source_tree"], same_trees["source_tree"])
        result = publisher.probe(REPOSITORY, new_basis, gh_runner=self.api)
        self.assertFalse(result["skip"], "source-only dedup silently ignores Hermes policy changes")
        self.assertEqual(result["blocked_reasons"], [])
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))

    def test_human_closed_unmerged_request_blocks_new_publication(self):
        self.seed_bot()
        self.api.add_pr(state="closed", body=self.metadata_body())
        result = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        self.assertTrue(result["blocked_reasons"], "a human close is not permission to reopen")
        self.assertFalse(result["skip"])
        self.assertIn("closed", " ".join(result["blocked_reasons"]))
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))

    def test_probe_rejects_nonbot_forked_ambiguous_or_mismatched_open_request(self):
        head = self.seed_bot()
        original = self.api.add_pr(body=self.metadata_body())
        for case in ("human", "fork", "multiple", "head-sha", "body-binding"):
            with self.subTest(case=case):
                self.api.prs = [json.loads(json.dumps(original))]
                pr = self.api.prs[0]
                if case == "human":
                    pr["user"]["login"] = "maintainer"
                elif case == "fork":
                    pr["head"]["repo"]["full_name"] = "stranger/agent-skills"
                elif case == "multiple":
                    self.api.add_pr(body=self.metadata_body())
                elif case == "head-sha":
                    pr["head"]["sha"] = "0" * 40
                else:
                    pr["body"] = self.metadata_body().replace(self.metadata["source_tree"], "0" * 40)
                with self.assertRaises(ValueError):
                    publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
                self.assertEqual(self.api.head(), head)
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))

    def envelope(self, updates=None):
        dest = self.root / ("snapshot-" + str(len(list(self.root.glob("snapshot-*")))))
        protocol.materialize(self.repo, protocol.plan(self.repo), dest)
        for relative, text in (updates or {"alpha/SKILL.md": "# Reviewed Hermes alpha\n"}).items():
            (dest / "candidate" / relative).write_text(text, encoding="utf-8")
        return protocol.collect(self.repo, protocol.plan(self.repo), dest / "candidate")

    def git_transport(self, repo, *args, input=None, env=None):
        # Only the transport is redirected; Git still builds/fetches/pushes real objects.
        self.git_calls.append(tuple(args))
        if self.before_git:
            self.before_git(args)
        if "push" in args or "fetch" in args:
            args = [str(self.origin) if arg == "origin" else arg for arg in args]
        result = publisher.git(repo, *args, input=input, env=env)
        if "push" in args:
            for pr in self.api.prs:
                if pr["state"] == "open":
                    pr["head"]["sha"] = self.api.head()
        return result

    def do_publish(self, envelope, expected, *, before_git=None):
        self.git_calls = []
        self.before_git = before_git
        return publisher.publish(self.repo, envelope, REPOSITORY, expected_probe=expected,
                                 gh_runner=self.api, git_runner=self.git_transport)

    def test_initial_publication_normal_pushes_reviewed_tree_and_verifies_exact_pr(self):
        self.assertTrue(callable(getattr(publisher, "publish", None)), "publish() is missing")
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        result = self.do_publish(envelope, expected)
        head = self.api.head()
        assert head is not None
        self.assertEqual(result, {"status": "published", "pr_number": 1,
                                  "url": f"https://github.com/{REPOSITORY}/pull/1",
                                  "head_sha": head, "branch": BRANCH})
        self.assertEqual(self.api.git("show", head + ":" + ADAPTED + "/alpha/SKILL.md"), "# Reviewed Hermes alpha")
        self.assertEqual(self.api.git("show", head + ":README.md"), "# Outside")
        self.assertEqual(self.api.git("show", "-s", "--format=%P", head), self.base)
        self.assertEqual(self.api.git("show", "-s", "--format=%an <%ae>|%cn <%ce>", head),
                         f"{BOT} <{EMAIL}>|{BOT} <{EMAIL}>")
        self.assertEqual(json.loads(self.api.git("show", head + ":" + ADAPTED + "/UPSTREAM.json")),
                         {"schema": 1, "source_commit": self.base, "source_tree": self.plan["source_tree"]})
        self.assertEqual(self.git("rev-parse", "HEAD"), self.base)
        self.assertEqual(self.git("diff", "--cached"), "")
        self.assertEqual(len(self.api.prs), 1)
        body = self.api.prs[0]["body"]
        self.assertIn(self.base, body)
        self.assertNotIn("Reviewed Hermes alpha", body)
        self.assertNotIn("tests passed", body.lower())
        pushes = [args for args in self.git_calls if "push" in args]
        self.assertEqual(len(pushes), 1)
        self.assertIn("credential.helper=", pushes[0])
        self.assertIn("credential.helper=!gh auth git-credential", pushes[0])
        self.assertEqual(pushes[0][-2:], ("origin", head + ":refs/heads/" + BRANCH))
        self.assertFalse(any("force" in arg or arg.startswith("+") for arg in pushes[0]))
        self.assertEqual(self.api.calls[-1][:2], ("GET", f"repos/{REPOSITORY}/pulls/1"))

    def test_actions_checkout_origin_without_git_suffix_publishes_reviewed_tree(self):
        origin = f"https://github.com/{REPOSITORY}"
        self.git("remote", "set-url", "origin", origin)
        self.assertEqual(self.git("remote", "get-url", "--all", "origin"), origin)
        self.assertEqual(self.git("remote", "get-url", "--push", "--all", "origin"), origin)
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        result = self.do_publish(envelope, expected)
        head = self.api.head()
        assert head is not None
        self.assertEqual(result, {"status": "published", "pr_number": 1,
                                  "url": f"https://github.com/{REPOSITORY}/pull/1",
                                  "head_sha": head, "branch": BRANCH})
        self.assertEqual(self.api.git("show", head + ":" + ADAPTED + "/alpha/SKILL.md"),
                         "# Reviewed Hermes alpha")
        self.assertEqual(len(self.api.prs), 1)
        pushes = [args for args in self.git_calls if "push" in args]
        self.assertEqual(len(pushes), 1)
        self.assertEqual(pushes[0][-2:], ("origin", head + ":refs/heads/" + BRANCH))
        self.assertEqual(self.api.calls[-1][:2], ("GET", f"repos/{REPOSITORY}/pulls/1"))

    def test_second_publication_appends_fast_forward_but_rebuilds_tree_from_main(self):
        first = self.do_publish(self.envelope(), publisher.probe(REPOSITORY, self.plan, gh_runner=self.api))
        old = first["head_sha"]
        self.git("reset", "--hard", self.base)
        self.put(f"{SOURCE}/alpha/guide.md", "# New upstream guide\n")
        self.put("README.md", "# Accepted unrelated main change\n")
        self.base = self.commit("main advances while bot PR stays open")
        self.git("push", str(self.origin), "HEAD:refs/heads/main")
        plan = protocol.plan(self.repo)
        envelope = self.envelope({"alpha/guide.md": "# Reviewed Hermes guide\n"})
        expected = publisher.probe(REPOSITORY, plan, gh_runner=self.api)
        self.assertFalse(expected["skip"])
        result = self.do_publish(envelope, expected)
        head = result["head_sha"]
        self.assertEqual(result["pr_number"], 1)
        self.assertEqual(len(self.api.prs), 1)
        self.assertEqual(self.api.git("show", "-s", "--format=%P", head), old + " " + self.base)
        self.api.git("merge-base", "--is-ancestor", old, head)
        self.assertEqual(self.api.git("show", head + ":" + ADAPTED + "/alpha/SKILL.md"), "# Hermes alpha",
                         "obsolete old-candidate alpha must not survive the rebuilt tree")
        self.assertEqual(self.api.git("show", head + ":" + ADAPTED + "/alpha/guide.md"), "# Reviewed Hermes guide")
        self.assertEqual(self.api.git("show", head + ":README.md"), "# Accepted unrelated main change")
        self.assertEqual(publisher.probe(REPOSITORY, plan, gh_runner=self.api)["pr_number"], 1)
        writes = [method for method, _, _ in self.api.calls if method != "GET"]
        self.assertEqual(writes, ["POST", "PATCH"])
        fetches = [args for args in self.git_calls if "fetch" in args]
        self.assertTrue(fetches)
        self.assertEqual(fetches[0][-1], old, "fetch the recorded object, never an arbitrary branch name")

    def test_latest_main_race_stops_before_branch_mutation(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        raced = []
        def main_moves(args):
            if "commit-tree" in args and not raced:
                tree = self.git("rev-parse", self.base + "^{tree}")
                new_main = self.git("commit-tree", tree, "-p", self.base, "-m", "concurrent main advance")
                self.git("push", str(self.origin), new_main + ":refs/heads/main")
                raced.append(new_main)
        with self.assertRaisesRegex(ValueError, "base|main|default"):
            self.do_publish(envelope, expected, before_git=main_moves)
        self.assertEqual(self.api.head("main"), raced[0])
        self.assertIsNone(self.api.head())
        self.assertFalse(any("push" in args for args in self.git_calls))
        self.assertEqual(self.api.prs, [])

    def test_unexpected_manual_branch_is_not_overwritten_even_when_fast_forwardable(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        def manual_branch_appears(args):
            if "commit-tree" in args:
                self.api.git("update-ref", "refs/heads/" + BRANCH, self.base)
        with self.assertRaisesRegex(ValueError, "branch|probe|head"):
            self.do_publish(envelope, expected, before_git=manual_branch_appears)
        self.assertEqual(self.api.head(), self.base)
        self.assertFalse(any("push" in args for args in self.git_calls))
        self.assertEqual(self.api.prs, [])

    def test_idempotent_publication_uses_existing_verified_pr_without_writes(self):
        envelope = self.envelope()
        first = self.do_publish(envelope, publisher.probe(REPOSITORY, self.plan, gh_runner=self.api))
        self.git("reset", "--hard", self.base)
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        self.assertTrue(expected["skip"])
        self.api.calls.clear()
        again = self.do_publish(envelope, expected)
        self.assertEqual(again, {**first, "status": "unchanged"})
        self.assertEqual(self.api.head(), first["head_sha"])
        self.assertEqual(len(self.api.prs), 1)
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
        self.assertFalse(any("push" in args or "commit-tree" in args for args in self.git_calls))

    def test_crash_after_push_recovers_missing_pr_without_another_commit(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        def crash(method, endpoint):
            if method == "POST":
                raise publisher.PublicationError("simulated crash before PR create")
        self.api.before_request = crash
        with self.assertRaisesRegex(ValueError, "simulated crash"):
            self.do_publish(envelope, expected)
        pushed = self.api.head()
        self.assertIsNotNone(pushed)
        self.assertEqual(self.api.prs, [])
        self.api.before_request = None
        self.git("reset", "--hard", self.base)
        retry_probe = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        self.assertEqual(retry_probe["expected_bot_branch_head"], pushed)
        self.assertIsNone(retry_probe["pr_number"])
        result = self.do_publish(envelope, expected)
        self.assertEqual(result["head_sha"], pushed)
        self.assertEqual(len(self.api.prs), 1)
        self.assertFalse(any("push" in args or "commit-tree" in args for args in self.git_calls))

    def interrupted_pr_update(self):
        first = self.do_publish(self.envelope(), publisher.probe(REPOSITORY, self.plan, gh_runner=self.api))
        self.git("reset", "--hard", self.base)
        self.put(f"{SOURCE}/alpha/guide.md", "# Next upstream guide\n")
        self.base = self.commit("source advances before interrupted PR update")
        self.git("push", str(self.origin), "HEAD:refs/heads/main")
        self.plan = protocol.plan(self.repo)
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        envelope = self.envelope({"alpha/guide.md": "# Next reviewed Hermes guide\n"})
        stale_body = self.api.prs[0]["body"]
        def crash(method, endpoint):
            if method == "PATCH" and endpoint == f"repos/{REPOSITORY}/pulls/1":
                raise publisher.PublicationError("simulated crash before PR update")
        self.api.before_request = crash
        with self.assertRaisesRegex(ValueError, "simulated crash"):
            self.do_publish(envelope, expected)
        pushed = self.api.head()
        assert pushed is not None
        self.assertNotEqual(pushed, first["head_sha"])
        self.assertEqual(self.api.prs[0]["body"], stale_body)
        self.api.before_request = None
        self.git("reset", "--hard", self.base)
        self.api.calls.clear()
        return envelope, expected, pushed

    def test_crash_after_push_recovers_stale_pr_with_original_probe_and_exact_tree(self):
        envelope, expected, pushed = self.interrupted_pr_update()
        with self.assertRaisesRegex(ValueError, "metadata differs"):
            publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        self.api.calls.clear()
        try:
            result = self.do_publish(envelope, expected)
        except publisher.PublicationError as exc:
            self.fail(f"exact-artifact retry must recover the interrupted PR update: {exc}")
        self.assertEqual(result, {"status": "published", "pr_number": 1,
                                  "url": f"https://github.com/{REPOSITORY}/pull/1",
                                  "head_sha": pushed, "branch": BRANCH})
        self.assertEqual(self.api.head(), pushed)
        self.assertEqual(len(self.api.prs), 1)
        self.assertFalse(any("push" in args or "commit-tree" in args for args in self.git_calls))
        writes = [(method, endpoint) for method, endpoint, _ in self.api.calls if method != "GET"]
        self.assertEqual(writes, [("PATCH", f"repos/{REPOSITORY}/pulls/1")])
        patch_index = next(index for index, call in enumerate(self.api.calls) if call[0] == "PATCH")
        reads_before_patch = [(method, endpoint) for method, endpoint, _ in self.api.calls[:patch_index]]
        self.assertIn(("GET", f"repos/{REPOSITORY}/pulls/1"), reads_before_patch)
        self.assertTrue(publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)["skip"])
        self.git("reset", "--hard", self.base)
        self.api.calls.clear()
        repeated = self.do_publish(envelope, expected)
        self.assertEqual(repeated, {**result, "status": "unchanged"})
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
        self.assertFalse(any("push" in args or "commit-tree" in args for args in self.git_calls))

    def test_stale_pr_recovery_rechecks_local_head_before_patch(self):
        envelope, expected, pushed = self.interrupted_pr_update()
        stale_body = self.api.prs[0]["body"]
        moved = []
        def move_local_head(args):
            if "write-tree" in args and not moved:
                tree = self.git("rev-parse", self.base + "^{tree}")
                sha = self.git("commit-tree", tree, "-p", self.base, "-m", "concurrent local HEAD")
                self.git("update-ref", "HEAD", sha)
                moved.append(sha)
        with self.assertRaisesRegex(ValueError, "HEAD|base"):
            self.do_publish(envelope, expected, before_git=move_local_head)
        self.assertEqual(self.git("rev-parse", "HEAD"), moved[0])
        self.assertEqual(self.api.head(), pushed)
        self.assertEqual(self.api.prs[0]["body"], stale_body)
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
        self.assertFalse(any("push" in args or "commit-tree" in args for args in self.git_calls))

    def test_stale_pr_recovery_rejects_nonexact_or_invalid_artifacts(self):
        envelope, expected, pushed = self.interrupted_pr_update()
        other = self.envelope({"alpha/guide.md": "# A different reviewed candidate\n"})
        stale_body = self.api.prs[0]["body"]
        for case in ("different-tree", "forged-hash", "dirty-target"):
            with self.subTest(case=case):
                self.git("reset", "--hard", self.base)
                self.api.calls.clear()
                candidate = json.loads(json.dumps(other if case == "different-tree" else envelope))
                if case == "forged-hash":
                    candidate["updates"][0]["after_sha256"] = "0" * 64
                elif case == "dirty-target":
                    self.put(f"{ADAPTED}/alpha/guide.md", "Keep manual checkout changes\n")
                with self.assertRaises(ValueError):
                    self.do_publish(candidate, expected)
                self.assertEqual(self.api.head(), pushed)
                self.assertEqual(self.api.prs[0]["body"], stale_body)
                self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
                self.assertFalse(any("push" in args or "commit-tree" in args for args in self.git_calls))

    def test_stale_pr_recovery_requires_original_protected_probe_bindings(self):
        envelope, expected, pushed = self.interrupted_pr_update()
        stale_body = self.api.prs[0]["body"]
        probes = [None, {**expected, "expected_bot_branch_head": None},
                  {**expected, "expected_bot_branch_head": pushed}, {**expected, "pr_number": 2},
                  {**expected, "default_branch": "other"}, {**expected, "extra": "untrusted"}]
        probes += [{**expected, key: "0" * 40}
                   for key in ("base_commit", "source_tree", "adaptation_tree")]
        for candidate in probes:
            with self.subTest(probe=candidate):
                self.api.calls.clear()
                with self.assertRaises(ValueError):
                    self.do_publish(envelope, candidate)
                self.assertEqual(self.api.head(), pushed)
                self.assertEqual(self.api.prs[0]["body"], stale_body)
                self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
                self.assertFalse(any("push" in args or "commit-tree" in args for args in self.git_calls))

    def test_stale_pr_recovery_rejects_edited_metadata_instead_of_repairing_it(self):
        envelope, expected, pushed = self.interrupted_pr_update()
        stale_body = self.api.prs[0]["body"]
        stale_metadata = publisher._metadata(stale_body, comment=True)
        for field in ("source_tree", "adaptation_tree", "result_tree"):
            with self.subTest(field=field):
                metadata = {**stale_metadata, field: "0" * 40}
                body = "<!-- pstack-hermes-publication:" + json.dumps(metadata) + " -->"
                self.api.prs[0]["body"] = body
                self.api.calls.clear()
                with self.assertRaisesRegex(ValueError, "metadata differs"):
                    self.do_publish(envelope, expected)
                self.assertEqual(self.api.head(), pushed)
                self.assertEqual(self.api.prs[0]["body"], body)
                self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
                self.assertFalse(any("push" in args or "commit-tree" in args for args in self.git_calls))

    def test_stale_pr_recovery_rejects_unrelated_bot_append_even_with_exact_tree(self):
        envelope, expected, pushed = self.interrupted_pr_update()
        commit = self.api.commit_json(pushed)
        identity = {**os.environ, "GIT_AUTHOR_NAME": BOT, "GIT_AUTHOR_EMAIL": EMAIL,
                    "GIT_COMMITTER_NAME": BOT, "GIT_COMMITTER_EMAIL": EMAIL}
        unrelated = self.git("commit-tree", commit["commit"]["tree"]["sha"],
                             "-p", pushed, "-p", self.base,
                             input=commit["commit"]["message"].encode(), env=identity)
        self.git("push", str(self.origin), unrelated + ":refs/heads/" + BRANCH)
        self.api.prs[0]["head"]["sha"] = unrelated
        with self.assertRaisesRegex(ValueError, "parents"):
            self.do_publish(envelope, expected)
        self.assertEqual(self.api.head(), unrelated)
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
        self.assertFalse(any("push" in args or "commit-tree" in args for args in self.git_calls))

    def test_stale_pr_recovery_rechecks_exact_pr_main_and_branch_before_patch(self):
        envelope, expected, pushed = self.interrupted_pr_update()
        original_pr = json.loads(json.dumps(self.api.prs[0]))
        human = self.git("commit-tree", self.api.git("rev-parse", pushed + "^{tree}"),
                         "-p", pushed, "-m", "manual branch advance during recovery")
        main = self.git("commit-tree", self.git("rev-parse", self.base + "^{tree}"),
                        "-p", self.base, "-m", "main advance during recovery")
        for case in ("human-close", "edited-body", "wrong-number", "fork", "human-author", "branch", "main"):
            with self.subTest(case=case):
                self.git("reset", "--hard", self.base)
                self.api.git("update-ref", "refs/heads/" + BRANCH, pushed)
                self.api.git("update-ref", "refs/heads/main", self.base)
                self.api.prs = [json.loads(json.dumps(original_pr))]
                self.api.calls.clear()
                exact_reads = []
                def concurrent_change(method, endpoint):
                    if method != "GET" or endpoint != f"repos/{REPOSITORY}/pulls/1":
                        return
                    exact_reads.append(endpoint)
                    if len(exact_reads) != 2:
                        return
                    pr = self.api.prs[0]
                    if case == "human-close":
                        pr["state"] = "closed"
                    elif case == "edited-body":
                        pr["body"] = "Human removed publication metadata"
                    elif case == "wrong-number":
                        pr["number"] = 2
                        pr["html_url"] = f"https://github.com/{REPOSITORY}/pull/2"
                    elif case == "fork":
                        pr["head"]["repo"]["full_name"] = "stranger/agent-skills"
                    elif case == "human-author":
                        pr["user"]["login"] = "maintainer"
                    elif case == "branch":
                        self.git("push", str(self.origin), human + ":refs/heads/" + BRANCH)
                    else:
                        self.git("push", str(self.origin), main + ":refs/heads/main")
                self.api.before_request = concurrent_change
                with self.assertRaises(ValueError):
                    self.do_publish(envelope, expected)
                self.assertEqual(len(exact_reads), 2, "re-read the exact PR after proving the result tree")
                self.assertEqual(self.api.prs[0]["body"],
                                 "Human removed publication metadata" if case == "edited-body" else original_pr["body"])
                self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
                self.assertFalse(any("push" in args or "commit-tree" in args for args in self.git_calls))

    def test_human_close_during_publication_blocks_before_push(self):
        first = self.do_publish(self.envelope(), publisher.probe(REPOSITORY, self.plan, gh_runner=self.api))
        self.git("reset", "--hard", self.base)
        self.put(f"{SOURCE}/alpha/SKILL.md", "# Another upstream delta\n")
        self.base = self.commit("next source change")
        self.git("push", str(self.origin), "HEAD:refs/heads/main")
        plan = protocol.plan(self.repo)
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, plan, gh_runner=self.api)
        def human_closes(args):
            if "commit-tree" in args:
                self.api.prs[0]["state"] = "closed"
        with self.assertRaises(ValueError):
            self.do_publish(envelope, expected, before_git=human_closes)
        self.assertEqual(self.api.head(), first["head_sha"], "human closure must be checked before branch writes")
        self.assertFalse(any("push" in args for args in self.git_calls))
        self.assertEqual(len(self.api.prs), 1)

    def test_pr_write_is_not_success_until_metadata_is_read_back(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        def change_after_write(method, endpoint):
            if method == "GET" and endpoint.endswith("/pulls/1"):
                self.api.prs[0]["body"] = "Human changed metadata after the API write"
        self.api.before_request = change_after_write
        with self.assertRaisesRegex(ValueError, "metadata|read.back"):
            self.do_publish(envelope, expected)
        self.assertEqual(len(self.api.prs), 1)
        self.assertIsNotNone(self.api.head())

    def test_readback_cannot_substitute_another_pr_number(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        def wrong_target(method, endpoint):
            if method == "GET" and endpoint.endswith("/pulls/1"):
                self.api.prs[0]["number"] = 2
                self.api.prs[0]["html_url"] = f"https://github.com/{REPOSITORY}/pull/2"
        self.api.before_request = wrong_target
        with self.assertRaisesRegex(ValueError, "number|target|read.back"):
            self.do_publish(envelope, expected)

    def test_probe_checks_bot_metadata_against_real_pinned_source_and_basis(self):
        self.seed_bot(plan={**self.plan, "source_tree": "0" * 40})
        with self.assertRaisesRegex(ValueError, "source|basis"):
            publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))

    def test_commit_uses_verified_bytes_not_post_apply_worktree_changes(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        def tamper_after_apply(args):
            if "read-tree" in args:
                self.put(f"{ADAPTED}/alpha/SKILL.md", "# Unreviewed concurrent worktree replacement\n")
        result = self.do_publish(envelope, expected, before_git=tamper_after_apply)
        self.assertEqual(self.api.git("show", result["head_sha"] + ":" + ADAPTED + "/alpha/SKILL.md"),
                         "# Reviewed Hermes alpha", "only verifier-normalized content can enter the commit tree")

    def test_duplicate_json_metadata_keys_are_not_last_wins(self):
        self.seed_bot()
        body = self.metadata_body().replace('"schema":1', '"schema":0,"schema":1')
        self.api.add_pr(body=body)
        with self.assertRaisesRegex(ValueError, "duplicate|metadata"):
            publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)

    def test_local_head_moving_after_apply_blocks_publication(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        moved = []
        def move_head(args):
            if "commit-tree" in args and not moved:
                tree = self.git("rev-parse", self.base + "^{tree}")
                sha = self.git("commit-tree", tree, "-p", self.base, "-m", "concurrent local HEAD")
                self.git("update-ref", "HEAD", sha)
                moved.append(sha)
        with self.assertRaisesRegex(ValueError, "HEAD|base"):
            self.do_publish(envelope, expected, before_git=move_head)
        self.assertIsNone(self.api.head())
        self.assertFalse(any("push" in args for args in self.git_calls))

    def test_multiple_push_destinations_are_rejected_before_applying_data(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        self.git("config", "--add", "remote.origin.pushurl", f"https://github.com/{REPOSITORY}.git")
        self.git("config", "--add", "remote.origin.pushurl", "https://github.com/other/repository.git")
        with self.assertRaisesRegex(ValueError, "origin|repository"):
            self.do_publish(envelope, expected)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertIsNone(self.api.head())

    def test_origin_url_variants_are_rejected_without_normalization(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        origin = f"https://github.com/{REPOSITORY}"
        urls = [
            f"http://github.com/{REPOSITORY}",
            f"https://github.example/{REPOSITORY}",
            "https://github.com/other/agent-skills",
            origin + "/extra",
            f"https://github.com/{REPOSITORY.lower()}",
            f"https://GITHUB.COM/{REPOSITORY}",
            f"git@github.com:{REPOSITORY}.git",
            f"ssh://git@github.com/{REPOSITORY}.git",
            f"https://username@github.com/{REPOSITORY}",
            f"https://x-access-token:fixture-token@github.com/{REPOSITORY}.git",
        ]
        urls += [base + ending for base in (origin, origin + ".git")
                 for ending in ("/", "?ref=main", "#fragment", " ", "\t", "\n")]
        urls += [" " + origin, "\t" + origin]
        for url in urls:
            with self.subTest(url=url):
                self.git("remote", "set-url", "origin", url)
                with self.assertRaisesRegex(ValueError, "origin|repository"):
                    self.do_publish(envelope, expected)
                self.assertEqual(self.git("status", "--porcelain"), "")
                self.assertIsNone(self.api.head())
                self.assertEqual(self.api.prs, [])
                self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
                self.assertFalse(any("fetch" in args or "push" in args for args in self.git_calls))

    def test_multiple_origin_urls_are_rejected_even_when_each_is_authorized(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        origin = f"https://github.com/{REPOSITORY}"
        for field in ("url", "pushurl"):
            for extra in (origin, origin + ".git", "https://github.com/other/repository.git"):
                with self.subTest(field=field, extra=extra):
                    self.git("config", "--replace-all", "remote.origin.url", origin)
                    self.git("config", "--replace-all", "remote.origin.pushurl", origin)
                    self.git("config", "--add", "remote.origin." + field, extra)
                    with self.assertRaisesRegex(ValueError, "origin|repository"):
                        self.do_publish(envelope, expected)
                    self.assertEqual(self.git("status", "--porcelain"), "")
                    self.assertIsNone(self.api.head())
                    self.assertEqual(self.api.prs, [])
                    self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
                    self.assertFalse(any("fetch" in args or "push" in args for args in self.git_calls))

    def test_authorized_fetch_and_push_urls_must_still_be_identical(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        origin = f"https://github.com/{REPOSITORY}"
        for fetch, push in ((origin, origin + ".git"), (origin + ".git", origin)):
            with self.subTest(fetch=fetch, push=push):
                self.git("config", "remote.origin.url", fetch)
                self.git("config", "remote.origin.pushurl", push)
                with self.assertRaisesRegex(ValueError, "origin|repository"):
                    self.do_publish(envelope, expected)
                self.assertEqual(self.git("status", "--porcelain"), "")
                self.assertIsNone(self.api.head())
                self.assertEqual(self.api.prs, [])
                self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
                self.assertFalse(any("fetch" in args or "push" in args for args in self.git_calls))

    def test_push_race_preserves_divergent_human_head_without_force_or_pr_write(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        raced = []
        def human_wins_after_final_read(args):
            if "push" in args and not raced:
                tree = self.git("rev-parse", self.base + "^{tree}")
                sha = self.git("commit-tree", tree, "-p", self.base, "-m", "human branch edit during push")
                self.git("push", str(self.origin), sha + ":refs/heads/" + BRANCH)
                raced.append(sha)
        with self.assertRaisesRegex(ValueError, "Git rejected"):
            self.do_publish(envelope, expected, before_git=human_wins_after_final_read)
        self.assertEqual(self.api.head(), raced[0])
        self.assertEqual(self.api.prs, [])
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
        pushes = [args for args in self.git_calls if "push" in args]
        self.assertEqual(len(pushes), 1)
        self.assertFalse(any("force" in arg or arg.startswith("+") for arg in pushes[0]))

    def test_manual_bot_branch_edit_blocks_probe_despite_copied_valid_trailer(self):
        old = self.seed_bot()
        tree = self.git("rev-parse", old + "^{tree}")
        message = "Human edit\n\nPstack-Hermes-Publication: " + json.dumps(self.metadata) + "\n"
        human = self.git("commit-tree", tree, "-p", old, input=message.encode())
        self.git("push", str(self.origin), human + ":refs/heads/" + BRANCH)
        with self.assertRaisesRegex(ValueError, "identity|untrusted"):
            publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        self.assertEqual(self.api.head(), human)

    def test_merged_old_pr_allows_a_new_pr_and_keeps_append_only_branch(self):
        first = self.do_publish(self.envelope(), publisher.probe(REPOSITORY, self.plan, gh_runner=self.api))
        self.git("reset", "--hard", self.base)
        self.git("merge", "--no-ff", "--no-edit", first["head_sha"])
        self.api.prs[0]["state"] = "closed"
        self.api.prs[0]["merged_at"] = "2026-01-01T00:00:00Z"
        self.put(f"{SOURCE}/alpha/guide.md", "# New source after accepted adaptation\n")
        self.base = self.commit("new source after manual merge")
        self.git("push", str(self.origin), "HEAD:refs/heads/main")
        plan = protocol.plan(self.repo)
        expected = publisher.probe(REPOSITORY, plan, gh_runner=self.api)
        self.assertEqual(expected["blocked_reasons"], [])
        self.assertIsNone(expected["pr_number"])
        self.assertFalse(expected["skip"])
        result = self.do_publish(self.envelope({"alpha/guide.md": "# New reviewed guide\n"}), expected)
        self.assertEqual(result["pr_number"], 2)
        self.assertEqual(len(self.api.prs), 2)
        self.api.git("merge-base", "--is-ancestor", first["head_sha"], result["head_sha"])
        self.assertEqual(self.api.prs[0]["state"], "closed")
        self.assertEqual(self.api.prs[1]["state"], "open")

    def test_main_drift_after_push_stops_before_pr_creation(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        raced = []
        def main_moves_after_branch_write(method, endpoint):
            if method == "GET" and "/git/ref/heads/automation" in endpoint and self.api.head() and not raced:
                tree = self.git("rev-parse", self.base + "^{tree}")
                sha = self.git("commit-tree", tree, "-p", self.base, "-m", "main advances after branch push")
                self.git("push", str(self.origin), sha + ":refs/heads/main")
                raced.append(sha)
        self.api.before_request = main_moves_after_branch_write
        with self.assertRaisesRegex(ValueError, "base|main|default"):
            self.do_publish(envelope, expected)
        self.assertIsNotNone(self.api.head(), "a verified push cannot be rolled back or deleted")
        self.assertEqual(self.api.prs, [])

    def test_publisher_revalidates_hashes_dirty_target_and_exact_local_base(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        for case in ("forged-hash", "dirty-target", "stale-head"):
            with self.subTest(case=case):
                self.git("reset", "--hard", self.base)
                candidate = json.loads(json.dumps(envelope))
                if case == "forged-hash":
                    candidate["updates"][0]["after_sha256"] = "0" * 64
                elif case == "dirty-target":
                    self.put(f"{ADAPTED}/alpha/SKILL.md", "Keep human worktree edits\n")
                else:
                    tree = self.git("rev-parse", self.base + "^{tree}")
                    moved = self.git("commit-tree", tree, "-p", self.base, "-m", "stale local checkout")
                    self.git("update-ref", "HEAD", moved)
                with self.assertRaises(ValueError):
                    self.do_publish(candidate, expected)
                self.assertIsNone(self.api.head())
                self.assertEqual(self.api.prs, [])
                self.assertFalse(any("push" in args or "commit-tree" in args for args in self.git_calls))
                if case == "dirty-target":
                    self.assertEqual((self.repo / ADAPTED / "alpha/SKILL.md").read_text(), "Keep human worktree edits\n")

    def test_real_index_and_outside_worktree_cannot_leak_into_publication_tree(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        self.put("README.md", "Staged outside changes must remain local\n")
        self.git("add", "README.md")
        self.put("outside-untracked.txt", "Untracked data must remain local\n")
        before_index = self.git("diff", "--cached", "--binary")
        result = self.do_publish(envelope, expected)
        self.assertEqual(self.git("diff", "--cached", "--binary"), before_index)
        self.assertEqual(self.api.git("show", result["head_sha"] + ":README.md"), "# Outside")
        self.assertNotIn("outside-untracked.txt", self.api.git("ls-tree", "-r", "--name-only", result["head_sha"]))

    def test_configured_clean_filters_are_rejected_before_protocol_can_execute_them(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        marker = self.root / "executed"
        trap = self.root / "trap.sh"
        trap.write_text("#!/bin/sh\nprintf fired > " + str(marker) + "\nexit 1\n")
        trap.chmod(0o755)
        for name in ("pre-commit", "post-commit", "pre-push"):
            hook = self.repo / ".git/hooks" / name
            hook.write_bytes(trap.read_bytes())
            hook.chmod(0o755)
        attributes = self.repo / ".git/info/attributes"
        attributes.write_text(f"{ADAPTED}/alpha/SKILL.md filter=trap\n")
        self.git("config", "filter.trap.clean", str(trap))
        self.git("config", "filter.trap.required", "true")
        with self.assertRaisesRegex(ValueError, "filter|configuration"):
            self.do_publish(envelope, expected)
        self.assertFalse(marker.exists(), "protocol status must not execute a configured clean filter")
        self.assertIsNone(self.api.head())

    def test_fetch_repository_cannot_differ_from_the_authorized_push_repository(self):
        self.seed_bot()
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        self.git("config", "remote.origin.url", "https://github.com/other/repository.git")
        self.git("config", "remote.origin.pushurl", f"https://github.com/{REPOSITORY}.git")
        with self.assertRaisesRegex(ValueError, "origin|repository"):
            self.do_publish(envelope, expected)
        self.assertFalse(any("fetch" in args or "push" in args for args in self.git_calls))
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_git_hooks_are_bypassed_for_commit_and_push(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        marker = self.root / "hook-executed"
        for name in ("pre-commit", "post-commit", "pre-push"):
            hook = self.repo / ".git/hooks" / name
            hook.write_text("#!/bin/sh\nprintf fired > " + str(marker) + "\nexit 1\n")
            hook.chmod(0o755)
        result = self.do_publish(envelope, expected)
        self.assertEqual(result["status"], "published")
        self.assertFalse(marker.exists())

    def test_oversized_pr_summary_is_rejected_before_branch_push(self):
        for index in range(65):
            self.put(f"{SOURCE}/alpha/reference-{index}.md", "Old upstream reference\n")
            self.put(f"{ADAPTED}/alpha/reference-{index}.md", "Hermes reference\n")
        checkpoint_commit = self.commit("establish many existing references")
        self.put(f"{ADAPTED}/UPSTREAM.json", json.dumps({
            "schema": 1, "source_commit": checkpoint_commit,
            "source_tree": self.git("rev-parse", f"{checkpoint_commit}:{SOURCE}"),
        }) + "\n")
        self.commit("accept reference checkpoint")
        for index in range(65):
            self.put(f"{SOURCE}/alpha/reference-{index}.md", "New upstream reference\n")
        self.base = self.commit("large but otherwise supported documentation delta")
        self.git("push", str(self.origin), "HEAD:refs/heads/main")
        plan = protocol.plan(self.repo)
        dest = self.root / "large-candidate"
        protocol.materialize(self.repo, plan, dest)
        envelope = protocol.collect(self.repo, plan, dest / "candidate")
        expected = publisher.probe(REPOSITORY, plan, gh_runner=self.api)
        with self.assertRaisesRegex(ValueError, "bounded|too many"):
            self.do_publish(envelope, expected)
        self.assertIsNone(self.api.head(), "unpublishable PR metadata must be rejected before a branch write")
        self.assertFalse(any("push" in args for args in self.git_calls))

    def test_repeating_same_verified_artifact_with_original_probe_is_idempotent(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        first = self.do_publish(envelope, expected)
        self.git("reset", "--hard", self.base)
        self.api.calls.clear()
        repeated = self.do_publish(envelope, expected)
        self.assertEqual(repeated, {**first, "status": "unchanged"})
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
        self.assertFalse(any("push" in args or "commit-tree" in args for args in self.git_calls))

    def test_original_probe_cannot_accept_a_different_bot_candidate_as_its_retry(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        other = self.seed_bot(updates={"alpha/SKILL.md": "# A different bot candidate\n"})
        self.api.add_pr(body=self.metadata_body())
        with self.assertRaisesRegex(ValueError, "drift|exact retry"):
            self.do_publish(envelope, expected)
        self.assertEqual(self.api.head(), other)
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
        self.assertFalse(any("push" in args for args in self.git_calls))

    def test_manual_branch_edit_after_push_prevents_pr_creation(self):
        envelope = self.envelope()
        expected = publisher.probe(REPOSITORY, self.plan, gh_runner=self.api)
        raced = []
        def human_edits_before_pr_write(method, endpoint):
            if method == "GET" and endpoint.endswith("/git/ref/heads/main") and self.api.head() and not raced:
                old = self.api.head()
                assert old is not None
                tree = self.git("rev-parse", old + "^{tree}")
                human = self.git("commit-tree", tree, "-p", old, "-m", "human edits after bot push")
                self.git("push", str(self.origin), human + ":refs/heads/" + BRANCH)
                raced.append(human)
        self.api.before_request = human_edits_before_pr_write
        with self.assertRaisesRegex(ValueError, "branch|head"):
            self.do_publish(envelope, expected)
        self.assertEqual(self.api.head(), raced[0])
        self.assertEqual(self.api.prs, [], "never open a PR on an unverified replacement head")

    def test_repository_is_validated_before_any_api_request(self):
        self.assertTrue(callable(getattr(publisher, "probe", None)), "probe() is missing")
        calls = []
        def forbidden_api(*args, **kwargs):
            calls.append(args)
            self.fail("invalid repository reached GitHub")
        for repository in ("owner", "owner/repo/extra", "../repo", "-owner/repo",
                           "owner/repo?x=y", "other/repo", REPOSITORY + "\n"):
            with self.subTest(repository=repository), self.assertRaises(ValueError):
                publisher.probe(repository, {}, gh_runner=forbidden_api)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()

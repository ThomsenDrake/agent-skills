"""Real, offline Git histories exercise the updater's data boundary.

Run: /usr/bin/python3 -m unittest discover -s skills/pstack-hermes/automation/tests -p test_protocol.py -v
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


MODULE = Path(__file__).resolve().parents[1] / "protocol.py"
SPEC = importlib.util.spec_from_file_location("pstack_protocol", MODULE)
assert SPEC is not None and SPEC.loader is not None
protocol = importlib.util.module_from_spec(SPEC)
if MODULE.exists():
    SPEC.loader.exec_module(protocol)

SOURCE = "skills/pstack"
ADAPTED = "skills/pstack-hermes"


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ["TMPDIR"])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Protocol Test")
        self.git("config", "user.email", "protocol@example.invalid")
        self.git("config", "core.filemode", "true")
        self.put(f"{SOURCE}/SKILL.md", "# Upstream index\n")
        self.put(f"{SOURCE}/alpha/SKILL.md", "# Upstream alpha\n")
        self.put(f"{SOURCE}/alpha/references/guide.md", "Upstream guide\n")
        self.put(f"{SOURCE}/agents/poteto-agent.md", "Upstream bot\n")
        self.put(f"{SOURCE}/agents/comment-sicko.md", "Upstream reviewer\n")
        self.put(f"{SOURCE}/alpha/scripts/check.py", "print('original')\n")
        self.put(f"{ADAPTED}/SKILL.md", "# Hermes index\n")
        self.put(f"{ADAPTED}/alpha/SKILL.md", "# Hermes alpha\n")
        self.put(f"{ADAPTED}/alpha/references/guide.md", "Hermes guide\n")
        self.put(f"{ADAPTED}/bots/poteto-agent/SOUL.md", "Hermes bot\n")
        self.put(f"{ADAPTED}/bots/comment-sicko/SOUL.md", "Hermes reviewer\n")
        self.put(f"{ADAPTED}/alpha/scripts/check.py", "print('adapted')\n")
        self.put(f"{ADAPTED}/automation/controller.py", "# protected controller\n")
        self.put(f"{ADAPTED}/tests/test_contract.py", "# protected tests\n")
        self.put(f"{ADAPTED}/references/verification.md", "Protected verification\n")
        self.put(f"{ADAPTED}/references/smoke/result.md", "Protected smoke\n")
        self.put(f"{ADAPTED}/.gitignore", "__pycache__/\n")
        self.put("README.md", "Outside package\n")
        self.upstream = self.commit("initial source and adaptation")
        self.source_tree = self.git("rev-parse", f"{self.upstream}:{SOURCE}")
        self.put(f"{ADAPTED}/UPSTREAM.json", json.dumps({
            "schema": 1, "source_commit": self.upstream,
            "source_tree": self.source_tree,
        }) + "\n")
        self.base = self.commit("record checkpoint")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.repo), *args], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.decode().strip()

    def put(self, relative, content):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            path.write_bytes(content)
        return path

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD")

    def changed(self, path="alpha/SKILL.md"):
        self.put(f"{SOURCE}/{path}", "# Changed upstream\n")
        self.base = self.commit("upstream documentation delta")
        return protocol.plan(self.repo)

    def candidate(self, result, name="snapshots"):
        dest = self.root / name
        protocol.materialize(self.repo, result, dest)
        return dest / "candidate"

    def test_collect_emits_bound_markdown_data_and_accepts_empty_semantic_update(self):
        result = self.changed()
        candidate = self.candidate(result)
        self.assertTrue(callable(getattr(protocol, "collect", None)),
                        "collect() is not implemented")
        empty = protocol.collect(self.repo, result, candidate)
        bindings = ("schema", "base_commit", "base_source_commit", "base_source_tree",
                    "source_commit", "source_tree", "adaptation_tree")
        self.assertEqual(empty, {**{key: result[key] for key in bindings}, "updates": []})
        text = "# Updated Hermes alpha\n\nPreserve \u00e9 and LF exactly.\n"
        (candidate / "alpha/SKILL.md").write_text(text, encoding="utf-8")
        envelope = protocol.collect(self.repo, result, candidate)
        self.assertEqual(envelope, {**empty, "updates": [{
            "path": "alpha/SKILL.md",
            "before_sha256": hashlib.sha256(b"# Hermes alpha\n").hexdigest(),
            "content": text,
            "after_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }]})
        self.assertEqual(json.loads(json.dumps(envelope)), envelope)
        self.assertEqual((self.repo / ADAPTED / "alpha/SKILL.md").read_text(), "# Hermes alpha\n")
        checkpoint = json.loads((self.repo / ADAPTED / "UPSTREAM.json").read_text())
        self.assertEqual(checkpoint["source_commit"], self.upstream)

    def envelope(self):
        result = self.changed()
        candidate = self.candidate(result)
        (candidate / "alpha/SKILL.md").write_text("# Reviewed Hermes change\n", encoding="utf-8")
        return result, protocol.collect(self.repo, result, candidate)

    def test_apply_rejects_forged_bindings_shape_duplicates_and_hashes_before_writes(self):
        result, valid = self.envelope()
        cases = [*valid.keys(), "update-extra", "duplicate", "before-hash", "after-hash"]
        for case in cases:
            with self.subTest(case=case):
                self.git("reset", "--hard", self.base)
                forged = json.loads(json.dumps(valid))
                if case == "schema":
                    forged[case] = True
                elif case in result:
                    forged[case] = "0" * 40
                elif case == "updates":
                    forged["model_metadata"] = {"review": "trust me"}
                elif case == "update-extra":
                    forged["updates"][0]["command"] = "execute nothing"
                elif case == "duplicate":
                    forged["updates"].append(dict(forged["updates"][0]))
                elif case == "before-hash":
                    forged["updates"][0]["before_sha256"] = "0" * 64
                elif case == "after-hash":
                    forged["updates"][0]["after_sha256"] = "0" * 64
                with self.assertRaises(ValueError):
                    protocol.apply(self.repo, forged)
                self.assertEqual(self.git("status", "--porcelain"), "")
                self.assertEqual(self.git("rev-parse", "HEAD"), self.base)

    def test_apply_refuses_stale_head_even_when_only_unrelated_files_changed(self):
        result, valid = self.envelope()
        for relative in ("README.md", f"{SOURCE}/alpha/SKILL.md", f"{ADAPTED}/SKILL.md"):
            with self.subTest(path=relative):
                self.git("reset", "--hard", self.base)
                self.put(relative, "New trusted branch state\n")
                head = self.commit("branch moved after candidate generation")
                with self.assertRaises(ValueError):
                    protocol.apply(self.repo, valid)
                self.assertEqual(self.git("rev-parse", "HEAD"), head)
                self.assertEqual(self.git("status", "--porcelain"), "")

    def test_apply_refuses_dirty_source_targets_checkpoint_policy_and_index(self):
        result, valid = self.envelope()
        cases = ("target", "source", "checkpoint", "policy", "mode", "index", "assume-unchanged")
        for case in cases:
            with self.subTest(case=case):
                self.git("update-index", "--no-assume-unchanged", f"{ADAPTED}/alpha/SKILL.md")
                self.git("reset", "--hard", self.base)
                relative = {
                    "source": f"{SOURCE}/alpha/SKILL.md",
                    "checkpoint": f"{ADAPTED}/UPSTREAM.json",
                    "policy": f"{ADAPTED}/automation/controller.py",
                }.get(case, f"{ADAPTED}/alpha/SKILL.md")
                if case == "mode":
                    (self.repo / relative).chmod(0o755)
                else:
                    self.put(relative, "Locally dirty bytes\n")
                if case == "index":
                    self.git("add", relative)
                elif case == "assume-unchanged":
                    self.git("update-index", "--assume-unchanged", relative)
                before = (self.repo / relative).read_bytes()
                checkpoint = (self.repo / ADAPTED / "UPSTREAM.json").read_bytes()
                with self.assertRaises(ValueError):
                    protocol.apply(self.repo, valid)
                self.assertEqual((self.repo / relative).read_bytes(), before)
                self.assertEqual((self.repo / ADAPTED / "UPSTREAM.json").read_bytes(), checkpoint)

    def test_apply_never_follows_a_target_redirect_after_cleanliness_check(self):
        result, valid = self.envelope()
        target = self.repo / ADAPTED / "alpha/SKILL.md"
        outside = self.root / "not-a-publication-target"
        outside.write_bytes(target.read_bytes())
        checkpoint = (self.repo / ADAPTED / "UPSTREAM.json").read_bytes()
        original = protocol._clean_publication_tree

        def swap_after_check(repo, expected):
            original(repo, expected)
            target.unlink()
            target.symlink_to(outside)

        with mock.patch.object(protocol, "_clean_publication_tree", side_effect=swap_after_check):
            with self.assertRaises((ValueError, OSError)):
                protocol.apply(self.repo, valid)
        self.assertEqual(outside.read_bytes(), b"# Hermes alpha\n")
        self.assertEqual((self.repo / ADAPTED / "UPSTREAM.json").read_bytes(), checkpoint)

    def test_apply_rejects_path_attacks_and_protected_updates(self):
        result, valid = self.envelope()
        sentinel = self.root / "sentinel.md"
        sentinel.write_text("not writable by the publisher\n")
        paths = ("../sentinel.md", str(sentinel), "alpha/../SKILL.md", "alpha//SKILL.md",
                 "alpha\\SKILL.md", "alpha/line\nbreak.md", "alpha/./SKILL.md",
                 "automation/controller.py", "tests/test_contract.py", "UPSTREAM.json",
                 "references/verification.md", "references/smoke/result.md", ".gitignore",
                 "alpha/scripts/check.py", "alpha/references/guide.md", ".git/config")
        for path in paths:
            with self.subTest(path=repr(path)):
                forged = json.loads(json.dumps(valid))
                forged["updates"][0]["path"] = path
                with self.assertRaises(ValueError):
                    protocol.apply(self.repo, forged)
                self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(sentinel.read_text(), "not writable by the publisher\n")

    def test_apply_rejects_malformed_content_and_update_container_types(self):
        result, valid = self.envelope()
        for updates in (None, {}, "not a list", [None], [*valid["updates"]] * 65):
            with self.subTest(container=type(updates).__name__):
                with self.assertRaises(ValueError):
                    protocol.apply(self.repo, dict(valid, updates=updates))
        for content in (None, 1, "x" * (512 * 1024 + 1), "bad\0text", "bad\ud800"):
            with self.subTest(content_type=type(content).__name__):
                forged = json.loads(json.dumps(valid))
                forged["updates"][0]["content"] = content
                with self.assertRaises(ValueError):
                    protocol.apply(self.repo, forged)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_empty_reviewed_update_only_advances_controller_checkpoint(self):
        result = self.changed()
        candidate = self.candidate(result)
        envelope = protocol.collect(self.repo, result, candidate)
        self.assertEqual(envelope["updates"], [])
        protocol.apply(self.repo, envelope)
        self.assertEqual(self.git("diff", "--name-only"), f"{ADAPTED}/UPSTREAM.json")
        self.assertEqual(json.loads((self.repo / ADAPTED / "UPSTREAM.json").read_text()), {
            "schema": 1, "source_commit": result["source_commit"], "source_tree": result["source_tree"],
        })

    def test_checkpoint_does_not_advance_when_atomic_publication_fails(self):
        result, valid = self.envelope()
        checkpoint = (self.repo / ADAPTED / "UPSTREAM.json").read_bytes()
        replace = os.replace

        def fail_checkpoint(src, dest, **kwargs):
            if dest == "UPSTREAM.json":
                raise OSError("simulated filesystem failure")
            return replace(src, dest, **kwargs)

        with mock.patch.object(protocol.os, "replace", side_effect=fail_checkpoint):
            with self.assertRaises(OSError):
                protocol.apply(self.repo, valid)
        self.assertEqual((self.repo / ADAPTED / "UPSTREAM.json").read_bytes(), checkpoint)
        self.assertEqual((self.repo / ADAPTED / "alpha/SKILL.md").read_text(), valid["updates"][0]["content"])
        self.assertFalse(list((self.repo / ADAPTED).rglob(".pstack-update-*")))

    def test_collect_apply_roundtrip_writes_only_markdown_and_controller_checkpoint(self):
        result = self.changed()
        candidate = self.candidate(result)
        text = "# Revised Hermes alpha\n"
        (candidate / "alpha/SKILL.md").write_text(text, encoding="utf-8")
        envelope = protocol.collect(self.repo, result, candidate)
        vendor_before = (self.repo / SOURCE / "alpha/SKILL.md").read_bytes()
        self.assertTrue(callable(getattr(protocol, "apply", None)),
                        "apply() is not implemented")
        protocol.apply(self.repo, envelope)
        self.assertEqual((self.repo / ADAPTED / "alpha/SKILL.md").read_text(), text)
        self.assertEqual(json.loads((self.repo / ADAPTED / "UPSTREAM.json").read_text()), {
            "schema": 1, "source_commit": result["source_commit"],
            "source_tree": result["source_tree"],
        })
        self.assertEqual(self.git("rev-parse", "HEAD"), self.base)
        self.assertEqual(self.git("diff", "--name-only").splitlines(), [
            f"{ADAPTED}/UPSTREAM.json", f"{ADAPTED}/alpha/SKILL.md",
        ])
        self.assertEqual((self.repo / SOURCE / "alpha/SKILL.md").read_bytes(), vendor_before)
        self.assertEqual(self.git("diff", "--", SOURCE), "")
        self.assertEqual(self.git("diff", "--cached"), "")

    def test_collect_rejects_every_protected_or_unmapped_candidate_change(self):
        result = self.changed()
        forbidden = ("automation/controller.py", "tests/test_contract.py",
                     "references/verification.md", "references/smoke/result.md",
                     "UPSTREAM.json", ".gitignore", "alpha/scripts/check.py",
                     "alpha/references/guide.md", "bots/poteto-agent/SOUL.md")
        for number, relative in enumerate(forbidden):
            with self.subTest(path=relative):
                candidate = self.candidate(result, f"protected-{number}")
                (candidate / relative).write_text("Untrusted replacement\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    protocol.collect(self.repo, result, candidate)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_collect_rejects_structural_mode_and_text_attacks(self):
        result = self.changed()
        cases = ("symlink-file", "symlink-dir", "symlink-root", "extra", "missing",
                 "empty-dir", "mode", "non-utf8", "nul", "oversize", "fifo", "hardlink")
        for number, case in enumerate(cases):
            with self.subTest(case=case):
                candidate = self.candidate(result, f"attack-{number}")
                path = candidate / "alpha/SKILL.md"
                if case == "symlink-file":
                    path.unlink()
                    path.symlink_to(candidate.parent / "current-hermes/alpha/SKILL.md")
                elif case == "symlink-dir":
                    shutil.rmtree(candidate / "alpha")
                    (candidate / "alpha").symlink_to(candidate.parent / "current-hermes/alpha", target_is_directory=True)
                elif case == "symlink-root":
                    link = self.root / "linked-candidate"
                    link.symlink_to(candidate, target_is_directory=True)
                    candidate = link
                elif case == "extra":
                    (candidate / "extra.md").write_text("extra\n")
                elif case == "missing":
                    path.unlink()
                elif case == "empty-dir":
                    (candidate / "extra-dir").mkdir()
                elif case == "mode":
                    path.chmod(0o755)
                elif case == "non-utf8":
                    path.write_bytes(b"\xff")
                elif case == "nul":
                    path.write_bytes(b"binary\0data")
                elif case == "oversize":
                    path.write_bytes(b"x" * (512 * 1024 + 1))
                elif case == "fifo":
                    os.mkfifo(candidate / "surprise.md")
                elif case == "hardlink":
                    path.unlink()
                    os.link(candidate.parent / "current-hermes/alpha/SKILL.md", path)
                with self.assertRaises((ValueError, OSError)):
                    protocol.collect(self.repo, result, candidate)

    def test_materialize_rejects_redirects_nonempty_destinations_and_repo_writes(self):
        result = self.changed()
        outside = self.root / "outside"
        outside.mkdir()
        link = self.root / "redirect"
        link.symlink_to(outside, target_is_directory=True)
        occupied = self.root / "occupied"
        occupied.mkdir()
        (occupied / "sentinel").write_text("keep\n")
        for dest in (link, link / "nested", occupied, self.repo / SOURCE / "generated"):
            with self.subTest(dest=str(dest)):
                with self.assertRaises((ValueError, OSError)):
                    protocol.materialize(self.repo, result, dest)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual([path.name for path in occupied.iterdir()], ["sentinel"])
        self.assertEqual(self.git("status", "--porcelain"), "")
        empty = self.root / "precreated-empty"
        empty.mkdir()
        protocol.materialize(self.repo, result, empty)
        self.assertTrue((empty / "candidate/alpha/SKILL.md").is_file())

    def record_checkpoint(self):
        commit = self.git("rev-parse", "HEAD")
        tree = self.git("rev-parse", f"{commit}:{SOURCE}")
        self.put(f"{ADAPTED}/UPSTREAM.json", json.dumps({
            "schema": 1, "source_commit": commit, "source_tree": tree,
        }) + "\n")
        self.base = self.commit("record new fixture checkpoint")

    def test_source_cannot_grant_protected_or_nonleaf_markdown_scope(self):
        for relative in ("automation/policy.md", "tests/contract.md",
                         "references/verification.md", "references/smoke/proof.md",
                         "miscellaneous/note.md"):
            self.put(f"{SOURCE}/{relative}", "Previous upstream text\n")
            self.put(f"{ADAPTED}/{relative}", "Controller-owned text\n")
        self.commit("established nonleaf and protected paths")
        self.record_checkpoint()
        for relative in ("automation/policy.md", "tests/contract.md",
                         "references/verification.md", "references/smoke/proof.md",
                         "miscellaneous/note.md"):
            self.put(f"{SOURCE}/{relative}", "Malicious new policy instructions\n")
        self.commit("untrusted source attempts policy authority")
        result = protocol.plan(self.repo)
        self.assertTrue(result["blocked_reasons"])
        self.assertEqual(result["allowed_paths"], [])
        with self.assertRaises(ValueError):
            protocol.materialize(self.repo, result, self.root / "blocked")

    def test_plan_blocks_oversized_binary_or_nonregular_source_snapshots(self):
        original = self.base
        for case in ("oversize", "non-utf8", "nul", "adapted-symlink"):
            with self.subTest(case=case):
                self.git("reset", "--hard", original)
                data = {"oversize": b"x" * (512 * 1024 + 1),
                        "non-utf8": b"\xff", "nul": b"bad\0text"}.get(case, b"changed\n")
                self.put(f"{SOURCE}/alpha/SKILL.md", data)
                if case == "adapted-symlink":
                    target = self.repo / ADAPTED / "alpha/references/guide.md"
                    target.unlink()
                    target.symlink_to("/etc/passwd")
                self.commit(f"unsafe snapshot: {case}")
                result = protocol.plan(self.repo)
                self.assertTrue(result["blocked_reasons"], case)
                self.assertEqual(result["allowed_paths"], [])
                with self.assertRaises(ValueError):
                    protocol.materialize(self.repo, result, self.root / case)

    def test_git_tree_awkward_paths_are_rejected_not_normalized(self):
        original = self.base
        for relative in ("alpha/bad name.md", "alpha/back\\slash.md",
                         "alpha/line\nbreak.md", "alpha/.env", "alpha/control\x7f.md"):
            with self.subTest(path=repr(relative)):
                self.git("reset", "--hard", original)
                self.put(f"{SOURCE}/{relative}", "Untrusted path\n")
                self.commit("source path policy violation")
                with self.assertRaises(ValueError):
                    protocol.plan(self.repo)

    def test_checkpoint_is_strict_regular_bounded_and_matches_source_tree(self):
        original = self.base
        checkpoint = {"schema": 1, "source_commit": self.upstream, "source_tree": self.source_tree}
        for case in ("duplicate", "wrong-tree", "unknown", "bool-schema", "symlink", "executable", "oversize"):
            with self.subTest(case=case):
                self.git("reset", "--hard", original)
                data = dict(checkpoint)
                if case == "wrong-tree":
                    data["source_tree"] = self.git("rev-parse", "HEAD^{tree}")
                elif case == "unknown":
                    data["approved"] = True
                elif case == "bool-schema":
                    data["schema"] = True
                text = json.dumps(data)
                if case == "duplicate":
                    text = text.replace('"schema": 1', '"schema": 1, "schema": 1')
                elif case == "oversize":
                    text += " " * (512 * 1024)
                path = self.put(f"{ADAPTED}/UPSTREAM.json", text)
                if case == "symlink":
                    path.unlink()
                    path.symlink_to(text)
                elif case == "executable":
                    path.chmod(0o755)
                self.commit(f"invalid checkpoint: {case}")
                with self.assertRaises(ValueError):
                    protocol.plan(self.repo)

    def test_checkpoint_source_commit_must_be_in_target_history(self):
        unrelated = self.git("commit-tree", self.git("rev-parse", "HEAD^{tree}"), "-m", "unrelated root")
        self.put(f"{ADAPTED}/UPSTREAM.json", json.dumps({
            "schema": 1, "source_commit": unrelated, "source_tree": self.source_tree,
        }))
        self.commit("checkpoint from unrelated source history")
        with self.assertRaises(ValueError):
            protocol.plan(self.repo)

    def test_noop_does_not_bypass_git_tree_path_validation(self):
        self.put(f"{SOURCE}/alpha/bad name.md", "unsafe path\n")
        self.commit("established unsafe source path")
        self.record_checkpoint()
        with self.assertRaises(ValueError):
            protocol.plan(self.repo)

    def reference_delta(self, count):
        paths = [f"alpha/references/reference-{number:02d}.md" for number in range(count)]
        for relative in paths:
            self.put(f"{SOURCE}/{relative}", "Old upstream reference\n")
            self.put(f"{ADAPTED}/{relative}", "Old Hermes reference\n")
        self.commit("established references")
        self.record_checkpoint()
        for relative in paths:
            self.put(f"{SOURCE}/{relative}", "New upstream reference\n")
        self.base = self.commit("changed references")
        return protocol.plan(self.repo), paths

    def test_collect_caps_genuine_updates_at_64_and_two_mebibytes(self):
        result, paths = self.reference_delta(65)
        candidate = self.candidate(result)
        for relative in paths:
            (candidate / relative).write_text("New Hermes reference\n")
        with self.assertRaises(ValueError):
            protocol.collect(self.repo, result, candidate)
        for relative in paths[5:]:
            (candidate / relative).write_text("Old Hermes reference\n")
        for relative in paths[:5]:
            (candidate / relative).write_bytes(b"x" * (512 * 1024))
        with self.assertRaises(ValueError):
            protocol.collect(self.repo, result, candidate)

    def test_apply_caps_total_update_bytes_before_any_write(self):
        result, paths = self.reference_delta(5)
        content = "x" * (512 * 1024)
        updates = [{"path": relative, "content": content,
                    "before_sha256": hashlib.sha256(b"Old Hermes reference\n").hexdigest(),
                    "after_sha256": hashlib.sha256(content.encode()).hexdigest()} for relative in paths]
        envelope = {key: result[key] for key in (
            "schema", "base_commit", "base_source_commit", "base_source_tree",
            "source_commit", "source_tree", "adaptation_tree")}
        envelope["updates"] = updates
        with self.assertRaises(ValueError):
            protocol.apply(self.repo, envelope)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_materialize_uses_git_blobs_and_full_consistent_candidate_snapshot(self):
        script = self.repo / ADAPTED / "alpha/scripts/check.py"
        script.chmod(0o755)
        self.commit("retain adapted executable bit")
        result = self.changed()
        self.put(f"{SOURCE}/alpha/SKILL.md", "Dirty source must not leak\n")
        self.put(f"{ADAPTED}/alpha/SKILL.md", "Dirty adaptation must not leak\n")
        self.assertTrue(callable(getattr(protocol, "materialize", None)),
                        "materialize() is not implemented")
        dest = self.root / "snapshots"
        protocol.materialize(self.repo, result, dest)
        self.assertEqual({path.name for path in dest.iterdir()}, {
            "old-upstream", "new-upstream", "current-hermes", "candidate",
        })
        self.assertEqual((dest / "old-upstream/alpha/SKILL.md").read_text(), "# Upstream alpha\n")
        self.assertEqual((dest / "new-upstream/alpha/SKILL.md").read_text(), "# Changed upstream\n")
        self.assertEqual((dest / "current-hermes/alpha/SKILL.md").read_text(), "# Hermes alpha\n")
        self.assertEqual((dest / "candidate/alpha/SKILL.md").read_text(), "# Hermes alpha\n")
        expected = set(self.git("ls-tree", "-r", "--name-only", f"{self.base}:{ADAPTED}").splitlines())
        for name in ("current-hermes", "candidate"):
            actual = {path.relative_to(dest / name).as_posix()
                      for path in (dest / name).rglob("*") if path.is_file()}
            self.assertEqual(actual, expected)
            self.assertEqual((dest / name / "alpha/scripts/check.py").stat().st_mode & 0o777, 0o755)
        self.assertFalse(any(path.name == ".git" for path in dest.rglob("*")))

    def test_materialize_refuses_inactive_or_forged_plans_before_writing(self):
        noop = protocol.plan(self.repo)
        live = self.changed()
        forged = dict(live, allowed_paths=["automation/controller.py"])
        self.put(f"{SOURCE}/alpha/scripts/check.py", "print('changed')\n")
        self.commit("blocked source")
        blocked = protocol.plan(self.repo)
        for name, result in (("noop", noop), ("forged", forged), ("blocked", blocked)):
            with self.subTest(case=name):
                dest = self.root / name
                with self.assertRaises(ValueError):
                    protocol.materialize(self.repo, result, dest)
                self.assertFalse(dest.exists())
                with self.assertRaises(ValueError):
                    protocol.collect(self.repo, result, self.root / "does-not-exist")
        bindings = ("schema", "base_commit", "base_source_commit", "base_source_tree",
                    "source_commit", "source_tree", "adaptation_tree")
        for result in (noop, blocked):
            with self.assertRaises(ValueError):
                protocol.apply(self.repo, {**{key: result[key] for key in bindings}, "updates": []})

    def test_unsupported_source_changes_require_manual_review_without_partial_scope(self):
        original = self.base
        cases = ("code", "add", "delete", "rename", "mode", "symlink", "leaf", "executable")
        for case in cases:
            with self.subTest(case=case):
                self.git("reset", "--hard", original)
                path = self.repo / SOURCE / "alpha/SKILL.md"
                if case == "code":
                    self.put(f"{SOURCE}/alpha/scripts/check.py", "print('changed')\n")
                elif case == "add":
                    self.put(f"{SOURCE}/alpha/new.md", "New reference\n")
                elif case == "delete":
                    path.unlink()
                elif case == "rename":
                    path.rename(path.with_name("renamed.md"))
                elif case == "mode":
                    path.chmod(0o755)
                elif case == "symlink":
                    path.unlink()
                    path.symlink_to("/etc/passwd")
                elif case == "leaf":
                    self.put(f"{SOURCE}/new-leaf/SKILL.md", "New leaf\n")
                elif case == "executable":
                    self.put(f"{SOURCE}/alpha/scripts/check.py", "print('changed')\n").chmod(0o755)
                self.commit(f"unsupported source change: {case}")
                result = protocol.plan(self.repo)
                self.assertTrue(result["changed_paths"])
                self.assertFalse(result["noop"])
                self.assertTrue(result["blocked_reasons"], case)
                self.assertTrue(all("manual review" in reason for reason in result["blocked_reasons"]))
                self.assertEqual(result["allowed_paths"], [])

    def test_markdown_delta_maps_only_counterparts_and_root_index(self):
        for relative in ("alpha/SKILL.md", "alpha/references/guide.md",
                         "agents/poteto-agent.md", "agents/comment-sicko.md"):
            self.put(f"{SOURCE}/{relative}", "Changed source Markdown\n")
        self.base = self.commit("source Markdown changes")
        result = protocol.plan(self.repo)
        self.assertFalse(result["noop"])
        self.assertEqual(result["blocked_reasons"], [])
        self.assertEqual(result["changed_paths"], [
            "agents/comment-sicko.md", "agents/poteto-agent.md",
            "alpha/SKILL.md", "alpha/references/guide.md",
        ])
        self.assertEqual(result["allowed_paths"], [
            "SKILL.md", "alpha/SKILL.md", "alpha/references/guide.md",
            "bots/comment-sicko/SOUL.md", "bots/poteto-agent/SOUL.md",
        ])
        self.assertEqual(result["source_commit"], self.base)
        self.assertEqual(result["source_tree"], self.git("rev-parse", f"HEAD:{SOURCE}"))
        self.assertEqual(protocol.plan(self.repo, self.base), result)

    def test_noop_binds_checkpoint_and_immutable_target_trees(self):
        self.assertTrue(callable(getattr(protocol, "plan", None)),
                        "plan() is not implemented")
        result = protocol.plan(self.repo)
        self.assertEqual(result, {
            "schema": 1,
            "base_commit": self.base,
            "base_source_commit": self.upstream,
            "base_source_tree": self.source_tree,
            "source_commit": self.base,
            "source_tree": self.source_tree,
            "adaptation_tree": self.git("rev-parse", f"{self.base}:{ADAPTED}"),
            "changed_paths": [], "allowed_paths": [],
            "noop": True, "blocked_reasons": [],
        })
        self.put(f"{SOURCE}/alpha/SKILL.md", "uncommitted attack\n")
        self.assertEqual(protocol.plan(self.repo), result)


if __name__ == "__main__":
    unittest.main()

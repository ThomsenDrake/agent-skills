"""Pinned, data-only boundary between an untrusted writer and a publisher.

No model output is executed. Paths in plans and updates are package-relative.
The caller must run its independent policy/tests/review before calling apply().
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess


SOURCE = "skills/pstack"
ADAPTED = "skills/pstack-hermes"
MANIFEST = "UPSTREAM.json"
MAX_FILE_BYTES = 512 * 1024
MAX_UPDATE_BYTES = 2 * 1024 * 1024
MAX_UPDATES = 64
MAX_SNAPSHOT_BYTES = 32 * 1024 * 1024
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")


def _git(repo: Path, *args: str) -> bytes:
    # Do not inherit alternate repositories, object stores or injected git config.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_OPTIONAL_LOCKS="0", GIT_NO_REPLACE_OBJECTS="1")
    try:
        return subprocess.run(
            ["git", "--no-replace-objects", "-c", "core.fsmonitor=false",
             "-C", str(repo), *args], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=30,
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("git rejected the pinned repository state") from exc


def _sha(value: object) -> str:
    if not isinstance(value, str) or not _HEX40.fullmatch(value):
        raise ValueError("expected a lowercase 40-hex object ID")
    return value


def _commit(repo: Path, value: str) -> str:
    if value != "HEAD":
        _sha(value)
    result = _sha(_git(repo, "rev-parse", "--verify", f"{value}^{{commit}}").decode().strip())
    if value != "HEAD" and result != value:
        raise ValueError("object ID is not a commit")
    return result


def _tree(repo: Path, commit: str, directory: str) -> str:
    oid = _sha(_git(repo, "rev-parse", "--verify", f"{commit}:{directory}").decode().strip())
    if _git(repo, "cat-file", "-t", oid) != b"tree\n":
        raise ValueError("package is not a git tree")
    return oid


def _entries(repo: Path, tree: str) -> dict:
    entries = {}
    for record in _git(repo, "ls-tree", "-r", "-z", tree).split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        relative = _path(path.decode("utf-8"))
        if relative in entries or len(entries) >= 4096:
            raise ValueError("duplicate/excessive git tree paths")
        entries[relative] = (mode, kind, _sha(oid))
    return entries


def _counterpart(path: str) -> str:
    return {
        "agents/poteto-agent.md": "bots/poteto-agent/SOUL.md",
        "agents/comment-sicko.md": "bots/comment-sicko/SOUL.md",
    }.get(path, path)


def _writable_markdown(path: str) -> bool:
    _path(path)
    return (path.endswith(".md")
            and path.split("/")[0] not in {"automation", "tests"}
            and path != "references/verification.md"
            and not path.startswith("references/smoke/"))


def _unique_json(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate checkpoint key")
        result[key] = value
    return result


def plan(repo: Path, commit: str = "HEAD") -> dict:
    """Compare immutable source trees against the controller's checkpoint."""
    base = _commit(repo, commit)
    adapted_tree = _tree(repo, base, ADAPTED)
    adapted = _entries(repo, adapted_tree)
    if MANIFEST not in adapted or adapted[MANIFEST][:2] != ("100644", "blob"):
        raise ValueError("checkpoint must be a regular nonexecutable blob")
    manifest = json.loads(_text(_blob(repo, adapted[MANIFEST][2])), object_pairs_hook=_unique_json)
    if (type(manifest) is not dict
            or set(manifest) != {"schema", "source_commit", "source_tree"}
            or type(manifest["schema"]) is not int or manifest["schema"] != 1):
        raise ValueError("invalid schema-1 checkpoint")
    old_commit = _commit(repo, _sha(manifest["source_commit"]))
    _git(repo, "merge-base", "--is-ancestor", old_commit, base)
    old_tree = _tree(repo, old_commit, SOURCE)
    if old_tree != _sha(manifest["source_tree"]):
        raise ValueError("checkpoint source tree does not match its commit")
    source_tree = _tree(repo, base, SOURCE)
    old_files, new_files = _entries(repo, old_tree), _entries(repo, source_tree)
    changed = sorted(path for path in old_files.keys() | new_files.keys()
                     if old_files.get(path) != new_files.get(path))
    allowed = {_counterpart(path) for path in changed} | {"SKILL.md"} if changed else set()
    reasons = []
    old_leaves = {path.split("/")[0] for path in old_files
                  if path.count("/") == 1 and path.endswith("/SKILL.md")}
    new_leaves = {path.split("/")[0] for path in new_files
                  if path.count("/") == 1 and path.endswith("/SKILL.md")}
    if old_leaves != new_leaves:
        reasons.append("manual review required: source skill leaf set changed")
    for label, files in (("old source", old_files), ("new source", new_files), ("adaptation", adapted)):
        for relative, (mode, kind, oid) in files.items():
            if kind != "blob" or mode not in {"100644", "100755"}:
                reasons.append(f"manual review required: nonregular {label} path {relative}")
    for path in changed:
        before, after = old_files.get(path), new_files.get(path)
        if before is None or after is None:
            reasons.append(f"manual review required: added/deleted/renamed source path {path}")
        elif (before[:2] != ("100644", "blob")
              or after[:2] != ("100644", "blob")):
            reasons.append(f"manual review required: source mode/type/executable change {path}")
        elif not path.endswith(".md"):
            reasons.append(f"manual review required: non-Markdown source change {path}")
        elif (path != "SKILL.md" and path not in {
                "agents/poteto-agent.md", "agents/comment-sicko.md"}
              and path.split("/")[0] not in old_leaves):
            reasons.append(f"manual review required: source path has no owned skill leaf {path}")
        else:
            try:
                _text(_blob(repo, before[2]))
                _text(_blob(repo, after[2]))
            except ValueError as exc:
                reasons.append(f"manual review required: invalid source text {path}: {exc}")
    for path in allowed:
        if (not _writable_markdown(path) or path not in adapted
                or adapted[path][:2] != ("100644", "blob")):
            reasons.append(f"manual review required: no regular Markdown counterpart {path}")
    return {
        "schema": 1, "base_commit": base,
        "base_source_commit": old_commit, "base_source_tree": old_tree,
        "source_commit": base, "source_tree": source_tree,
        "adaptation_tree": adapted_tree,
        "changed_paths": changed, "allowed_paths": [] if reasons else sorted(allowed),
        "noop": source_tree == old_tree, "blocked_reasons": sorted(reasons),
    }


def _blob(repo: Path, oid: str) -> bytes:
    _sha(oid)
    if int(_git(repo, "cat-file", "-s", oid)) > MAX_FILE_BYTES:
        raise ValueError("git blob exceeds 512 KiB limit")
    return _git(repo, "cat-file", "blob", oid)


def _snapshot(repo: Path, tree: str) -> dict:
    files, total = {}, 0
    for path, (mode, kind, oid) in _entries(repo, tree).items():
        _path(path)
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"nonregular git snapshot path: {path}")
        data = _blob(repo, oid)
        _text(data)
        total += len(data)
        if total > MAX_SNAPSHOT_BYTES or len(files) >= 4096:
            raise ValueError("git snapshot exceeds resource limits")
        files[path] = mode, data
    return files


def _checked_plan(repo: Path, supplied: dict) -> dict:
    if type(supplied) is not dict or "base_commit" not in supplied:
        raise ValueError("invalid plan")
    expected = plan(repo, _sha(supplied["base_commit"]))
    try:
        same = json.dumps(supplied, sort_keys=True) == json.dumps(expected, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError("plan must be JSON data") from exc
    if not same:
        raise ValueError("plan differs from pinned repository policy")
    if expected["noop"] or expected["blocked_reasons"]:
        raise ValueError("noop or blocked plan cannot be processed")
    return expected


def materialize(repo: Path, plan: dict, dest: Path) -> None:
    """Copy immutable blobs, never a worktree, into four isolated snapshots.

    The full tracked package, including protected files, is copied consistently.
    Only the candidate is writer-writable; collect() rejects protected changes.
    """
    plan = _checked_plan(repo, plan)
    snapshots = {
        "old-upstream": _snapshot(repo, plan["base_source_tree"]),
        "new-upstream": _snapshot(repo, plan["source_tree"]),
        "current-hermes": _snapshot(repo, plan["adaptation_tree"]),
    }
    snapshots["candidate"] = snapshots["current-hermes"]
    dest = Path(dest).absolute()
    if dest.is_relative_to(Path(repo).resolve()):
        raise ValueError("snapshots must be outside the repository")
    with _directory(dest, create=True) as root:
        if os.listdir(root):
            raise ValueError("snapshot destination must be empty")
        for name, files in snapshots.items():
            os.mkdir(name, 0o755, dir_fd=root)
            with _descend(root, [name]) as directory:
                for relative, (mode, data) in files.items():
                    parts = _path(relative).split("/")
                    with _descend(directory, parts[:-1], create=True) as parent:
                        fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o600, dir_fd=parent)
                        with os.fdopen(fd, "wb") as stream:
                            os.fchmod(stream.fileno(), 0o755 if mode == "100755" else 0o644)
                            stream.write(data)


_BINDINGS = ("schema", "base_commit", "base_source_commit", "base_source_tree",
             "source_commit", "source_tree", "adaptation_tree")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _path(value: object) -> str:
    if (not isinstance(value, str) or not value or len(value) > 512
            or len(value.split("/")) > 16):
        raise ValueError("invalid package-relative path")
    for part in value.split("/"):
        if (len(part) > 128 or part in {".", ".."}
                or part.casefold() == ".git"
                or not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9._-]*|\.gitignore", part)):
            raise ValueError(f"unsafe package-relative path: {value!r}")
    return value


def _text(data: bytes) -> str:
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("file exceeds 512 KiB limit")
    text = data.decode("utf-8")
    if any(ord(char) < 32 and char not in "\t\n\r" or ord(char) == 127 for char in text):
        raise ValueError("binary/control bytes in text file")
    return text


@contextmanager
def _descend(root: int, parts: list[str], create: bool = False):
    fd = os.dup(root)
    try:
        for part in parts:
            if part in {"", ".", ".."}:
                raise ValueError("unsafe filesystem directory")
            if create:
                try:
                    os.mkdir(part, 0o755, dir_fd=fd)
                except FileExistsError:
                    pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


@contextmanager
def _directory(path: Path, create: bool = False):
    parts = list(Path(path).absolute().parts)
    root = os.open(parts[0], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        with _descend(root, parts[1:], create) as fd:
            yield fd
    finally:
        os.close(root)


def _read_file(directory: int, name: str) -> tuple[int, bytes]:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("file must be regular and not hardlinked")
        if info.st_size > MAX_FILE_BYTES:
            raise ValueError("file exceeds 512 KiB limit")
        data = stream.read(MAX_FILE_BYTES + 1)
        _text(data)
        after = os.fstat(stream.fileno())
        if (info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
                after.st_mode, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("file changed while being read")
        return stat.S_IMODE(info.st_mode), data


def _candidate_files(directory: Path, expected: dict) -> dict:
    directories = {path.rsplit("/", index)[0] for path in expected
                   for index in range(1, path.count("/") + 1)}
    found, total = {}, 0

    def walk(fd: int, prefix: str = "") -> None:
        nonlocal total
        with os.scandir(fd) as children:
            for entry in children:
                relative = _path(prefix + entry.name)
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    if relative not in directories:
                        raise ValueError(f"extra candidate directory: {relative}")
                    with _descend(fd, [entry.name]) as child:
                        walk(child, relative + "/")
                elif stat.S_ISREG(info.st_mode) and relative in expected:
                    mode, data = _read_file(fd, entry.name)
                    total += len(data)
                    if total > MAX_SNAPSHOT_BYTES + MAX_UPDATE_BYTES:
                        raise ValueError("candidate exceeds snapshot byte budget")
                    expected_mode = 0o755 if expected[relative][0] == "100755" else 0o644
                    if mode != expected_mode:
                        raise ValueError(f"candidate mode changed: {relative}")
                    found[relative] = data
                else:
                    raise ValueError(f"extra/nonregular candidate path: {relative}")

    with _directory(directory) as fd:
        walk(fd)
    if set(found) != set(expected):
        raise ValueError("candidate is missing tracked paths")
    return found


def collect(repo: Path, plan: dict, candidate_dir: Path) -> dict:
    """Reduce an untrusted candidate to content-and-hash data, not a patch."""
    plan = _checked_plan(repo, plan)
    expected = _snapshot(repo, plan["adaptation_tree"])
    actual = _candidate_files(Path(candidate_dir), expected)
    updates, total = [], 0
    for relative, (mode, before) in sorted(expected.items()):
        data = actual[relative]
        if data != before:
            if relative not in plan["allowed_paths"]:
                raise ValueError(f"candidate modified protected/unmapped path: {relative}")
            total += len(data)
            if total > MAX_UPDATE_BYTES or len(updates) >= MAX_UPDATES:
                raise ValueError("candidate exceeds 64 updates / 2 MiB changed-byte budget")
            updates.append({"path": relative, "before_sha256": _digest(before),
                            "content": data.decode("utf-8"), "after_sha256": _digest(data)})
    return {**{key: plan[key] for key in _BINDINGS}, "updates": updates}


def _validated_envelope(repo: Path, envelope: dict) -> tuple[dict, list[tuple[str, bytes]]]:
    if (type(envelope) is not dict or set(envelope) != {*_BINDINGS, "updates"}
            or type(envelope.get("schema")) is not int or envelope["schema"] != 1):
        raise ValueError("invalid schema-1 publication envelope")
    for key in _BINDINGS[1:]:
        _sha(envelope[key])
    expected = plan(repo, envelope["base_commit"])
    if expected["noop"] or expected["blocked_reasons"]:
        raise ValueError("cannot publish a noop or blocked plan")
    if any(envelope[key] != expected[key] for key in _BINDINGS):
        raise ValueError("publication source/base/tree binding mismatch")
    updates = envelope["updates"]
    if type(updates) is not list or len(updates) > MAX_UPDATES:
        raise ValueError("invalid or excessive updates")
    trusted = _snapshot(repo, expected["adaptation_tree"])
    seen, verified, total = set(), [], 0
    for update in updates:
        if (type(update) is not dict or set(update) != {
                "path", "before_sha256", "content", "after_sha256"}):
            raise ValueError("invalid update shape")
        relative = _path(update["path"])
        if relative in seen or relative not in expected["allowed_paths"]:
            raise ValueError("duplicate or disallowed update path")
        seen.add(relative)
        if type(update["content"]) is not str or len(update["content"]) > MAX_FILE_BYTES:
            raise ValueError("update content must be UTF-8 text")
        data = update["content"].encode("utf-8")
        _text(data)
        total += len(data)
        if total > MAX_UPDATE_BYTES:
            raise ValueError("publication exceeds 2 MiB changed-byte budget")
        for key in ("before_sha256", "after_sha256"):
            if type(update[key]) is not str or not re.fullmatch(r"[0-9a-f]{64}", update[key]):
                raise ValueError("invalid SHA-256 digest")
        before = trusted[relative][1]
        if update["before_sha256"] != _digest(before) or update["after_sha256"] != _digest(data):
            raise ValueError("before/after digest mismatch")
        if data == before:
            raise ValueError("update does not change content")
        verified.append((relative, data))
    return expected, verified


def _clean_publication_tree(repo: Path, expected: dict) -> None:
    if _commit(repo, "HEAD") != expected["base_commit"]:
        raise ValueError("stale publication base: HEAD moved")
    if _git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", SOURCE, ADAPTED):
        raise ValueError("source/adaptation worktree or index is dirty")
    # Explicit byte checks also catch assume-unchanged/skip-worktree index flags.
    for package, tree in ((SOURCE, expected["source_tree"]),
                          (ADAPTED, expected["adaptation_tree"])):
        with _directory(Path(repo) / package) as root:
            for relative, (mode, before) in _snapshot(repo, tree).items():
                parts = relative.split("/")
                with _descend(root, parts[:-1]) as parent:
                    actual_mode, data = _read_file(parent, parts[-1])
                if actual_mode != (0o755 if mode == "100755" else 0o644) or data != before:
                    raise ValueError(f"dirty publication path: {package}/{relative}")
    if _commit(repo, "HEAD") != expected["base_commit"]:
        raise ValueError("HEAD moved during publication validation")


def _atomic_write(root: int, relative: str, data: bytes, before: bytes, mode: int) -> None:
    parts = _path(relative).split("/")
    with _descend(root, parts[:-1]) as parent:
        actual_mode, actual = _read_file(parent, parts[-1])
        if actual != before or actual_mode != mode:
            raise ValueError("publication target changed before write")
        temporary = ".pstack-update-" + secrets.token_hex(12)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                os.fchmod(stream.fileno(), mode)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            # Replace the directory entry; never write through a raced symlink.
            os.replace(temporary, parts[-1], src_dir_fd=parent, dst_dir_fd=parent)
            os.fsync(parent)
        finally:
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass


def apply(repo: Path, envelope: dict) -> None:
    """Publish reviewed data without staging, committing or touching source.

    This is a publication primitive, not an authorization/review decision.
    """
    expected, updates = _validated_envelope(repo, envelope)
    _clean_publication_tree(repo, expected)
    trusted = _snapshot(repo, expected["adaptation_tree"])
    checkpoint = {"schema": 1, "source_commit": expected["source_commit"],
                  "source_tree": expected["source_tree"]}
    with _directory(Path(repo) / ADAPTED) as root:
        for relative, data in updates:
            _atomic_write(root, relative, data, trusted[relative][1], 0o644)
        # Controller-owned checkpoint is always last, including empty updates.
        data = (json.dumps(checkpoint, indent=2) + "\n").encode("utf-8")
        _atomic_write(root, MANIFEST, data, trusted[MANIFEST][1], 0o644)

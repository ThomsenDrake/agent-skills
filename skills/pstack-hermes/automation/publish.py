"""Least-privileged, single-PR publisher. No models or candidate code run here."""
from __future__ import annotations

from pathlib import Path
import json
import os
import re
import subprocess
import tempfile
from urllib.parse import quote, urlencode

import protocol


REPOSITORY = "ThomsenDrake/agent-skills"
BOT_BRANCH = "automation/pstack-hermes-update"
BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"


class PublicationError(ValueError):
    """Ownership, policy, Git or GitHub failure; do not continue publication."""


def _repository(value: str) -> str:
    if (not isinstance(value, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9._-]*", value)
            or value != REPOSITORY):
        raise PublicationError("repository must be the authorized owner/repo")
    return value


class GitHubNotFound(PublicationError):
    """Only an explicit HTTP 404 is treated as an absent branch."""


def gh(args: list[str], *, input: str | None = None):
    """Inject this JSON CLI boundary in tests; never inspect credential values."""
    try:
        result = subprocess.run(["gh", *args], input=input, text=True,
                                capture_output=True, timeout=60, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as exc:
        if re.search(r"\(HTTP 404\)", exc.stderr or ""):
            raise GitHubNotFound("GitHub target does not exist") from exc
        raise PublicationError("GitHub request failed") from exc
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise PublicationError("GitHub request failed or returned invalid JSON") from exc


def _api(runner, repository: str, suffix: str = "", *, method="GET", data=None):
    args = ["api", "--hostname", "github.com", "--method", method,
            f"repos/{repository}{suffix}"]
    payload = None
    if data is not None:
        args += ["--input", "-"]
        payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return runner(args, input=payload)


def _sha(value) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise PublicationError("invalid commit/tree object ID")
    return value


def _branch_head(runner, repository: str, branch: str) -> str | None:
    try:
        result = _api(runner, repository, "/git/ref/heads/" + quote(branch, safe=""))
    except GitHubNotFound:
        return None
    if (type(result) is not dict or result.get("ref") != "refs/heads/" + branch
            or type(result.get("object")) is not dict
            or result["object"].get("type") != "commit"):
        raise PublicationError("invalid GitHub branch response")
    return _sha(result["object"].get("sha"))


_METADATA_FIELDS = {"schema", "repository", "base_commit", "source_commit",
                    "source_tree", "adaptation_tree", "result_tree"}
_TRAILER = "Pstack-Hermes-Publication: "
_COMMENT = "<!-- pstack-hermes-publication:"


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PublicationError("duplicate JSON metadata key")
        result[key] = value
    return result


def _metadata(text: str, *, comment=False) -> dict:
    pattern = (r"<!-- pstack-hermes-publication:(\{[^\n]*\}) -->" if comment
               else r"^Pstack-Hermes-Publication: (\{[^\n]*\})$")
    matches = re.findall(pattern, text, re.MULTILINE)
    if len(matches) != 1:
        raise PublicationError("missing or ambiguous bot publication metadata")
    try:
        result = json.loads(matches[0], object_pairs_hook=_unique_object)
    except (ValueError, TypeError) as exc:
        raise PublicationError("invalid bot publication metadata") from exc
    if (type(result) is not dict or set(result) != _METADATA_FIELDS
            or type(result["schema"]) is not int or result["schema"] != 1
            or result["repository"] != REPOSITORY):
        raise PublicationError("invalid bot publication metadata bindings")
    for key in _METADATA_FIELDS - {"schema", "repository"}:
        _sha(result[key])
    if result["source_commit"] != result["base_commit"]:
        raise PublicationError("bot source commit differs from its pinned base")
    return result


def _remote_tree(runner, repository: str, tree: str) -> dict:
    result = _api(runner, repository, "/git/trees/" + _sha(tree))
    if (type(result) is not dict or result.get("sha") != tree
            or result.get("truncated") is not False or type(result.get("tree")) is not list):
        raise PublicationError("invalid or truncated GitHub source/basis tree response")
    return result


def _subtree(tree: dict, name: str) -> str:
    entries = [item for item in tree["tree"] if type(item) is dict and item.get("path") == name]
    if len(entries) != 1 or entries[0].get("type") != "tree" or entries[0].get("mode") != "040000":
        raise PublicationError("missing/non-tree source or adaptation basis")
    return _sha(entries[0].get("sha"))


def _check_remote_basis(runner, repository: str, metadata: dict) -> None:
    base = _api(runner, repository, "/commits/" + metadata["base_commit"])
    try:
        if base["sha"] != metadata["base_commit"]:
            raise PublicationError("GitHub returned a different source/basis commit")
        root = _remote_tree(runner, repository, base["commit"]["tree"]["sha"])
        skills = _remote_tree(runner, repository, _subtree(root, "skills"))
        if (_subtree(skills, "pstack") != metadata["source_tree"]
                or _subtree(skills, "pstack-hermes") != metadata["adaptation_tree"]):
            raise PublicationError("bot metadata source/basis does not match its pinned commit")
    except (KeyError, TypeError) as exc:
        raise PublicationError("invalid GitHub source/basis commit response") from exc


def _head_metadata(runner, repository: str, head: str, *, expected_parents: list[str] | None = None) -> dict:
    result = _api(runner, repository, "/commits/" + head)
    try:
        commit = result["commit"]
        if (result["sha"] != head or result["author"]["login"] != BOT_NAME
                or result["committer"]["login"] != BOT_NAME
                or any(commit[role]["name"] != BOT_NAME or commit[role]["email"] != BOT_EMAIL
                       for role in ("author", "committer"))):
            raise PublicationError("bot branch has an untrusted commit identity")
        metadata = _metadata(commit["message"])
        parents = [_sha(parent["sha"]) for parent in result["parents"]]
        if (len(parents) not in {1, 2} or metadata["base_commit"] not in parents
                or commit["tree"]["sha"] != metadata["result_tree"]
                or (expected_parents is not None and parents != expected_parents)):
            raise PublicationError("bot commit tree/parents do not match its publication metadata")
    except (KeyError, TypeError) as exc:
        raise PublicationError("invalid GitHub bot commit response") from exc
    _check_remote_basis(runner, repository, metadata)
    return metadata


def _pulls(runner, repository: str, base: str) -> list[dict]:
    result = []
    for page in range(1, 101):
        query = urlencode({"state": "all", "head": repository.split("/")[0] + ":" + BOT_BRANCH,
                           "base": base, "per_page": 100, "page": page})
        values = _api(runner, repository, "/pulls?" + query)
        if type(values) is not list or len(values) > 100:
            raise PublicationError("invalid GitHub pull request list")
        for pr in values:
            if (type(pr) is not dict or pr.get("head", {}).get("ref") != BOT_BRANCH
                    or pr.get("base", {}).get("ref") != base):
                raise PublicationError("pull request query returned an unexpected target")
        result.extend(values)
        if len(values) < 100:
            return result
    raise PublicationError("pull request history exceeds the safe pagination bound")


def _check_pr(pr: dict, repository: str, base: str, head: str | None) -> None:
    try:
        number = pr["number"]
        if (head is None or type(number) is not int or number < 1 or pr["state"] != "open"
                or pr.get("merged_at") is not None or pr["user"]["login"] != BOT_NAME
                or pr["head"]["ref"] != BOT_BRANCH or pr["head"]["sha"] != head
                or pr["head"]["repo"]["full_name"] != repository
                or pr["base"]["ref"] != base or pr["base"]["repo"]["full_name"] != repository
                or pr["html_url"] != f"https://github.com/{repository}/pull/{number}"):
            raise PublicationError("pull request ownership, target, state or head changed")
    except (KeyError, TypeError) as exc:
        raise PublicationError("invalid GitHub pull request response") from exc


def probe(repository: str, plan: dict, *, gh_runner=None) -> dict:
    """Read-only pre-model decision bound to both source and adaptation trees."""
    return _probe(repository, plan, gh_runner=gh_runner)


def _probe(repository: str, plan: dict, *, gh_runner=None, retry_probe: dict | None = None) -> dict:
    """Allow authenticated PR lag only inside publish's exact-artifact retry."""
    _repository(repository)
    runner = gh_runner or gh
    for key in ("base_commit", "source_tree", "adaptation_tree"):
        _sha(plan.get(key))
    info = _api(runner, repository)
    base = info.get("default_branch")
    if (info.get("full_name") != repository or type(base) is not str
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", base)):
        raise PublicationError("invalid default branch response")
    if _branch_head(runner, repository, base) != plan["base_commit"]:
        raise PublicationError("latest default branch moved from the pinned base")
    head = _branch_head(runner, repository, BOT_BRANCH)
    pulls = _pulls(runner, repository, base)
    opened = [pr for pr in pulls if pr.get("state") == "open"]
    if len(opened) > 1:
        raise PublicationError("multiple active bot-branch pull requests")
    metadata = _head_metadata(runner, repository, head) if head else None
    active = opened[0] if opened else None
    if active:
        _check_pr(active, repository, base, head)
        pr_metadata = _metadata(active["body"], comment=True)
        if metadata is None or pr_metadata != metadata:
            original = retry_probe.get("expected_bot_branch_head") if retry_probe else None
            if (retry_probe is None or head is None or original is None or original == head
                    or type(retry_probe.get("pr_number")) is not int
                    or retry_probe["pr_number"] != active["number"]
                    or pr_metadata != _head_metadata(runner, repository, _sha(original))):
                raise PublicationError("pull request metadata differs from the trusted branch head")
            _head_metadata(runner, repository, head,
                           expected_parents=[original, plan["base_commit"]])
            exact = _api(runner, repository, "/pulls/" + str(active["number"]))
            _check_pr(exact, repository, base, head)
            if (exact["number"] != active["number"]
                    or _metadata(exact["body"], comment=True) != pr_metadata):
                raise PublicationError("pull request changed during exact retry probe")
    blocked = [f"human-closed unmerged pull request #{pr['number']} blocks publication"
               for pr in pulls if pr.get("state") == "closed" and not pr.get("merged_at")]
    skip = bool(not blocked and active and metadata and _metadata(active["body"], comment=True) == metadata
                and all(metadata[key] == plan[key] for key in ("source_tree", "adaptation_tree")))
    return {
        "schema": 1, "repository": repository, "default_branch": base,
        **{key: plan[key] for key in ("base_commit", "source_tree", "adaptation_tree")},
        "expected_bot_branch_head": head, "pr_number": active["number"] if active else None,
        "skip": skip, "blocked_reasons": blocked,
    }


def git(repo: Path, *args: str, input: bytes | None = None, env: dict | None = None) -> bytes:
    """Git plumbing only; bypass hooks, ambient Git config and replacement objects."""
    clean = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    clean.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                 GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0")
    clean.update(env or {})
    try:
        return subprocess.run([
            "git", "--no-replace-objects", "-c", "core.hooksPath=" + os.devnull,
            "-c", "core.fsmonitor=false", "-C", str(repo), *args,
        ], input=input, env=clean, check=True, capture_output=True, timeout=120).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise PublicationError("Git rejected publication; no forced recovery is permitted") from exc


def _publication_tree(repo: Path, envelope: dict, runner) -> str:
    with tempfile.TemporaryDirectory(prefix="pstack-publish-", dir=os.environ["TMPDIR"]) as temp:
        env = {"GIT_INDEX_FILE": str(Path(temp) / "index")}
        runner(repo, "read-tree", envelope["base_commit"], env=env)
        # apply() has validated these exact bytes. Never re-read writer/worktree data.
        contents = {update["path"]: update["content"].encode("utf-8") for update in envelope["updates"]}
        contents[protocol.MANIFEST] = (json.dumps({
            "schema": 1, "source_commit": envelope["source_commit"], "source_tree": envelope["source_tree"],
        }, indent=2) + "\n").encode("utf-8")
        for relative, data in sorted(contents.items()):
            path = protocol.ADAPTED + "/" + relative
            oid = _sha(runner(repo, "hash-object", "-w", "--no-filters", "--stdin", input=data).decode().strip())
            runner(repo, "update-index", "--cacheinfo", "100644," + oid + "," + path, env=env)
        return _sha(runner(repo, "write-tree", env=env).decode().strip())


def _body(plan: dict, metadata: dict) -> str:
    paths = plan["changed_paths"]
    if len(paths) > 64:
        raise PublicationError("too many upstream paths for a bounded pull request body")
    listed = "\n".join("- `" + path + "`" for path in paths)
    return ("Data-only Hermes adaptation of upstream Markdown. Manual merge required.\n\n"
            + "Source commit: `" + plan["source_commit"] + "`\n\nChanged upstream paths:\n"
            + listed + "\n\n" + _COMMENT
            + json.dumps(metadata, sort_keys=True, separators=(",", ":")) + " -->\n")


def _verified_result(api, repository: str, base: str, head: str, number: int, status: str, metadata: dict) -> dict:
    if _branch_head(api, repository, BOT_BRANCH) != head:
        raise PublicationError("bot branch failed final head verification")
    verified = _api(api, repository, "/pulls/" + str(number))
    _check_pr(verified, repository, base, head)
    if verified["number"] != number:
        raise PublicationError("pull request number failed exact-target read-back verification")
    if _metadata(verified["body"], comment=True) != metadata:
        raise PublicationError("pull request metadata failed read-back verification")
    return {"status": status, "pr_number": number, "url": verified["html_url"],
            "head_sha": head, "branch": BOT_BRANCH}


def publish(repo: Path, envelope: dict, repository: str, *, expected_probe: dict | None = None,
            gh_runner=None, git_runner=None) -> dict:
    """Publish ONLY verifier-normalized data with its pre-model probe binding.

    Workflow callers must verify artifact/run/attempt provenance before this call.
    ``envelope`` is protocol.collect/apply schema 1; ``expected_probe`` is the
    earlier probe result, carried by the protected verifier (never by the writer).
    Injectable runners are trusted test dependencies, not artifact fields.
    """
    _repository(repository)
    repo = Path(repo)
    api, command = gh_runner or gh, git_runner or git
    if type(envelope) is not dict or type(expected_probe) is not dict:
        raise PublicationError("publication requires a verifier envelope and its original probe")
    # Even read-only `git status` can execute a local clean/process filter.
    # Inspect key names only (never values), before invoking protocol Git checks.
    keys = command(repo, "config", "--includes", "--null", "--name-only", "--list").decode().split("\0")
    if any(key.casefold().startswith("filter.") for key in keys):
        raise PublicationError("configured Git filters are forbidden in the publisher checkout")
    plan = protocol.plan(repo, _sha(envelope.get("base_commit")))
    current = _probe(repository, plan, gh_runner=api, retry_probe=expected_probe)
    drifted = current != expected_probe
    stable = set(current) - {"expected_bot_branch_head", "pr_number", "skip"}
    # A retry can observe its own completed push/PR. Permit no other drift,
    # and prove the exact reviewed result tree below before any remote write.
    if (current["blocked_reasons"] or expected_probe.get("blocked_reasons")
            or (drifted and (set(expected_probe) != set(current)
                or any(current[key] != expected_probe[key] for key in stable)
                or current["expected_bot_branch_head"] is None
                or expected_probe["pr_number"] not in (None, current["pr_number"])))):
        raise PublicationError("publication probe drifted or is blocked")
    origin = command(repo, "remote", "get-url", "--push", "--all", "origin").decode().removesuffix("\n")
    fetch_origin = command(repo, "remote", "get-url", "--all", "origin").decode().removesuffix("\n")
    if (origin not in {f"https://github.com/{repository}", f"https://github.com/{repository}.git"}
            or fetch_origin != origin):
        raise PublicationError("origin is not the authorized HTTPS repository")
    old = current["expected_bot_branch_head"]
    prior = {}
    if old:
        command(repo, "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential",
                "fetch", "--no-tags", "--no-write-fetch-head", "origin", old)
        prior = _head_metadata(api, repository, old)
        old_plan = protocol.plan(repo, prior["base_commit"])
        if (any(prior[key] != old_plan[key] for key in ("source_commit", "source_tree", "adaptation_tree"))
                or command(repo, "rev-parse", old + "^{tree}").decode().strip() != prior["result_tree"]):
            raise PublicationError("old bot branch source/basis/tree binding is invalid")
    protocol.apply(repo, envelope)
    if current["skip"] and not drifted:
        return _verified_result(api, repository, current["default_branch"], old,
                                current["pr_number"], "unchanged", prior)
    tree = _publication_tree(repo, envelope, command)
    if drifted:
        if (prior.get("result_tree") != tree or any(prior.get(key) != plan[key]
                for key in ("base_commit", "source_commit", "source_tree", "adaptation_tree"))):
            raise PublicationError("bot branch drift is not an exact retry of this verified artifact")
        if current["skip"]:
            return _verified_result(api, repository, current["default_branch"], old,
                                    current["pr_number"], "unchanged", prior)
    metadata = {"schema": 1, "repository": repository, "result_tree": tree,
                **{key: plan[key] for key in ("base_commit", "source_commit", "source_tree", "adaptation_tree")}}
    data = {"title": "chore(pstack-hermes): adapt upstream Markdown", "body": _body(plan, metadata)}
    if drifted or (old and current["pr_number"] is None and prior["result_tree"] == tree):
        head = old  # A previous attempt pushed the exact reviewed tree before the PR write.
    else:
        message = ("chore(pstack-hermes): adapt upstream Markdown\n\n" + _TRAILER
                   + json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n")
        identity = {"GIT_AUTHOR_NAME": BOT_NAME, "GIT_AUTHOR_EMAIL": BOT_EMAIL,
                    "GIT_COMMITTER_NAME": BOT_NAME, "GIT_COMMITTER_EMAIL": BOT_EMAIL}
        parents = ["-p", old, "-p", plan["base_commit"]] if old else ["-p", plan["base_commit"]]
        head = _sha(command(repo, "commit-tree", tree, *parents,
                            input=message.encode(), env=identity).decode().strip())
        if probe(repository, plan, gh_runner=api) != current:
            raise PublicationError("pull request/probe changed before publication")
        if _branch_head(api, repository, current["default_branch"]) != plan["base_commit"]:
            raise PublicationError("latest default branch moved before publication")
        if _branch_head(api, repository, BOT_BRANCH) != old:
            raise PublicationError("bot branch head moved since the original probe")
        if command(repo, "rev-parse", "HEAD").decode().strip() != plan["base_commit"]:
            raise PublicationError("local HEAD moved before publication")
        command(repo, "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential",
                "push", "origin", head + ":refs/heads/" + BOT_BRANCH)
        if _branch_head(api, repository, BOT_BRANCH) != head:
            raise PublicationError("pushed branch head failed read-back verification")
    if drifted and current["pr_number"] is not None:
        if _probe(repository, plan, gh_runner=api, retry_probe=expected_probe) != current:
            raise PublicationError("pull request/probe changed before exact retry publication")
        if command(repo, "rev-parse", "HEAD").decode().strip() != plan["base_commit"]:
            raise PublicationError("local HEAD moved before exact retry publication")
    if _branch_head(api, repository, current["default_branch"]) != plan["base_commit"]:
        raise PublicationError("latest default branch moved before pull request publication")
    if _branch_head(api, repository, BOT_BRANCH) != head:
        raise PublicationError("bot branch head moved before pull request publication")
    if current["pr_number"]:
        number = current["pr_number"]
        _api(api, repository, "/pulls/" + str(number), method="PATCH", data=data)
    else:
        created = _api(api, repository, "/pulls", method="POST", data={
            **data, "head": BOT_BRANCH, "base": current["default_branch"],
            "draft": False, "maintainer_can_modify": False,
        })
        number = created.get("number")
    if type(number) is not int or number < 1:
        raise PublicationError("GitHub did not return a valid pull request number")
    return _verified_result(api, repository, current["default_branch"], head, number, "published", metadata)

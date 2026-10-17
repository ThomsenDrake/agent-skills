# Code Archaeology (git + in-repo)

Load with `skill_view(name="why", file_path="references/sources/code-archaeology.md")`. Use `terminal` for git and `gh`, `read_file` for content, and `search_files` for repository searches. Investigate the assigned checkout without edits or commits; do not delegate again. Verify repository/history and authenticated PR access rather than assuming either is available. Return exact queries, inspected revisions, citations, and gaps.

## What this source contains

- Commit history (messages, dates, authors, diffs)
- PR descriptions, review comments, and discussion threads (via `gh`)
- Inline code comments, TODOs, FIXMEs, deprecation notes
- ADRs (architectural decision records) if the repo keeps them
- Tests, whose names and assertions often encode the edge cases that motivated a change
- Related files modified in the same commits (co-change signal)
- CHANGELOG entries and release notes in the repo
- Issue/ticket IDs in commit messages and PR bodies

This is tied directly to code, but is not automatically complete or authoritative about motivation. Squashed commits, shallow history, missing PR access, private discussions, and lost review context can leave gaps. Explicit author statements are stronger intent evidence than a plausible reading of the diff.

## How to search it

Expand the seed commit list:

```python
# History through renames
terminal(command="git log --follow --oneline -- <file>")

# Pickaxe: commits adding/removing exact text, or matching a patch pattern
terminal(command="git log -S '<exact_string_from_code>' -- <file>")
terminal(command="git log -G '<regex>' -- <file>")

# Last-touch attribution, one full commit, or a bounded history range
terminal(command="git blame -L <start>,<end> -- <file>")
terminal(command="git show <hash>")
terminal(command="git log <old>..<new> -p -- <file>")
```

Resolve placeholders against actual identifiers and shell-quote paths/strings. Paginate full commit and PR discussions rather than treating a truncated preview as complete evidence.

Look for out-of-band docs:

```python
# ADRs often live in docs/adr/ or similar
search_files(pattern="(?i)architecture.decision", path="<repo>", file_glob="*.md")

# TODOs and FIXMEs near the target
search_files(pattern="TODO|FIXME|HACK|XXX|NOTE", path="<target_file>", context=2)

# Related tests
search_files(pattern="<symbol>", path="<repo>", file_glob="*test*")
```

Read the matching files with `read_file`. Follow full PR bodies/reviews through authenticated `gh` via `terminal` when available; report denied access separately from no matching rationale.

# Poteto helper scripts

These are the retained upstream Bun, Node, and Bash helpers.
No helper needs the editor harness except the worktree audit described below.
Resolve the installed directory through `skill_view(name="poteto-mode")`.
Replace placeholders with quoted real paths in every `terminal` call.

## Supported helpers

| Helper | Runtime and purpose |
| --- | --- |
| `orch/orch.ts` | Bun. Durable local orchestration records, inbox, gates, and verification ledger. It does not launch Hermes workers. |
| `watch-pr/watch-pr` | Bun and authenticated `gh`. Read PR state, review threads, and checks. Its watch mode needs supported GitHub event commands. |
| `check-plan.mjs` | Node. Validate the exact multi-phase-plan checklist structure. It expects a plan filename, not a `--help` flag. |
| `bootstrap.ts` | Bun. Install locked dependencies for the CLIs on first use. Requires network access on a cold install. |
| `worktree-audit.sh` | Upstream editor-specific transcript lookup. Skip on Hermes. Use the Worktree cleanup playbook's git checks instead. |

The audit's editor transcript path and macOS file-age commands are not portable.
Its age or `safe` bucket is never evidence that a Hermes worktree is abandoned.
Do not run it as a cleanup gate. It is retained for source comparison only.

## Run

```python
terminal(command="bun install --frozen-lockfile", workdir="<skill-dir>/scripts")
terminal(command="bun run '<skill-dir>/scripts/orch/orch.ts' --help")
terminal(command="bun run '<skill-dir>/scripts/watch-pr/watch-pr' --help")
terminal(command="node '<skill-dir>/scripts/check-plan.mjs' '<plan.md>'")
terminal(command="bun run test", workdir="<skill-dir>/scripts")
terminal(command="bun run typecheck", workdir="<skill-dir>/scripts")
```

`orch` needs `--store <scratch-or-project-record-dir>` or `ORCH_STORE`.
Use a separate store and worktree for each program.
The PR watcher needs a repository and a PR number. Read its actual `--help` output.
The watcher is GitHub-only through `gh`; it has no Origin route. The orchestrator can use optional Origin for frontier discovery after installed-help and repository-resolution checks, and defaults to `gh`. Do not assume Origin exists or pass its state to the watcher as though it used that forge.
A helper report does not authorize a merge or any other external write.

## Verification limits

The unit tests use their own local fixtures and fake PR responses. They test helper behavior, not a live GitHub merge.
A passing helper suite is not proof that an application works or a PR is safe to land.
Record live integration evidence separately.

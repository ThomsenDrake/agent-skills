---
name: show-me-your-work
description: "Use when work needs an auditable decision trail."
compatibility: "Hermes file and terminal tools, current-session history, optional session_search and delegate_task; bash for scripts/log.sh."
---

# Show me your work

Keep one canonical log.

## The format

A single TSV file, one row per decision. Cells stay single-line. Evidence is a pointer, not prose.

Read `skill_view(name="show-me-your-work", file_path="references/decision-log-template.tsv")` and copy its header row to start a clean log. Columns:

- **ts.** ISO8601 timestamp.
- **phase.** The phase or workstream.
- **decision.** What was chosen or done, one line.
- **why.** The reason in plain words. If a principle drove it, say it plainly, not as a jargon tag.
- **evidence.** A link or path that proves it: commit SHA, PR number, `file:line`, or an artifact, trace, or screenshot path. Never a paragraph.
- **result.** The outcome or predicate state: `tests green`, `reverted`, `pixel-diff 0`, `INCONCLUSIVE`, `open`.

An example, plain-spoken so a reviewer reads it at a glance.

```
ts	phase	decision	why	evidence	result
2026-05-24T09:02:00Z	frame	counted the work first, about 100 components and roughly 75 hours	wanted to know the size before starting a long run	commit 3a9f1c2	found 5 things to sort out before starting
2026-05-24T09:40:00Z	harness	took screenshots of the old version before changing anything	so we can compare old against new and catch any visual change	scripts/snapshot.sh, baseline/	saved 120 reference screenshots
2026-05-24T11:15:00Z	widget	moved the widget styles over without changing how it looks	keep the change small and the result identical	commit 7c21e0a, pixel-diff 0	looks identical, tests pass
2026-05-24T12:30:00Z	widget	threw out a helper's work because its screenshots were blank	checked the real files instead of trusting its summary	worktree reset	reverted, tightened the instructions for next time
```

## Logging a row

Write each entry the way you'd tell a teammate what you did. Plain words, concrete actions, no AI speak or abstract jargon (the **unslop** skill applies to log text too).

Load `skill_view(name="show-me-your-work", file_path="scripts/log.sh")` to locate the shipped helper. Invoke it with `terminal(command="bash <resolved-skill-dir>/scripts/log.sh <logfile> <phase> <decision> <why> <evidence> <result>")`, shell-quoting every argument. Never guess a harness plugin path. It stamps `ts`, writes the header on first use, strips stray tabs/newlines, and prefixes any cell starting with `=`, `+`, `-`, or `@` with a single quote. If bash is unavailable, use an equivalent safe writer that enforces six columns, single-line cells, and the same spreadsheet-formula escaping.

Log decision points and checkpoints, not every action: a fork chosen, a unit completed with its verification result, a pivot or revert with its trigger, a blocker surfaced, a gate fixed. For loop runs, one row per iteration. Skip the trivial and self-evident.

A run is one agent conversation, including its later turns and any summary of it. A pickup, a replacement agent, or a new chat starts a new run. When a run adds to a log that already has rows, its first row has phase `start`, and so does its first row after another run's `start` row. So a run that comes back to a log in a later turn first reads the log's last rows to see whether another run wrote since. A `start` row names the `ts` range of the rows before it that this run did not write, and its evidence names this run, such as its agent id. Use phase `start` for nothing else.

## Where it lives

By default the log is a working artifact, not committed. Keep it at `decisions.tsv` in the work dir, or `.audit/<task-slug>.tsv` when several efforts run at once, and leave it out of git. Assign one writer per log; delegates report decisions to the coordinator rather than racing appends.

Commit it only when the work is ambitious enough that a reviewer needs the trail to trust the result.

## Rules

- Append-only. A wrong call gets a new row that supersedes it. Never edit or delete history.
- Prefer evidence produced by committed scripts over hand-made one-offs (`skill_view(name="principle-encode-lessons-in-structure")`).

## Audit the log against the transcript

At the end of the run, before handing back, check the log told the truth. Use this conversation's real tool results and visible history first. If more is needed, use the enabled `session_search` tool with this exact session ID and tool roles, or export only this session with `terminal(command="hermes -p <profile> sessions export --session-id <id> --format jsonl --redact <scratch>/run.jsonl")`, then `read_file` on that export. Resolve the selected profile before exporting. Do not scan other profiles or unrelated sessions. A compacted summary is not a full tool trace; label any unobservable interval unaudited. Walk this run's rows against what actually happened. Each stretch of them begins at one of this run's `start` rows, or at the first row if this run created the log, and ends at the next `start` row of another run:

- Check that every row maps to a real decision or action.
- Check that each row's evidence resolves and shows what the row claims.
- A fork, pivot, or abandoned approach that shaped the work but isn't logged is a gap. Add it.

Correct the log, not the story. The audit never edits or removes a row, even an invented one. When a row records neither a real decision nor a real action, or its claim or evidence is wrong, add a row that supersedes it with what actually happened and a pointer that resolves. This audit does not check rows outside this run's stretches. If this run's own work shows one of them is wrong, supersede it like any wrong call.

## Independent review of the trail

**One-shot launch gate.** Before any profile-process launch here, load `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`. `-z` bypasses command and hook approval gates. Require explicit authorization for that bypass, review inherited hooks, and verify restricted execution boundaries, scoped credentials, and minimal toolsets. Model-diversity or unattended-work requests are not bypass authorization. Otherwise use bounded parent-driven delegates, an approval-preserving interactive session, or report blocked.

Before handing back, call `delegate_task(tasks=[{"goal": "Audit the decision trail without redoing the work", "context": "<canonical log path, this run's session ID or scoped redacted export, owned row ranges, and checks below>"}])`. The reviewer inherits the parent model; fresh context is not cross-model review. Give it only in-scope evidence. If delegation is unavailable, do a manual audit and label independent review unavailable. If actual model diversity is required, use separately configured named profiles and verify which provider/model ran; no per-call delegate model knobs.

- Decisions logged with weak or absent evidence.
- Verification steps skipped or claimed without proof in the transcript.
- Choices that look risky in hindsight (premature, scope-creeping, papering over a symptom).
- Gaps the user would otherwise miss on a casual skim.

Every reply for a run that produced a trail ends with an "Attention" section. State `reviewed by independent same-model delegate`, `reviewed by <verified profile/model>`, or `independent review unavailable`, then list each flag pointing to specific rows or moments. Do not invent a model identity. "No flags" is valid only after an actual review.

## Reviewing the trail

Read top to bottom, follow the evidence pointers, spot-check. GitHub renders a committed TSV as a table. Use `read_file` to inspect it, or run `column` through `terminal` when available.

## Composing this skill

Other skills route their audit trail here instead of inventing one. Reference it by name and let it own the format. Don't restate the columns.

## Verification

Every row in this run's ranges maps to an observed decision or action and a resolvable evidence pointer. Supersede false rows without deleting history, retain an honest unaudited marker for missing history, and include the reviewer's actual flags or the lack of independent review.

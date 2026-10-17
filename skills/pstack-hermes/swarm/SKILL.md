---
name: swarm
description: "Use when parallel workers need one verified report."
compatibility: "Requires Hermes delegation and file tools; terminal and git for revision-based verification."
---

# Swarm

Fan out bounded workers for coverage, exploration, measurements, or races, then return one verified report. Load `arena` when competing complete artifacts need base selection and grafting rather than coverage aggregation.

Keep a checklist: Frame, Fan out, Aggregate, Report.

## Phase A: Frame

**One-shot launch gate.** Before any profile-process launch here, load `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`. `-z` bypasses command and hook approval gates. Require explicit authorization for that bypass, review inherited hooks, and verify restricted execution boundaries, scoped credentials, and minimal toolsets. Model-diversity or unattended-work requests are not bypass authorization. Otherwise use bounded parent-driven delegates, an approval-preserving interactive session, or report blocked.

1. State the falsifiable done predicate and the artifact or report the swarm must return.
2. Choose coverage slices, identical-brief races, or a mix. For races declare `first pass`, `rank all`, or `best-of` before dispatch. Define pass independently of a worker's claim. `First pass` selects the first eligible completion the parent independently verifies. If the runtime delivers only a consolidated batch without reliable completion order, declare a deterministic tie-break in advance instead of inventing a finish-time winner. Do not assume other in-flight work was canceled.
3. Use the parent model by default, with different scopes or directions. Children inherit it unless global delegation settings override it. This is not cross-model evidence. `delegate_task` has no per-call model selection; model aliases do not change that. If a model race is genuinely required, load `arena` for its optional named-profile process protocol, use only profiles configured by `setup-pstack`, and verify actual models before labeling arms as different models.
4. Give each writer its own worktree or disjoint writable output under `$TMPDIR` or runtime scratch. Branches in one checkout are not filesystem isolation. Verify paths and starting revisions before launch, and forbid cross-worker or unrelated writes.
5. Revision-based verification briefs name exact SHAs. Measurement briefs also specify sample count, what one sample is, run order, environment controls, and units. Workers must record these in their results. Do not compare samples from mismatched commits or methods.
6. Put the complete goal, scope, slice/race arm, working path, required inputs, allowed writes, verification method, and result format into each context. Children have no access to the parent's conversation history. Confirm required tools and external read access are available; never invent a remote execution environment.

Completion: every required slice has an owner and a concrete acceptance check.

## Phase B: Fan out

Dispatch independent work together using real Hermes delegation:

```python
delegate_task(tasks=[
    {"goal": "Verify coverage slice A", "context": "<complete brief, exact SHAs, working/output paths, check method>"},
    {"goal": "Verify coverage slice B", "context": "<complete brief, exact SHAs, working/output paths, check method>"},
])
```

Respect tool-reported concurrency limits, splitting into bounded batches when needed. No child is asked to delegate recursively. A fresh conversation does not imply a private filesystem or an enforced no-write mode.

Workers report `PASS`, `ISSUES`, or `BLOCKED`, with evidence locations, actual commands/checks, exit codes, files changed, revision/method details when required, and all provable issues rather than just the first. Require bounded commands to finish before the worker's final report. A pending process is not a passing check.

When dispatch is asynchronous, finish independent work and yield for completion messages between parent turns. Do not poll child transcripts or read partial outputs to infer completion. Finite one-shot sessions may return joined results; inspect what actually arrived. A child does not survive its owning process exiting.

A failed worker is a visible dropout, not a passing slice. Continue where useful, but keep the coverage gap open.

## Phase C: Aggregate

Read every completion and inspect referenced artifacts with `read_file`, `search_files`, and relevant `terminal` checks. Child reports are self-reports. The parent verifies candidate paths/diffs and checks representative evidence, rerunning decisive acceptance checks rather than trusting a `PASS` label. Read back any authorized external side effects from the exact target.

Reject a result missing the exact SHAs or measurement method its brief required. Re-dispatch that slice once with the missing contract made explicit. A second miss is a recorded gap, never a pass. A sample-order or revision mismatch invalidates the comparison, not merely its formatting.

Coverage requires a valid result for every required slice. For races, apply only the predeclared selection rule and its evidence standard. Do not infer finish order from task-index ordering in a batch response. Same-model agreement is correlated opinion, not cross-model validation. Do not paste raw worker dumps.

## Phase D: Report and verify

Return one consolidated report: slice/arm table, verdicts and evidence, issue one-liners, verified revision/method details, gaps/dropouts, and the race rule if used. State what the parent independently checked and which conclusions remain unverified.

The swarm is complete only when the done predicate is checked and every slice is accounted for. If delegation is unavailable, perform a disclosed sequential pass or report a blocker; do not fabricate workers or their results.

---
name: arena
description: "Use when comparing competing artifact candidates."
compatibility: "Requires Hermes delegation and file tools; git for worktrees, terminal for optional configured profiles."
---

# Arena

Generate multiple candidates, choose a base, and graft the best compatible ideas from the others. Use when a single attempt would prematurely settle a non-trivial artifact. For partitioned coverage rather than competing artifacts, load `swarm`.

Keep a checklist: Frame, Fan out, Cross-judge, Pick, Graft, Verify.

## Hermes delegation contract

Use `delegate_task(tasks=[{"goal": "...", "context": "..."}, ...])`. Each child has an isolated conversation, not a private filesystem by default. Every brief must stand alone: task, shared grounding, assigned direction, allowed reads and writes, exact working/output paths, verification method, and reporting contract.

Children inherit the parent model unless global delegation settings override it. Do not pass a model or harness-specific mode to the tool. Default to same-model candidates with distinct design directions and a fresh-context judge with a separate role. This is not cross-model evidence. Aliases do not retarget `delegate_task`.

The parent owns every stage; do not ask a candidate or judge to delegate again. In sessions with background delivery, a dispatch handle is not a completed result. Complete independent parent work, then yield so completion messages can arrive between turns. Do not poll child transcripts or repeatedly read partial candidate files while waiting. Finite one-shot sessions may join automatically; follow the actual tool response. Children do not provide durable execution after the owner exits. Respect reported concurrency limits and use bounded batches if necessary.

### Optional actual model diversity

Only use named Hermes profiles already configured by `setup-pstack` when genuine model diversity is requested. Load it with `skill_view(name="setup-pstack")`; do not invent entitled model slugs, mutate live model settings, or silently substitute another model. Inspect available profiles with `terminal(command="hermes profile list")` and a selected profile's model with `terminal(command="hermes -p <configured-profile> config get model.default")`.

**One-shot launch gate.** Before any profile-process launch here, load `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`. `-z` bypasses command and hook approval gates. Require explicit authorization for that bypass, review inherited hooks, and verify restricted execution boundaries, scoped credentials, and minimal toolsets. Model-diversity or unattended-work requests are not bypass authorization. Otherwise use bounded parent-driven delegates, an approval-preserving interactive session, or report blocked.

Run each selected profile as an explicit separate process in its own verified worktree or output directory, for example:

```python
terminal(
    command="hermes -p <configured-profile> -z '<complete candidate brief>'",
    workdir="<isolated-workdir>",
    background=True,
    notify=True,
)
```

Replace placeholders with configured values and shell-quote the prompt. Record configured provider/model and verify the actual resolved model from that process's runtime evidence, including fallback use. Configuration alone is not proof of the served model. If unavailable, say model diversity is unverified; a same-model panel remains useful, but is not cross-model confirmation. Terminal process notifications are separate from delegation completions. Keep the parent alive to collect bounded runs and use the terminal process manager only for those explicit processes, not child-transcript polling.

## Phase A: Frame

1. State the artifact each candidate must produce and a falsifiable done predicate.
2. Derive 3-6 concrete gradeable criteria. Keep evaluation details for the parent and judge; candidates receive the task, constraints, and required behavior.
3. Choose candidate count and distinct directions. Use at least two for a real comparison. Same-model repetition is useful for generation-bound work, but agreement does not establish independent model validation.
4. Give each candidate its own output under `$TMPDIR` or the runtime scratch directory. For code, prefer separate worktrees from the same recorded base SHA. Capture uncommitted input explicitly when it is part of the task. A different branch in the same checkout does not isolate files. Load `principle-separate-before-serializing-shared-state` for the ownership rule.
5. Record which paths are writable and forbid writes to shared grounding, other candidates, or external systems. For a no-write judge, state the restriction in its context; it is a behavioral instruction, not a tool sandbox.

## Phase B: Fan out

Dispatch all independent candidate briefs in one batch:

```python
delegate_task(tasks=[
    {"goal": "Produce candidate A using direction A", "context": "<complete task, grounding, isolated working/output paths, constraints, checks>"},
    {"goal": "Produce candidate B using direction B", "context": "<same contract, different direction and isolated paths>"},
])
```

Require the artifact plus a short rationale naming alternatives considered and rejected, files written, checks run, and any blockers. A child must finish its own bounded commands before reporting; a process ID is not a verified artifact.

If a candidate produces no usable artifact, record a dropout. Continue with the remaining candidates only when the comparison still has enough evidence; with fewer than two, retry once or disclose that this is a single-candidate result.

## Phase C: Cross-judge

After all candidates finish, dispatch one fresh-context judge with `delegate_task(tasks=[{"goal": "Judge completed candidates against the rubric", "context": "<rubric, stable candidate labels/paths, no-write instruction, score-and-rationale contract>"}])`.

Give it the rubric and stable path labels, not the parent's preferred choice. Require criterion-by-criterion scores, evidence locations, and a recommended base. A default same-model judge is an independent context, not a different model. The parent reads candidates while the judge works. Never launch judging while candidates are still writing.

## Phase D: Pick a base

Read every candidate end to end with `read_file`; inspect code diffs with `terminal` when applicable. Score criterion by criterion, then compare with the judge. Agreement is a corroborating opinion, not artifact verification. Disagreement may reflect bias or an ambiguous rubric: read both rationales and resolve against evidence.

Prefer the shape a maintainer can extend without breaking invariants. Break ties toward cleaner boundaries or a smaller public API. Load `principle-laziness-protocol` for complexity discipline.

## Phase E: Graft

Revisit each losing candidate for the one or two things worth porting. Fold them into the base deliberately so the result has one mental model. Do not paste candidates together mechanically. Load `principle-redesign-from-first-principles` when integration changes the design.

If candidates converge, note the convergence and do not invent grafts. Convergence among same-model runs is not cross-model consensus. If they diverge because the task was under-specified, reframe and rerun instead of averaging incompatible designs. Legitimate tradeoffs are not themselves evidence of bad framing.

## Phase F: Verify

Load `principle-prove-it-works`. Verify the synthesized artifact directly: read the final output, inspect exact paths/diffs, and run applicable tests or real usage. Child summaries and judge votes are self-reports, not proof of side effects. Check external effects by reading the exact target back when any were authorized.

If the frame was wrong, return to Phase A. If a candidate caught a missed issue, revisit the graft. Do not patch around an invalid contract.

## Outputs and pitfalls

Return one artifact and a synthesis note naming the base, rubric-based reason, judge verdict, grafts and their sources, rejections, convergence, dropouts, actual checks, and evidence gaps. Record whether the run was same-model, globally overridden, or verified configured-profile diversity.

Do not claim parallel execution when delegation is unavailable. Sequential labeled candidates are a disclosed fallback. Do not delete worktrees containing unreviewed work or include scratch scaffolds in the deliverable accidentally.

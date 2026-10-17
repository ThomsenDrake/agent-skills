---
name: figure-it-out
description: "Use when an unfamiliar task needs an auditable plan."
compatibility: "Requires Hermes skill_view, terminal and file tools; delegation when parallel work is useful."
---

# Figure it out

When no narrower playbook fits, design one. Before implementation, produce a workflow with rigor scaled to risk, a hypothesis loop, and an audit trail a human can inspect after stepping away. Then execute it; the plan alone is not the finished deliverable.

## Start

Load `poteto-mode` with `skill_view(name="poteto-mode")` and read its principles. Keep a checklist for Frame, Design, Run, Audit, Verify, then expand it with concrete units as the workflow becomes clear. Load other skills by name, not through their installation paths.

## Phase A: Frame

Ground the system first. State:

- A falsifiable definition of done. Load `principle-prove-it-works` for the evidence standard.
- Quantified scope, rough units/effort, and real blockers from discovery. Use tools for calculations and current state; do not invent estimates as observations.
- The rigor level, biased high for one-way doors and broad blast radius. Reversible low-stakes work needs fewer gates. Rigor means concrete checks and artifacts, not "try harder."

Present framing and tradeoffs before a long run. Continue authorized reversible work without waiting for routine approval, per `principle-never-block-on-the-human`, but a multi-hour commitment earns a checkpoint. Destructive, external, or broader-than-requested side effects still require appropriate authorization.

## Phase B: Design the workflow

Decompose into atomic, independently verifiable and landable units. Sequence riskiest unknowns first. Put scaffold and verification before features; load `principle-foundational-thinking` when needed.

- Build the verification harness before implementation. Capture the real pre-change baseline so results show old versus new, not an invented comparison.
- Use `architect` for one-way-door design decisions; it coordinates `arena`. Skip design competition for mechanical work whose shape is settled. A second arena over a settled shape is unnecessary, per `principle-laziness-protocol`.
- Parallelize only across real seams. Give writers separate worktrees or disjoint outputs under `$TMPDIR` or runtime scratch, never just branches sharing one checkout. Load `principle-separate-before-serializing-shared-state` for ownership discipline. Do not over-fan.
- Write the chosen phases, gates, owned paths, artifacts, and fallback behavior down before the run. This is what the human audits.

### Hermes delegation

**One-shot launch gate.** Before any profile-process launch here, load `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`. `-z` bypasses command and hook approval gates. Require explicit authorization for that bypass, review inherited hooks, and verify restricted execution boundaries, scoped credentials, and minimal toolsets. Model-diversity or unattended-work requests are not bypass authorization. Otherwise use bounded parent-driven delegates, an approval-preserving interactive session, or report blocked.

The parent owns orchestration. Dispatch bounded independent units with `delegate_task(tasks=[{"goal": "...", "context": "..."}, ...])`. Each context includes the complete task, exact working/output paths, scope, accepted starting revision, write limits, verification contract, and expected report. Children do not inherit the parent's conversation history and are not asked to delegate recursively.

Children inherit the parent model unless global delegation settings override it. Distinct roles are the default, not per-call model selection. This is not cross-model evidence. If genuine diversity is justified, load `arena` for its optional process protocol using named profiles configured by `setup-pstack`; verify actual models and isolated working directories. Model aliases do not retarget delegation.

When a dispatch returns a background handle, work only on independent steps and yield for completion messages between turns. Do not poll child transcripts or assume scratch outputs imply completion. Keep the owner alive; running children are not durable across owner exit. A child must finish its bounded commands before reporting. If delegation is unavailable, execute sequentially and disclose that fallback.

Add the designed units to the checklist. Apply the Phase C loop to each and add Phase D audit rows as they land, not at the end.

## Phase C: Run the hypothesis loop

Each unit is an experiment: state a hypothesis, make the smallest change, measure the real artifact against the predicate, keep it if it advances the task, and revert only your own failed experiment if not. Do not undo another worker's or the user's changes. Load `principle-sequence-verifiable-units`; verify each unit before starting a dependent one.

- Use `read_file` and `search_files` for evidence, `patch` for targeted edits, and `write_file` for new artifacts. Use `terminal` for actual checks, not plausible descriptions of commands.
- Verify the artifact, never just a worker self-report. Read candidate paths/diffs and independently exercise decisive checks. If something passes suspiciously easily, test the observation method before trusting the result.
- Pair delegated implementation with a separate judge or parent review after the work is stable. A same-model judge is another perspective, not independent model proof.
- If a worker games a gate, reset and harden the contract. If the gate is wrong, fix it as its own verified unit, not by routing around it.
- Verdicts are `VERIFIED`, `NOT VERIFIED`, or `INCONCLUSIVE`. Inconclusive is not a pass. Record failed tools, access gaps, and negative results honestly.

## Phase D: Keep the audit trail

Load `show-me-your-work` and log decisions, hypotheses, evidence, rejected options, and verification results as the run proceeds. Choose a task-scoped path; include the trail in the review artifact when authorized. Commit it only if the task authorizes commits. The trail plus the diff should let a human understand the work without reading all child transcripts.

For authorized external writes, read back the exact target to verify the effect. A successful API call or a child's assertion is not sufficient.

## Phase E: Verify and hand back

Check the whole deliverable against the original predicate on the real product, not only the harness. Account for every named unit, test, artifact, and blocker. Replace all intended scaffolds with working behavior. Encode recurring corrections in tests, lint, scripts, or structure rather than adding more prose; load `principle-encode-lessons-in-structure`.

Return the designed playbook, rigor level and reason, audit-trail path, completed artifacts, actual verification results, and what remains open. A plan, delegated `PASS`, or clean subset is not completion if the end-to-end acceptance predicate remains unchecked.

---
name: architect
description: "Use when designing architecture before implementation."
compatibility: "Requires Hermes skill_view, delegation, and file tools; git for worktree isolation."
---

# Architect

Sketch types, signatures, class shapes, and module boundaries with `not implemented` bodies and pseudocode. Explore competing whole-system shapes, synthesize one contract, then implement and verify it.

## Start and prerequisites

Use for non-trivial designs where early code would lock in the wrong shape. Do not add a design ceremony to a mechanical change with a settled shape. Keep a phase checklist: Ground, Sketch, Agree, Implement, Scrap.

Load companion skills by name with `skill_view(name="how")` or `/skill how`, never by installation paths. Load this skill's references with `skill_view(name="architect", file_path="references/runner-prompt.md")`, substituting the reference name below as needed.

The parent owns the workflow. Candidate children produce bounded artifacts, not another orchestration tree. Use `delegate_task(tasks=[{"goal": "...", "context": "..."}, ...])` for isolated candidate conversations. Children inherit the parent model unless global delegation settings override it. The default panel uses the same model with distinct design directions. This is not cross-model evidence. Load `arena` for its isolation, completion, and optional configured-profile diversity protocol.

## Phase A: Ground the problem

Build a real mental model of every touched system. Load `how` and run its workflow over the relevant subsystems. Naming files is not grounding: produce its architectural explanation. If the design changes ownership or layering, also load `why` and investigate the existing shape so its rationale becomes a constraint rather than a guess.

Skip this phase only for genuinely greenfield work with no surrounding system to integrate. Completion: the shared grounding package names boundaries, callers, invariants, and evidence gaps.

## Phase B: Sketch

1. Load `arena` with `skill_view(name="arena")`. Give it the design-sketch task, the grounding package, and the full runner prompt from `skill_view(name="architect", file_path="references/runner-prompt.md")`.
2. Require at least two structurally distinct candidates, even if the first looks sufficient. Assign different architectural directions while keeping the task and constraints identical. Load `principle-exhaust-the-design-space` when a design needs broader exploration. Whole-shape alternatives matter, not point fixes inside one shape.
3. Give each candidate an isolated worktree from the same verified base, or its own output directory under `$TMPDIR` or the runtime scratch directory. Use explicit absolute working and output paths in each brief. A plain branch in a shared checkout is not isolation. Keep scaffolds out of the live tree unless explicitly intended.
4. Screen every candidate against `skill_view(name="architect", file_path="references/design-red-flags.md")`. Assume the next contributor sees only opened files, copies the nearest example, and takes the shortest compiling path. Prefer a design where a change that looks right from one file is right for the whole repo.
5. Compare interface depth: how much complexity is hidden behind how small a public surface. A rich implementation can shorten call chains by concentrating capability instead of scattering it across layers.
6. Apply arena's base selection and deliberate grafting. The resulting design package fills the rationale's Synthesis decision section.

Read the actual candidate artifacts before deciding. A child summary is a self-report, not proof that the sketch exists or satisfies the constraints. The parent verifies paths, diffs, and the usage-to-signature agreement.

## Phase C: Agree (opt-in)

Default: proceed to implementation without a human checkpoint, within the authorized scope. If the user explicitly requests a checkpoint, such as "stop and show me before implementing," present the synthesized design and wait for sign-off.

The scaffold can be a separate commit when the task authorizes commits. Load `principle-foundational-thinking` for scaffold-first sequencing and `principle-outcome-oriented-execution` for explicitly scoped temporary breakage during fill-in. Do not present placeholders as a finished implementation. Load `interrogate` for adversarial design review before coding.

If the human challenges the shape, treat that as new grounding evidence. Re-ground and repeat Phase B before writing more implementation.

## Phase D: Implement against the sketch

Replace placeholders with code and pseudocode with logic. The synthesized sketch is the contract. Surface deviations rather than absorbing them silently. If a function needs an unanticipated parameter, decide whether the sketch was wrong, a requirement was missed, or the implementation is overreaching.

Use `read_file` and `search_files` for discovery, `patch` for targeted edits, and `write_file` for new artifacts. Exercise the real behavior and the project's applicable tests. Completion: no intended runtime path is still a stub, and verification covers the stated contract.

## Phase E: Scrap when the architecture is wrong

When repeated friction cannot fit the sketch, redesign instead of bolting fixes onto it. Load `principle-redesign-from-first-principles` and `principle-fix-root-causes` as needed.

Look for a pattern, not one exception:

- The same workaround recurs in unrelated code.
- Several unrelated edge cases need special branches.
- Types require escape hatches such as `any`, casts, or supposedly optional fields always set in practice.
- Implementation needs locks even though the sketch said state was separate.
- Callers must know internal rules to use the abstraction.
- Two or more independent implementation deviations share the same shape.

Some problems are legitimately complex. Complexity in data is not itself a design failure. When scrapping:

1. Re-run `how` over what was built.
2. Redesign with the new constraints as day-one assumptions.
3. Load `principle-subtract-before-you-add`: make the new sketch smaller before it grows.
4. Return to Phase B for a fresh arena.

## Outputs and verification

Write the caller's usage first and derive the type sketch from it. Small changes need a type/signature file; larger work needs a module map plus type definitions. Ship the rationale shaped by `skill_view(name="architect", file_path="references/rationale-template.md")`, including usage, synthesis, tradeoffs, rejected shapes, and the next implementation step.

Verify each candidate's existence, each accepted boundary and invariant, and the completed implementation. Report actual checks, design deviations, and unresolved risks. If delegation is unavailable, perform and label sequential independent drafts; do not claim a parallel or cross-model panel ran.

### Visual parity

**You own pixel-exact equivalence. The baseline is the spec. You do not touch it.** Equivalence is verified by image diff, not by eye.

1. Establish the baseline before migration. Discover or build a visual regression harness that screenshots the current component across its states, plus the target when matching two implementations. Pin viewport, scale, browser, fonts, assets, state, and animation timing. Run it through `terminal` or available Hermes browser/computer-use tools. Screenshot and image-diff dependencies must be available first. No baseline means no parity claim. This is a blocking prerequisite, not a follow-up.
2. State and hold the anti-shortcut clauses. No harness modifications, baseline tampering, weakened threshold, or component restructuring just to make a diff pass. If the baseline looks wrong, stop and ask instead of editing it. Save baseline inputs and receipts separately from candidate output.
3. Migrate one component at a time with `read_file`, `search_files`, and `patch`. Shared primitives migrate first as a blocking phase. Load `skill_view(name='principle-separate-before-serializing-shared-state')` and use one owner per component and isolated worktree for parallel work. `delegate_task(tasks=[{'goal': '<component migration>', 'context': '<worktree, allowed files, immutable baseline, exact image-diff command, report>'}])` inherits the parent model; do not assume recursive delegation or automatic worktree creation.
4. Verify each component on the same surface against its baseline with the exact image-diff command. A nonzero diff is a fail. Investigate the pixel delta and repeat the bounded change/verify loop until zero. Log attempts and retain diff artifacts. Do not relax parity on a plateau. If the environment cannot render a comparable capture, report the blocker instead of calling it a pass. Review child diffs and actual image-diff output yourself.
5. For an authorized PR, load `skill_view(name='poteto-mode', file_path='playbooks/opening-a-pr.md')` per component or safe batch.

**Reply:** components migrated, exact diff result for each, baseline harness location, evidence paths, and what remains.

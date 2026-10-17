### Feature

**One-shot launch gate.** Before any profile-process launch here, load `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`. `-z` bypasses command and hook approval gates. Require explicit authorization for that bypass, review inherited hooks, and verify restricted execution boundaries, scoped credentials, and minimal toolsets. Model-diversity or unattended-work requests are not bypass authorization. Otherwise use bounded parent-driven delegates, an approval-preserving interactive session, or report blocked.

**You own the design. Plan, review, verify.** Delegate bounded implementation when available. Stay in the lead and verify the artifact yourself.

1. Load `skill_view(name='how')` over the affected subsystem. Discover project rules, test commands, and the real user surface with `search_files` and `read_file`.
2. Load `skill_view(name='architect')` for parallel design exploration. A same-model panel is the default and is not multi-model evidence. Different model families require operator-configured named profiles, separate terminal runs, and recorded actual identities, not invented model slugs.
3. Write the throughput checkpoint as four todo items. A dimension that does not apply keeps its item with `n/a: <reason>`.
   - **Blocking first steps.** Gates run before fan-out.
   - **Independent workstreams.** Disjoint files, services, or layers parallelize. Shared writes serialize.
   - **Shared mutable state.** Load `skill_view(name='principle-separate-before-serializing-shared-state')`. Split the target before adding serialization, unless a real invariant requires it.
   - **Smallest safe decomposition.** If one worker is best, name why.
4. Load `skill_view(name='principle-model-the-domain')` and choose the data shape before logic. Prefer a state machine to scattered booleans, a registry to repeated branching, and a typed model to repeated shape assumptions. Give code-writing to `delegate_task(tasks=[{'goal': '<implementation outcome>', 'context': '<repo, exclusive worktree or file boundary, data shape, success criteria, test commands, forbidden actions, report>'}])` when available. Children have isolated contexts, inherit the parent model, and are leaf workers by default. Do not require recursive fan-out. When several valid implementation shapes exist, load `skill_view(name='arena')` for separate candidate and review passes. Without delegation, implement directly and keep the same explicit alternative review. Do not wait on a nested worker you cannot spawn.
5. Review the actual diff with `read_file` and a diff command through `terminal`. Keep edits surgical. Re-ground upstream-derived files against their source, port shared-primitive improvements to all consumers, and verify each. Remove generated boilerplate and comments that only narrate code. A child report is unverified until you inspect its artifact and receipts.
6. Verify on the matching real surface. Use the repo's CLI or UI harness through `terminal`, or available Hermes browser/computer-use tools. Name required optional drivers before the run. "Inconclusive" or wrong-surface is not a pass. Keep screenshots, logs, and failing/passing test output as appropriate.
7. Load `skill_view(name='principle-sequence-verifiable-units')`. Build, verify, and commit each small unit before the next when commits are authorized. Reorder into small ordered commits without discarding unrelated work. Stack only authorized follow-ups.
8. If the design is contested, load `skill_view(name='interrogate')` before shipping. If a PR is authorized, load `skill_view(name='poteto-mode', file_path='playbooks/opening-a-pr.md')`.

Code-coupled work such as one feature or migration gets one implementation owner with the checkpoint inline. The parent schedules any later slices after that owner returns. Parent-level fan-out is for independent artifacts such as audits, cross-subsystem investigations, or competing experiments. Rewrite the checkpoint at phase boundaries and use a fresh consolidated brief for the next unit.

For background delegation, do other independent work, then end the turn. Results arrive between parent turns. Do not poll child transcripts, and do not claim the child survives the parent process.

**Reply:** what you built, what you chose and why, the throughput checkpoint, verification output, and open decisions. Use a table for design alternatives.

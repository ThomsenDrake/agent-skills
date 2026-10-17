### Perf issue

**You own the measurement story. Plan, review, verify the numbers.** Tie every fix to a measurement. Do not read source instead of measuring.

1. Capture a baseline trace on the matching surface. Discover the repo's profiler or harness through `search_files` and `read_file`, then run it through `terminal` or available Hermes browser/computer-use tools. No control plugin is assumed. Record workload, environment, errors, work count, and artifact path. Load `skill_view(name='benchmark-checklist')` to vet the baseline and every later number.
2. Load `skill_view(name='how')` to ground hypotheses. Do not claim a performance ceiling without running it first. Try the performance mantras in order, cheapest first.
   1. Don't do it. Stop work whose result nothing uses rather than cheapening it.
   2. Do it, but don't do it again.
   3. Do it less.
   4. Do it later.
   5. Do it when they're not looking.
   6. Do it concurrently.
   7. Do it cheaper.

   When an earlier mantra meets the target, stop.
3. Plan from the trace. If the fix crosses a function boundary, load `skill_view(name='architect')` first. Use a bounded `delegate_task(tasks=[{'goal': '<specific fix>', 'context': '<repo/worktree, trace finding, allowed files, metric harness, regression gates, report>'}])` when available. The child inherits the parent model and cannot be assumed to delegate. Otherwise implement directly and run a separate review. Review the actual diff, capture a post-fix trace, and load `skill_view(name='principle-sequence-verifiable-units')` to verify each attempt before the next.
4. Parse and compare the real artifacts through `terminal`, for example JSON into SQLite and paired queries. Use matched workload and environment, interleave before/after probes, and compute deltas with a tool. Preserve correctness and count errors. "Inconclusive", measurement noise, or wrong-surface is not a pass. Flag it rather than publishing a speedup.
5. Cite the measurement and artifact in the PR if publication is authorized. Include one primary metric with a unit and the before/after values.
6. Load `skill_view(name='poteto-mode', file_path='playbooks/opening-a-pr.md')` only for an authorized PR.

For sustained improvement against a target rather than a one-off fix, load `skill_view(name='poteto-mode', file_path='playbooks/hillclimb.md')`.

**Reply:** baseline number, post-fix number, computed delta, exact measurement command, artifact path, and any unresolved validity limits.

### Trace forensics

**You own the diagnosis from the artifact.**

Unlike runtime forensics, the capture already exists. It is a fixed dataset. Read it, do not rerun the workload or rewrite the input. Use a format-appropriate DevTools or trace parser for cpuprofile and `.json.gz`, a text reader for a spindump, and heap tooling for a heapsnapshot. Discover optional tools before relying on them.

1. Identify the format with `read_file` for text or a small format-aware inspection through `terminal` for compressed or binary artifacts. For bulk analysis, use `delegate_task(tasks=[{'goal': '<bounded diagnosis question>', 'context': '<exact capture, format, read-only constraint, required evidence and source mapping>'}])` when available. Children inherit the parent model and have isolated contexts. Load `skill_view(name='principle-guard-the-context-window')` and retain reduced findings, not raw dumps. Verify child claims.
2. Transform a copy into a queryable form through `terminal`, for example SQLite rows for samples, frames, or nodes. Save derived files under `$TMPDIR` or the approved artifact directory. Preserve timestamps, units, parent-child links, symbols, and the original capture. Reach the queryable shape before guessing from snippets.
3. Narrow to the cause. Query frames that hold the most time and walk the call tree to the hot path. For a leak, follow retainers to a GC root. For a spindump, find the thread stuck on-CPU or blocked and its wait reason. Include the query and output supporting the finding.
4. Attribute to source with `search_files` and `read_file`. Map the hot frame to file, symbol, and line through the artifact's symbols. A frame with no mapping is not yet a source-level diagnosis. Resolve symbols or say plainly the capture does not carry them.
5. If a paired capture exists, diff the before/after artifacts on matched workloads to confirm. Otherwise mark the finding as the strongest hypothesis supported by this artifact, not a confirmed cause. Compute counts and deltas with a tool.
6. Hand back a cited diagnosis, no fix unless asked. Route authorized follow-up to `skill_view(name='poteto-mode', file_path='playbooks/bug-fix.md')` or `skill_view(name='poteto-mode', file_path='playbooks/perf-issue.md')`. Keep the checkpoint to one line. `throughput checkpoint: n/a, read-only forensics`.

**Reply:** artifact and format, reduced finding, queries and source location, derived artifact paths, and whether a paired capture confirmed the cause.

### Orchestrate

**You own the program, not the implementation. Author briefs, drain the queue, keep the frontier green, and decide.** Use for a standing multi-day project with many units and PRs, not work one session can finish. A single task driven to a predicate loads `skill_view(name='poteto-mode', file_path='playbooks/autonomous-run.md')`. A bespoke one-run workflow loads `skill_view(name='figure-it-out')`.

Ceremony scales with the program. Cheap near-identical units use a light brief and inline verification. Three rules carry the rest.

- Completions are queue events, not interruptions to an atomic step.
- Every dispatch and replacement carries the full current standing orders.
- The brief is the product. Missing scope or evidence requirements are reasons not to dispatch.

#### Runtime and role boundaries

**One-shot launch gate.** Before any profile-process launch here, load `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`. `-z` bypasses command and hook approval gates. Require explicit authorization for that bypass, review inherited hooks, and verify restricted execution boundaries, scoped credentials, and minimal toolsets. Model-diversity or unattended-work requests are not bypass authorization. Otherwise use bounded parent-driven delegates, an approval-preserving interactive session, or report blocked.

Native `delegate_task(tasks=[{'goal': '<bounded unit>', 'context': '<full scoped brief>'}, ...])` is for bounded workers with isolated contexts and inherited parent model. It is not a durable coordinator fleet, a per-call model router, an automatic worktree manager, or a recursive worker tree. Leaf workers do not spawn other workers by default. Dispatch them from the coordinator. The default batch delivers one consolidated result between parent turns. Do independent work, then end the turn. Do not poll transcripts, artifacts, or unrelated CI while waiting for a native completion, and do not assume a follow-up message updates a running child's brief.

For work the user explicitly wants to outlive this conversation, use actual operator-configured named profiles with reviewed tools, model identity, workspace access, and every launch-gate precondition above. Configured approvals do not protect a `-z` run. A real launch is `terminal(command='hermes -p <profile> -z "Read <absolute brief path>; execute only that brief and write the named report"', workdir='<exclusive worktree>', background=true, notify=true, persist_on_release=true)`. Materialize the complete brief with `write_file` first and verify the profile can read it. Track the returned terminal session ID and actual exit/result. Do not create profiles, change config, or select invented model slugs as an implicit setup step. Never infer approval-bypass authorization from the requested lifetime. `persist_on_release` survives session cleanup only, not host restart. Host-restart durability needs an operator-managed service or scheduler. If those dependencies are absent, run bounded supervised waves and report that unattended continuation is unavailable.

- **Coordinator.** This session, or an explicitly managed coordinator profile process. Frames the program, authors briefs, drains the inbox, owns human reports, and makes decisions. It does not write implementation code. Clean integration of verified commits may be bookkeeping when authorized; conflict resolution, code edits, chain rebases, and merges need an explicitly scoped owner/lander phase. Record actions through the bookkeeping CLI below. The CLI does not spawn, wait for, or wake an agent.
- **Track owner.** Optional only when one coordinator cannot manage the ready queue. Prefer a flat coordinator-to-worker plan. A track owner is a bounded planner returning briefs/rollups, or a separately launched operator-managed profile process with explicit runtime and permissions. Never assume a delegated child becomes a durable sub-coordinator or has permission to recurse. The root schedules its workers unless an actual configured orchestration service owns that track. Record that single scheduler. Extra layers must earn their orientation cost.
- **Worker / verifier.** One bounded unit, one exclusive worktree/branch or disjoint file set. No default cloud environment. Verify that the chosen terminal backend can reach the repo, driver, credentials, artifacts, and authorized data before dispatch. A remote backend is an explicit optional dependency. Use fresh independent verifier contexts for costly or high-risk work. Same-model reviewers are the default, not multi-model evidence. Actual diversity requires operator-configured named profiles with genuinely different models and recorded identities.

#### Store and helper setup

Use `<approved durable store>/orchestrate/<project-slug>/`. There is no assumed editor agent-store path. Keep scratch worktrees and transient probes under `$TMPDIR`; scratch is not a durable postmortem. Confirm the store's ownership, retention, and sensitive-data limits. Every fact file has one writer. Workers write their report/receipt path, and the coordinator alone updates shared tables. Readers derive aggregates rather than rewriting an owner's facts.

Load `skill_view(name='poteto-mode')` and resolve `<poteto-mode-skill-dir>` from its returned directory. The preserved helper requires Bun and locked dependencies; PR frontier discovery also needs Git and authenticated `gh`, or optional Origin. Its bootstrap may install packages beside the script. Use an approved writable installation or scratch copy rather than changing a read-only skill. Inspect `terminal(command='bun run "<poteto-mode-skill-dir>/scripts/orch/orch.ts" --help')`. All `orch ...` shorthand below means `terminal(command='bun run "<poteto-mode-skill-dir>/scripts/orch/orch.ts" --store "<approved durable store>/orchestrate/<project-slug>" <arguments>', workdir='<repo>')`. Always supply `--store` or a deliberately set `ORCH_STORE`.

- `preferences.md` is the numbered standing-orders register. Include scope, model policy, stack shape, verifier bar, forbidden paths/actions, escalation, and stop policy. Paste it verbatim into every brief and replacement, even when the brief is a file. Encode repeated corrections here before acting. Load `skill_view(name='principle-encode-lessons-in-structure')`.
- `overview.md` is the durable PR/issue history. Append facts rather than rewriting it on every event.
- `units.tsv` records id, track, state, branch, PR, head SHA, and brief path. The coordinator updates rows through `orch unit add` and `orch unit set`.
- `frontier.json` is the computed stack frontier, not a prose guess.
- `ledger.tsv` is the verification ledger keyed by PR/head.
- `inbox/` holds completion pointers. `gates.md` records questions, options, and safe no-action defaults. A default never supplies missing merge, deletion, credential, or message authority.
- `decisions.tsv` is the trail from `skill_view(name='show-me-your-work')`.
- `runs.tsv`, when needed, maps each unit/phase to the actual delegation or terminal handle, runtime budget, worktree, remote lease, report path, and terminal state. It does not claim the process will survive a restart.
- `status.md` is derived from unit and ledger tables with `orch status`, not manually narrated.

If Bun/helper dependencies cannot be used, the coordinator can maintain the same plain TSV/JSON contract with `read_file`, `patch`, and `write_file` and validate counts with `terminal`. Mark this fallback and verify schema, unique keys, and computed totals. Never pretend helper output was produced.

#### The brief

Every dispatch carries enough context for a stranger with no chat history. A field you cannot fill means the unit is not scoped yet.

```
GOAL         One outcome.
SCOPE        Exact allowed/forbidden paths and exclusive worktree/branch.
CONTEXT      Source and PR pointers plus the relevant upstream findings and receipts.
ACCEPTANCE   Checkable criteria, one per line.
VERIFY       Exact commands or actual driver, expected output, and known limitations.
TIMEBOX      Runtime/cost cap; report partial findings on expiry and stop safely.
FORBIDDEN    No ungranted PR, push, merge, retarget, rebase, force-push, messages,
             credential access, deployment, deletion, or out-of-scope fixes.
REPORT       Status, artifact paths, branch/head, PR, actual runs/output, verdict,
             deviations, blockers, and next action. Do not leave child-owned jobs running.
STANDING     Current preferences.md pasted verbatim.
```

Collapse a one-command unit to a paragraph, but keep its goal, scope, command, gates, and report contract. Dependencies are context relays, not just ordering. The root reads an upstream report as unverified input, checks its receipts, and passes necessary findings to the downstream brief. Do not assume siblings share chat history or a remote worker can read the local store.

A track-planning brief adds its unit list, dependency graph, boundaries, scheduling owner, rollup contract, and runtime limitations. Audit a sampled brief per track alongside a wave. A bad sample stops the next refill and fixes the template/standing orders, not only that worker. Replacement means a fresh consolidated brief with original scope, all later directives, current artifacts, and authorization. Do not resume-chain stale instructions.

#### Procedure

1. **Frame and authorize.** State a countable predicate, unit count, effort, stacks, wall-clock/cost budget, allowed actions, review gates, and who may land. If one agent can finish inside the budget, collapse to direct session work with bounded helpers and inline verification; skip the program store/track machinery. Do not interpret "own this project" as permission for unrelated writes. Schedule integration from the first unit and stop spawning around the budget's final 30% when that leaves time for verification and handoff. Load `skill_view(name='arena')` for a contested decomposition or irreversible design choice, using honest same-model evidence unless real profiles exist. Present the framing. Reversible prep proceeds within the grant, but execution or landing waits for any explicit go gate.
2. **Initialize the record and runtime.** Run `orch init`. Write standing orders and the trail before any dispatch. Seed an existing stack with `orch frontier set --repo <repo-dir>` and `--forge origin` only if Origin was selected. A new program without PRs records no frontier until a real chain exists; do not invent PR rows. Record handles and lifecycle expectations. For a long unattended program, verify the real coordinator process/scheduler and checkpoint path, not a claimed durable chat.
3. **Pilot one unit.** Push one unit through brief, implementation, checks, verification, ledger, and the authorized delivery endpoint. That endpoint is merge only with landing authority; otherwise it is merge-ready or STACK-READY. Use the first normal unit as the pilot for cheap near-identical work, with its verify command inline. Novel/high-risk units get an independent verifier and audit gate. Fix brief, driver, and unit-size problems from actual pilot evidence before fan-out.
4. **Scale within measured capacity.** Root-dispatch flat batches up to the actual available concurrency and review capacity. Do not invent a hard cap or configure a larger one mid-run. Native batch results normally arrive together, so refill after delivery, not by polling child side effects. Keep independent coordinator work moving and then end the turn. Separately tracked terminal jobs can notify individually and support a rolling window. Relay verified upstream context, maintain exclusive writers, and use optional track planners only when they reduce root load. A failed sampled-brief audit stops the next refill.
5. **Drain using the queue discipline below.** Classify every delivered completion, update tables, and schedule only work with satisfied dependencies and current authorization. Never count a child summary as verification.
6. **Integrate continuously.** Land or stack verified units as they become ready according to the grant. One topology owner per stack applies Stack safety. Keep the lowest unmerged frontier green before spending on upper links. A heavy repo may use a dedicated bounded integration role or managed profile; no mandatory remote environment or standing leaf agent. Advance frontier facts only after actual forge/base/head readback.
7. **Close.** Drain all delivered inbox items and reconcile every spawned unit to done, blocked, failed, abandoned, or late-result-reconciled. Account for still-running jobs rather than labeling them done. Confirm the predicate on the real artifact and each landed PR's accepted head verdict, including documented carry-forward evidence. Audit the decision trail with an independent review, labeled same-model unless actual diversity was used. Encode recurring corrections in standing orders or the brief template. Leave the store intact as the postmortem.

#### Queue and drain

- Delivered completions become pointers with `orch inbox push <agent> <unit> <status> --report <path>`. Finish an atomic brief, topology operation, gate, or table update before reviewing a result. A notification is not a request to abandon the current critical section.
- Drain after a critical section, a delivered batch/track rollup, a real frontier watcher event, and before a human report. Begin with `orch inbox drain`. Arrivals during a drain wait for the next one. No invented loop tool or transcript-mtime watcher.
- Classify each pointer as needs-verify, verified, failed, stale/late, blocked, or noise. Update `orch unit add`, `orch unit set`, and `orch ledger record` as appropriate. Do not deep-review a diff inside the bookkeeping drain. Make that a bounded review unit or a separate explicit review step.
- Run `orch status`, read complete rows with `--json` when compact output reports more, and compute declared counts from those tables. Schedule the next ready batch in one dispatch only after dependencies are satisfied.
- Account for every child at rollup, including arrived, failed, interrupted, replaced after confirmed stop, or explicitly absorbed scope. A missing result is a coverage gap, not implicit success.
- A drain update uses the three `orch status` lines for counts, changes, and open gates. Full artifacts stay in the store. Report only newly tracked operator-relevant changes; unchanged blockers do not need a repeated table.

#### Stack safety

- Recompute `frontier.json` after every actual merge or topology mutation. It records ordered PRs, branches, heads, generation, and lowest unmerged PR. `orch frontier set --repo <repo-dir>` walks the checked-out branch's PR base chain through the selected forge; it defaults to `gh`. Local head refs must be freshly synchronized from the integration owner's clone before use. A branch with no PR is an error, not an invitation to guess. Read the exact forge targets back after external writes.
- Exactly one named topology owner per stack may perform authorized rebases, leased force-pushes, retargets, closes, and merges. Quiesce the branch writer before taking its lease. Branch protection and operator review still apply. Run expensive work on a verified available backend, not an assumed cloud machine.
- Workers never mutate stack topology. Babysit loads `skill_view(name='poteto-mode', file_path='playbooks/babysit.md')`, has one owner per stack and a pinned frontier generation, and reports conflicts to the topology owner.
- Closing or retargeting a base can orphan upper PRs. Treat those actions as explicitly scoped topology units and check the whole affected chain. A merge grant does not authorize closing someone else's PR.
- If authorized, a parent-owned bounded watcher checks merged PRs for reverts, post-merge failures, and follow-ups. Record its job ID, deadline, and stop path. It is not a native child expected to outlive completion.

#### Verification

Scale to the unit. A single cheap exact check can be run by the worker and re-run or spot-checked by the coordinator. Expensive, judgment-heavy, behavioral, or high-blast-radius work gets a fresh independent verifier context. Different-model review is optional and requires configured profiles; do not call same-model agreement multi-model proof. Real-surface verification uses a discovered driver through `terminal` or available Hermes browser/computer-use tools, not a mandatory control plugin.

Use `orch ledger record <pr> <sha> <verdict> --evidence <path> --verifier <identity>` and `orch ledger check <pr> <sha>`. Verdicts are `live-ui-verified`, `unit-test-verified`, `type-check-only`, `verifier-blocked`, or `verifier-failed`. CI green is input, not the verdict. Behavioral work needs more than type-check-only, and no blocked/failed lane is a pass. Store actual commands, outputs, base/head, and artifact pointers. A self-report stays labeled until checked; verifier evidence overrides an unproved owner claim for the same key. A new head needs a fresh row or explicit evidence-backed carry-forward under `skill_view(name='poteto-mode', file_path='playbooks/shipping.md')`, never memory.

Externalize a unit's authorized output as soon as retained, not at program end. Verify pushed heads and PR state, retain receipts outside disposable worktrees, and stop child-owned jobs before the child returns. A worker's private checkout or an expired VM is not the durable deliverable.

#### Liveness and failure

- Do not resume an idle agent to ask status. For real terminal profile runs, inspect the owned process via `process_manage`, report/checkpoint path, pushed branch, and forge state. Native delegation completion is delivered between turns; do not poll its transcripts or assume a missing summary proves a stall. Transcript mtime is not liveness.
- A process failure or expired budget gets a synthetic inbox row naming unit, observed failure, last evidence, and options. Before replacement, confirm the old writer stopped or revoke/quarantine its branch/worktree and choose a new exclusive scope. Never overlap two writers because one was quiet.
- Retry by evidence. Capacity/OOM calls for smaller scope or concurrency. A transport drop may retry as-is after side-effect reconciliation. Tool errors need a corrected dependency or supported alternative, not an invented model flag. Unknown failure gets one bounded retry. After two failed retries, abandon/replan or ask for the precise missing resource. Never repeat a non-idempotent external write without readback.
- A late result reconciles against current frontier, head, and ledger. Salvage unique findings through a fresh bounded unit, not a blind merge.
- If fan-out would spread invalid upstream output, broken acceptance, or dead infrastructure, stop dispatching, record the stop in standing orders, checkpoint/stop in-flight writers safely, fix the cause, and only then clear it.
- Bound coordinator infrastructure retries too. After repeated aborts, write a durable handoff with completed artifacts and the exact supported resume command, then stop instead of claiming the program continues unattended.
- After a parent/backend restart, native children are not resumed. Inspect actual terminal jobs; even persistent jobs may have died with the host. Re-read standing orders, units, reports, and frontier, reconcile already-applied external effects, and dispatch fresh briefs for unknown phases only after ownership is safe. The helper can replace a lock with a demonstrably dead PID; never use `--force` to steal a live store. PID assumptions across hosts need explicit coordination.

#### Escalation and reports

Batch genuine decisions in `gates.md` and the status report. Escalate irreversible or ungranted writes, shared-branch rewrites, deployments, data deletion, messages, secret access, another owner's PR closure, product/preference decisions no measurement can settle, contradictory standing orders, and dead ends that survived a replan. Route other work around the gate. A safe no-action default is not permission to bypass it.

Routine retries, CI classification, format fixes, and topology mechanics proceed only inside their already-authorized scope. Refuse a forbidden scope rather than asking repeatedly. Mid-run discoveries fix only authorized blockers of the frontier; other ideas go to follow-ups so fan-out does not multiply scope leaks.

**Reply:** at checkpoints and close, give the predicate and counts from complete unit/ledger tables, tracks and actual delivered/landed work, frontier PRs/heads, accepted verdict summary, failed/abandoned units and reasons, open operator gates, any running or unknown jobs, and store/trail paths. Include actual PR links. Distinguish merged, queued, STACK-READY, and merely reported work.

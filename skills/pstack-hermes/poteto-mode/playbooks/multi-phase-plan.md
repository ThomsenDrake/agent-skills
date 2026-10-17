### Multi-phase or multi-PR plan

**One-shot launch gate.** Before any profile-process launch here, load `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`. `-z` bypasses command and hook approval gates. Require explicit authorization for that bypass, review inherited hooks, and verify restricted execution boundaries, scoped credentials, and minimal toolsets. Model-diversity or unattended-work requests are not bypass authorization. Otherwise use bounded parent-driven delegates, an approval-preserving interactive session, or report blocked.

**You own the plan, not the code. The plan is a checklist an owner runs box by box and the operator audits from evidence.** The plan is the deliverable. Do not implement it or arm automation before the explicit go.

1. If the change is one or two files with an obvious approach, say a multi-phase plan is unnecessary and stop. Do not treat that as implementation approval.
2. Settle empirical questions before writing. Load `skill_view(name='poteto-mode', file_path='playbooks/prototype.md')` for each authorized throwaway probe. Keep branch/SHA when one exists and real screenshots/output for Appendix A. Ask only for a product/preference call no observation can settle, with options. Load `skill_view(name='principle-never-block-on-the-human')` without weakening authorization gates.
3. Explore with bounded `delegate_task(tasks=[{'goal': '<one planning question>', 'context': '<repo, exact files, read-only scope, needed conventions, test commands, entry points, report>'}, ...])` when available. Children inherit the parent model, have isolated contexts, and do not recursively delegate by default. No per-call model/reasoning/speed flags. Load `skill_view(name='principle-guard-the-context-window')`, verify returned pointers, and retain reduced findings instead of dumps. Without delegation, do the bounded exploration directly. Do independent work and end the turn for background completion delivery; do not poll child transcripts.
4. Copy the skeleton below to the operator's named path, or `docs/plans/<slug>.md` in the approved repo when no path is named. Fill every placeholder and preserve heading/sub-block order. One section per independently verifiable PR. Load `skill_view(name='principle-sequence-verifiable-units')`. Name execution in **How to read this** using `skill_view(name='poteto-mode', file_path='playbooks/autopilot-full.md')` for independent PRs with explicit landing authority, `skill_view(name='poteto-mode', file_path='playbooks/autopilot-stack.md')` for a reviewable dependent chain, or `skill_view(name='poteto-mode', file_path='playbooks/orchestrate.md')` for a standing program. Name who can merge and all operator-reserved items.
5. Write under `skill_view(name='technical-writing')`, then apply `skill_view(name='unslop')`. The body is a how-to; appendices contain explanation/reference. Headings state tasks or findings. Use no long dashes or mid-sentence connector colons.
6. Validate the filled file with `terminal(command='bun run "<poteto-mode-skill-dir>/scripts/check-plan.mjs" "<plan.md>"', workdir='<repo>')`, resolving the directory from `skill_view(name='poteto-mode')`. Bun is an explicit dependency; Node can also run this standalone `.mjs` checker through `terminal` if Bun is absent. This script requires a plan filename and has no help switch. It checks shape and some literal markers, not whether the plan ran or every media-recording step exists. Manually audit the scenario, screenshot, video, and pass-predicate boxes as well. Fix every real problem. Never invent a model, ref, screenshot, scheduled job, or successful run just to make its string checks green. Report a verifier limitation explicitly if the actual environment cannot satisfy a pinned example.
7. Hand back the plan path and actual checker output, then stop. Execution begins only on the operator's go under the named execution playbook. Planning itself does not authorize implementation workers, PRs, messages, merges, secrets, deletion, or runtime profile/config changes.

**Verification rule.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Each verification block opens with that exact rule. The live block is mandatory. Ten concrete lanes run at the exact PR head, with one regression lane against trunk. Each names the scenario, screenshot, pass predicate, and real driver. Concurrency can be bounded waves or serial runs; ten lanes do not imply ten machines or different models. The default is same-model workers inherited from the parent. Record their actual model identity in the filled plan and do not call it multi-model evidence. True different models require operator-configured named profiles and separate `terminal(command='hermes -p <profile> -z "<bounded brief>"', workdir='<exclusive worktree>')` runs.

If trunk lacks the feature, record that fact. Gate the diff-added behavior and end state the user waits for, not an invented trunk result. Performance is dual-sided. Both trunk and head must emit the named common metric. Baseline is measured first, followed by interleaved matched probes and a numerical failure rule. If scenarios differ, do not claim a ratio. Add absolute budgets for the diff-added work and user-visible end state. Interactions require operator review in chat with screenshots and a 30 to 60 second video before merge. A PR with no changed interaction writes `**Review gate.** None. <PR id> is not review-gated.` and no boxes under it. A blocked surface or metric stays unchecked, never becomes a silent waiver.

**Drivers and runtime.** Discover the repo's CLI/UI harness and invoke it through `terminal`, or use available Hermes browser/computer-use tools. No control plugin or cloud service is assumed installed. Two changed surfaces need coverage on both. Record missing drivers as Appendix C risks and prerequisite gates, with the actual lane procedure. Use isolated worktrees under `$TMPDIR` or an approved worktree directory, known test data, and explicit readiness signals. Scratch captures are not durable until copied to the approved artifact store. Native delegation is bounded and process-local. For a multi-day unattended program, require a real authorized named-profile process/service/scheduler and checkpoint store; never claim a delegated child persists across the parent exit.

The skeleton keeps the preserved checker's example markers. A `git show origin/main:` source audit is valid only when that is the actual fetched trunk; otherwise substitute the discovered ref and report any literal-marker limitation. A `/loop 1h` audit is a documented optional Hermes session facility, not a claim of a portable tool or host-restart durability. Inspect available Hermes help/docs and confirm actual acceptance before reporting a loop armed. If unavailable, select a real supported parent-owned watcher or approved scheduler with an hourly audit and an explicit stop path. Do not configure a runtime merely to satisfy a plan.

````markdown
# <Program> plan

<Under ten lines. What changes, for whom, the program's rule, and PR ids in order.>

## How to read this

One box is one unit of work. Every box names the evidence that checks it. A nested box is a sub-step of its parent. Check a box only when its evidence exists, such as a file, log, screenshot, test run, or SHA. The body is a how-to. The appendices explain and record.

The program loads `skill_view(name='poteto-mode', file_path='playbooks/<execution-playbook>.md')`. <Who merges, which actions are authorized, which PR ids stop at merge-ready or STACK-READY, and operator review gates.>

Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

## Program checklist

### Arm the program

- [ ] State this plan, grant, resource budget, and runtime limits to the operator, then stop. Execute only on the operator's explicit go.
- [ ] At start and each actual audit wake, reload the approved installed instructions with `skill_view` and record the source revision.
  - [ ] Load `skill_view(name='poteto-mode', file_path='playbooks/<execution-playbook>.md')`.
  - [ ] Load `skill_view(name='swarm')`.
  - [ ] Read <repo driver docs> with `read_file` and confirm optional dependencies.
  - [ ] Load `skill_view(name='poteto-mode', file_path='playbooks/opening-a-pr.md')`.
  - [ ] Load <each named leaf skill> through `skill_view(name='<name>')`.
  - [ ] Audit the tracked plan against the fetched actual trunk. The main-trunk example is `terminal(command='git show origin/main:<plan-path>', workdir='<repo>')`. Replace the ref when trunk differs and never assume installed skills are tracked there.
- [ ] On go, arm a real hourly audit. If the installed Hermes session supports it, `/loop 1h <tick prompt below>` is one session-scoped option. Otherwise use <supported parent-owned watcher or approved scheduler, actual command, handle, deadline, and stop path>. Verify acceptance/liveness before marking this box. Work that must survive the session needs a real managed process or scheduler, not native delegation.
- [ ] Use this tick prompt. "Reload the approved execution playbook and standing orders. Audit the operation and fix authorized drift in this tick. Check delivered results, known terminal process status, current PR heads, receipts, and gates. Do not poll native child transcripts while waiting for completion. Stop or quarantine an old writer before replacing it. Post a short status message only for newly tracked changes such as a PR opened, code-ready head, verification round, verdict, merge, stuck job and action, blocker change, or operator-only decision. Name those changes and no repeated table or unchanged blocker. If none changed, leave only the durable audit row. Log what was reported or none. Never exceed the recorded grant."
- [ ] On hold, stop new dispatches/writes and known owned jobs, confirm cancellation where supported, quarantine any unconfirmed writer, and checkpoint all phases.

### Spawn owners

- [ ] Assign one owner role per PR and dispatch bounded phases from the coordinator. Children inherit the parent model and do not form a recursive durable fleet. Record exclusive worktree, branch, allowed paths/actions, runtime cap, report path, and actual handle. Separately managed profile processes are optional dependencies, not assumed workers.
- [ ] **One-shot launch gate.** Before any profile-process launch here, load `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`. `-z` bypasses command and hook approval gates. Require explicit authorization for that bypass, review inherited hooks, and verify restricted execution boundaries, scoped credentials, and minimal toolsets. Model-diversity or unattended-work requests are not bypass authorization. Otherwise use bounded parent-driven delegates, an approval-preserving interactive session, or report blocked.
- [ ] Follow the dependency graph. Start after the parent merges or branch from the parent when the execution playbook stacks.
  - [ ] <PR id> and <PR id> are independent and first. Both branch from <actual trunk>.
  - [ ] <PR id> depends on <PR id>.
- [ ] Hold file boundaries. <PR id or class> writes only <allowed glob>, never <forbidden paths>.
- [ ] Hold review gates. <PR ids> change interactions and wait for operator screenshot/video review before merge.

### PR mechanics, for every PR

- [ ] Resolve the forge and authentication once through `terminal`. Default to `gh`; optional Origin needs installed-help and repo-resolution checks. Never require Graphite.
- [ ] Before any PR-facing publication, complete Opening a PR's mandatory parent-owned delegated-PR gate for every delegated PR. The code leaf returns implementation, cleanup, head/diff, and check receipts first. The parent then runs interrogate, verifies cleanup, and dispatches no-comments independently, with audit-only scope by default. No recursive reviewers in the code leaf. Apply accepted scoped fixes in bounded follow-up phases and rerun affected gates on the final snapshot. Missing independent review blocks publication.
- [ ] Open ready through the available inspected PR integration or selected forge per Opening a PR, only with publishing authority and the accepted gate. For GitHub use `terminal(command='gh pr create --base "<base>" --title "<title>" --body-file "<body-file>"', workdir='<repo>')` without a draft flag. A child targets its parent's branch. Read back exact base/head/readiness after every write.
- [ ] Run relevant formatter, lint, typecheck, and tests on the committed head before a PR-facing push. Push with hooks on and verify the remote head.
- [ ] Before each commit, remove boilerplate, unused imports, redundant guards, speculative abstractions, and narration comments without weakening gates. The parent owns the independent reviews above after the code leaf returns. No external cleanup plugin is mandatory.
- [ ] Triage every bot/security finding through `skill_view(name='poteto-mode', file_path='references/bugbot-triage.md')`. Replies/resolution require their own grant and exact-target readback.
- [ ] Let only the named topology owner rebase onto current trunk before code-ready when required. Fix rounds keep that base. Rebase again for merge preparation, an actual merge-result conflict, or verified trunk-caused check failure. Never overlap branch writers.

### Verdict and merge, for every PR

- [ ] At code-ready, run one full matrix from `skill_view(name='swarm')`. Include a gates lane, the ten named live lanes, the perf lane, and at least two independent audits of diff and receipts. Same-model lanes are the default. Use bounded coordinator dispatches, not recursive worker spawns. Run serially or in waves when capacity is lower. The root audits actual receipts before verdict.
- [ ] Clean requires all required lanes `PASS`. Return every proven defect to the owner, even if labeled a note. A blocked lane is not a pass. Rerun the full matrix only for new behavior/redesign/large diff; a minor fix or rebase gets a fresh targeted verifier and current CI. Carry results only with the patch-id and context proof from `skill_view(name='poteto-mode', file_path='playbooks/shipping.md')`.
- [ ] <Exact merge or append rule from the execution playbook, named operator gates, and Shipping's patch/context rule. Never treat green as merge authority.>
- [ ] For authorized GitHub landing only, bind the accepted current verdict to the fresh PR `headRefOid` and use `terminal(command='gh pr merge <pr> --squash --match-head-commit <verified-head-sha>', workdir='<repo>')` with that full verified SHA. On mismatch, stop and reverify, never update the pin without a verdict. Read the exact PR afterward for merged state, trunk base, and accepted head. No admin/protection bypass. In stack mode, record the operator handoff instead and do not invoke a merge.
- [ ] Do not arm auto-merge or enqueue landing. Inspect branch rules and pending landing state first; if the command would defer automatically, stop at merge-ready. A request-time pin and promised writer freeze do not enforce immutable head semantics. Queue-only landing stays blocked pending a separately approved service with immutable head semantics and continuously current verdicts.

### Boot recipe, for every live lane

Each lane uses an exclusive worktree at the exact PR head on a verified available backend, not an assumed cloud VM. Drive input through <actual repo driver or available Hermes browser/computer-use tools>. Name optional dependencies and test-only credentials before starting.

- [ ] Fetch and check out <exact head SHA> in <exclusive worktree> with `terminal`. Confirm the SHA before probing.
- [ ] <Start backend/surface with the exact terminal command, wait for named ready signal, and verify the endpoint.>
- [ ] <Deliver input through the named actual driver. Name read-only diagnostics and forbidden side effects.>
- [ ] Save screenshots under `$TMPDIR/swarm-<pr-id>/worker-<n>/<slug>.png`, then copy retained receipts to <approved durable media store>. Return both paths and actual commands/output. Stop owned servers after the lane unless explicitly handed off.

## <Task as a verb phrase> (<PR id>)

**Depends on.** <PR id, or None.>

**Files.**

- [ ] Edit `<path>`.
- [ ] Create `<path>`.
- [ ] Delete `<path only if authorized>`.

**Build.**

- [ ] <One change naming its symbol, data shape, and file.>

**You see.**

- [ ] <One observable result with the exact log line or screen state.>

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] <Test file and case.> Run <exact terminal command and expected failure/pass evidence>.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `<actual inherited parent model identity or configured profile model>` at the PR head, per the boot recipe. These are independent same-model lanes unless distinct configured models were actually used.

- [ ] Lane 1. Regression lane against trunk. Run <same load-bearing scenario> at trunk and head. If trunk lacks it, record that and gate <diff-added behavior and awaited end state>. Save `<slug>.png`. Pass when <predicate>.
- [ ] Lane 2. <Scenario.> Save `<slug>.png`. Pass when <predicate>.
- [ ] Lane 3. <Scenario.> Save `<slug>.png`. Pass when <predicate>.
- [ ] Lane 4. <Scenario.> Save `<slug>.png`. Pass when <predicate>.
- [ ] Lane 5. <Scenario.> Save `<slug>.png`. Pass when <predicate>.
- [ ] Lane 6. <Scenario.> Save `<slug>.png`. Pass when <predicate>.
- [ ] Lane 7. <Scenario.> Save `<slug>.png`. Pass when <predicate>.
- [ ] Lane 8. <Scenario.> Save `<slug>.png`. Pass when <predicate>.
- [ ] Lane 9. <Scenario.> Save `<slug>.png`. Pass when <predicate>.
- [ ] Lane 10. <Scenario.> Save `<slug>.png`. Pass when <predicate>.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. <Common metric emitted at both trunk and head. If trunk lacks the feature, also name added work and the awaited end state.>
- [ ] Probe. <Exact command/procedure at trunk and head, interleaved on matched workloads. Both sides produce the metric with errors/work counts.>
- [ ] Baseline. Record the actual trunk <value and unit> first.
- [ ] Rule. <Numerical failure threshold, noise check, and correctness gate. If scenarios differ, give absolute added-work/end-state budgets instead of an invalid ratio.>

**Review gate.** The operator reviews before merge.

- [ ] Copy lane <n> screenshots to `<media-path>/<pr-id>-review-<slug>.png`.
- [ ] Record a 30 to 60 second video using <actual driver/recorder>. Save `<media-path>/<pr-id>-review.mp4`.
- [ ] Show screenshots and video to the operator in the authorized chat, then stop at merge-ready. Wait for explicit review approval. No external message destination is implied.

**Merge.**

- [ ] Root's accepted clean verdict covers the exact head and relevant base context.
- [ ] Bot triage and any authorized reply/resolution readback are complete.
- [ ] Current-head CI and required reviews pass, and merge-result drift is verified under Shipping's patch/context rule.
- [ ] <Authorized lander follows the SHA-pinned immediate-merge checklist above with exact-target readback, or root appends the verified dependent link for the operator. Stop and reverify on drift. No deferred merge and no merge in stack mode.>

## Close the program

- [ ] Every required box is checked with existing evidence, or the program is explicitly reported blocked/incomplete rather than called done.
- [ ] Reconcile all worker/process handles and external effects. Stop watchers and disarm pending landing actions on hold when supported and authorized.
- [ ] Reply with the execution playbook's report and actual artifact links.

## Appendix A. Prototype evidence

<Each empirical question, branch/SHA when one exists, real artifact links, and what remains unproven.>

## Appendix B. Alternatives rejected

<Each approach weighed and why it lost.>

## Appendix C. Risks

<Each risk, owning PR, missing optional dependency, resource/lifetime limit, and what is watched.>

## Appendix D. Links and reading list

<Docs before editing. Which PRs load skill_view(name='how') and skill_view(name='interrogate'). Trail from skill_view(name='show-me-your-work'). Only links actually read or produced.>
````

**Reply:** plan path, PR ids/dependencies and review-gated set, prototype findings and limits, exact checker command/output, and any runtime or authorization gate. Stop after the plan.

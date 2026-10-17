# One-shot safety

Load this reference before choosing a one-shot profile process. It is a launch gate, not permission to launch.

## Approval semantics

The installed top-level `-z` / `--oneshot` path bypasses command and hook approval gates. Its runner unconditionally sets `HERMES_YOLO_MODE=1` and `HERMES_ACCEPT_HOOKS=1`. The CLI help also discloses automatic approval bypass. Configured command approvals and first-use shell-hook consent do not protect this path, even when the profile normally prompts.

No flag makes `-z` preserve approvals. Setting those environment variables to zero before launch does not override the runner. Do not invent a preserving flag, treat omission of `--yolo` as protection, or substitute another noninteractive mode without verifying its approval semantics. Check the installed help/source and the authoritative CLI reference at https://hermes-agent.nousresearch.com/docs/reference/cli-commands when the runtime changes.

## Preconditions for every launch

1. Obtain explicit authorization for that bypass of both command and hook approval gates for this task and scope. A request for model diversity, a provider-readiness check, or unattended work is not bypass authorization. Record the grant separately from the task, inference-cost, publication, and process-lifetime grants. If the grant is missing, do not launch.
2. Inspect the selected profile and review inherited hooks before execution. Use `hermes -p <profile> hooks list` through `terminal`, then read the actual configured hook commands/scripts and their dependencies without executing them. Check inherited environment, plugins, MCP tools, project rules, and profile-clone state for additional execution/access paths. Do not use hook `test` or `doctor` as a passive review because they can execute hooks. Stop for unreviewed or out-of-scope hooks. Removing or changing them needs its own authorization.
3. Verify appropriate restricted execution boundaries for the task's risk before running. A separate profile or worktree is not a security sandbox. Profiles separate Hermes state and worktrees separate repository writes; neither restricts host filesystem, network, or credential access. A no-write prompt is behavioral only. Use actual enforced filesystem/process/network boundaries where needed, and cover hooks plus every enabled file, terminal, plugin, and MCP path, not just the terminal backend. If those boundaries cannot be established, report blocked rather than implying isolation.
4. Use scoped credentials with least privilege and shortest useful lifetime. Do not inherit broad parent/source credentials merely because a clone can copy them. Remove access to unrelated repositories, messaging, production systems, and private state through an operator-approved runtime. Never print credentials or copy them into briefs, receipts, or this package.
5. Choose minimal toolsets from the installed tool catalog and verify their effective tools. Inspect current `--toolsets` help, resolve the exact names, and pass only the required sets with `-t` when supported. A toolset limit does not constrain a retained shell's own capabilities or hooks. Keep restricted execution boundaries and scoped credentials even for a read-only brief or a READY-only prompt. Do not add broad tools to make a smoke test pass.
6. Supply a bounded self-contained brief, exclusive write scope, time/cost limits, approved output path, stop conditions, and a tracked process handle. Keep lifecycle authority separate from approval-bypass authority. Verify the actual exit, artifacts, tool use, and runtime model/provider. Report incomplete or unverified work honestly.

## Fallback when a precondition is absent

Use bounded parent-driven `delegate_task` phases within the existing approved runtime, with independent reviewers dispatched by the parent. Delegation is not itself a sandbox or a way to evade the parent's gates. If actual model diversity is essential, use an approval-preserving interactive session whose command approvals and hook consent are verified active, without bypass settings or inherited bypass environment. Do not replace it with `chat -q` on an unverified assumption. If neither path can meet the requirement, report blocked. Never silently relax a gate to obtain diversity or unattended continuation.

## Evidence limits

A profile name, scratch workspace, restricted prompt, or successful fixture run does not prove an OS sandbox. Describe only the execution boundaries actually inspected. The recorded package smokes used a dedicated profile/workspace and bounded fixtures; their captured traces prove specific file/delegation behavior, not host isolation or a general safety guarantee.

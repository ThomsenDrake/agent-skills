---
name: poteto-help
description: "Use when choosing or learning pstack workflows."
compatibility: "Hermes skills_list and skill_view, file tools, and terminal for profile/config/skill-discovery checks."
---

# Poteto help

Answer the question about pstack, give at most one prompt the user can send, and cite the skill or reference the answer came from. A help request does not authorize a token-heavy run. If the user actually asked for work, load `skill_view(name="poteto-mode")` and do that work instead of handing back instructions.

Read the selected skill before recommending it. Its procedure owns the details. Use `skill_view(name="<slug>")`, `/skill <slug>` for explicit chat loading, and `skill_view(name="<slug>", file_path="<relative-reference>")` for supporting material. Loading a skill supplies instructions; it does not execute a workflow by itself.

## Find the need

Infer it from the conversation. If unclear, ask one short multiple-choice question: setup, start a task, choose a workflow, fix a drifting run, or personalize pstack. Check only the live state that changes the answer:

- Read the selected profile's `model.default`, `model.provider`, `agent.reasoning_overrides`, and `delegation` through `terminal(command="hermes -p <profile> config get <key>")` when setup or cost matters. No missing rule file can prove setup has not run.
- Find an existing `verify-*` skill or real-app harness before recommending `create-verification-skill`.
- Check `skills_list` or `terminal(command="hermes -p <profile> skills list")` for discovery. A source directory sitting in a checkout is not necessarily installed.

Offer `/skill setup-pstack` at most once per chat if model setup or budget is relevant. The default is independent delegates on the inherited parent model, not a hidden family-specific role list.

## Get set up

**One-shot launch gate.** Before any profile-process launch here, load `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`. `-z` bypasses command and hook approval gates. Require explicit authorization for that bypass, review inherited hooks, and verify restricted execution boundaries, scoped credentials, and minimal toolsets. Model-diversity or unattended-work requests are not bypass authorization. Otherwise use bounded parent-driven delegates, an approval-preserving interactive session, or report blocked.

1. Install the adapted `skills/pstack-hermes/` tree into the selected profile's skills directory using the repository's installation instructions. Resolve its actual home with `terminal(command="hermes -p <profile> config path")`. Do not copy into a different profile or the vendored upstream tree. `bots/README.md` documents profile-safe whole-tree installation and optional bot skeletons. Individual GitHub skill identifiers resolve the repository's default branch, so use them only after this adaptation is merged there; a local branch copy is the reliable pre-merge path.
2. Confirm discovery with the profile's `skills list`, then start a new session for a fresh catalog. Load `skill_view(name="setup-pstack")` if the user wants to select model/provider/reasoning. It writes native profile configuration and reads it back; it does not generate rules.
3. Start a task with `/skill poteto-mode` plus a goal and a check that can pass or fail. `terminal(command="hermes -p <profile> -s poteto-mode -z '<goal and done checks>'")` preloads it for a one-shot process when that is appropriate.

Installation exposes skills; invocation or preloading supplies their instructions to a task. Do not promise a permanently pinned custom editor mode. For each new task, explicitly load `poteto-mode` again when needed. A dedicated profile can put its standing identity in `SOUL.md`, but that is separate from loading the procedure.

If cost is the worry, explain that delegates, panels, and repeated app checks cost tokens. Use narrower scope and smaller worker counts. Rerun `setup-pstack` for a supported lower effort or a cheaper verified model. Never claim that an alias changes an individual delegate's model; aliases are session selection shortcuts.

## Start a task

Load `skill_view(name="poteto-help", file_path="references/prompting.md")` before wording a prompt. A good prompt names the goal, evidence, constraints, and a falsifiable done check, not a hand-written list of every skill. `poteto-mode` chooses a playbook and records the steps, including an explicit reason for each skipped step.

The coordinator owns the playbook and todo list. Ordinary `delegate_task(tasks=[{"goal": "<bounded job>", "context": "<scope and evidence contract>"}, ...])` calls inherit its model and need explicit scope and skill-loading instructions. They do not select an agent persona from a markdown filename. `bots/poteto-agent/SOUL.md` is an optional standalone profile skeleton, not a special delegate type.

## Pick a skill

Default to `poteto-mode` for non-trivial work. Recommend a narrower skill when the user deliberately wants more or less of its process. Load that skill before quoting its contract.

| The user wants to | Load with `skill_view(name=...)` or `/skill ...` |
|---|---|
| Do a non-trivial task with rigor | `poteto-mode` |
| Check the underlying goal before implementation | `in-your-own-words` |
| Raise the ambition without overspecifying the method | `sharpen` |
| Understand current mechanics or code placement | `how` |
| Recover design rationale or the source of a number | `why` |
| Learn how and why, plainly | `teach` |
| Rebuild context across recent work | `recall` |
| Catch up within this chat | `ketchup` |
| Prove what a diff could break elsewhere | `blast-radius` |
| Settle types and module boundaries in code | `architect` |
| Compare independent attempts at one brief | `arena` |
| Run checks over bounded parallel slices or a race | `swarm` |
| Review a diff skeptically | `interrogate` |
| Fix a bug test-first on a cheap local path | `tdd` |
| Apply TypeScript rules | `typescript-best-practices` |
| Remove unnecessary comments with independent review | `no-comments` |
| Remove AI prose habits | `unslop` |
| Write docs, an RFC, README, PR text, or commit message | `technical-writing` |
| Restate the last answer in plain words | `bro` |
| Create a real-app verification harness skill | `create-verification-skill` |
| Audit a verification skill and feature map | `maintain-verification-skill` |
| Vet a performance number | `benchmark-checklist` |
| Run a large or cross-cutting change rigorously | `figure-it-out` |
| Keep and independently audit a decision trail | `show-me-your-work` |
| Choose profile model/provider/reasoning | `setup-pstack` |
| Capture personal working conventions | `automate-me` |
| Turn completed work into durable skill corrections | `reflect` |
| Stop a repeat mistake in this repository | `correct` |
| Build a UI that calls a Hermes webhook safely | `make-bot-ui` |
| Find the right pstack workflow | `poteto-help` |

If a neighboring skill is absent from this table, read its frontmatter and route by its real trigger. Use `skills_list` to distinguish absent from disabled or undiscovered skills. Do not invent a capability from a name.

Close calls: `how` is mechanics, `why` is rationale, `teach` is the explanation. `arena` compares attempts on one brief; `swarm` divides a task. `interrogate` reviews the diff; `blast-radius` proves effects beyond it. `recall` spans recent sessions; `ketchup` covers this chat. `architect` proceeds into implementation unless its checkpoint contract says otherwise, so offer a checkpoint when the user wants to review the design first.

## Playbooks and principles

Playbooks are files under `poteto-mode`, not independent skills. Load the exact reference with `skill_view(name="poteto-mode", file_path="playbooks/<file>.md")`. “Babysit this PR,” “land the stack,” “take over this branch,” “pause safely,” “full autopilot,” and “run the eval playbook” select those workflows after loading `poteto-mode`. Babysitting stops at merge-ready unless merging was authorized. A multi-phase plan can be planning-only; read its file before assuming implementation is part of it.

Principles are `principle-*` skills loaded by name when their rule matters. Say the decision they changed, not merely the principle's title. There is no need to invent a separate planning or orchestrate skill when the matching playbook exists.

## Fix a run

| Symptom | Check or steer |
|---|---|
| The procedure faded after several turns | Reload `/skill poteto-mode`; do not promise an editor-only pinning shortcut. |
| A question was treated as more implementation | Say “new task” or explicitly request an explanation-only turn. |
| Config changes did not affect this chat | Read back the selected profile and resolver, then use a fresh session; session overrides can win. |
| A skill did not load | Check installation, project trust, name collision, enabled state, and catalog caching; load it explicitly. |
| Parallel writers collided | Assign disjoint paths or isolated worktrees, then have one coordinator integrate. |
| An unattended run kept moving without finishing | Supply a measurable finish predicate, bounded retries, a decision log, and a stop condition. No scheduler is created just for asking help. |
| A green build was treated as proof | Ask for the actual user flow, stored value, endpoint result, or profile readback. |

For personalization, load `automate-me`; for lessons after a run, load `reflect`; for a repeat failure, load `correct`. Preserve unrelated skill behavior and keep fixes in their own reviewable scope.

## Reply and verification

Lead with the answer. Give at most one task-specific prompt from `skill_view(name="poteto-help", file_path="references/recipes.md")`, then cite the loaded skill/reference. Use an existing local source path or a verified published URL, never a guessed upstream guide link. State missing tools or integrations rather than promising an unsupported shortcut. For help alone, finish without starting the suggested work.

---
name: pstack-hermes
description: "Use when installing or choosing Hermes pstack skills."
compatibility: "Hermes Agent with recursive skills discovery, skill_view and file tools. Workflows may also need terminal, delegation, Git, gh, Bun or browser tools."
version: 0.1.0
author: Lauren Tan (poteto), Drake Thomsen, Hermes Agent
license: MIT
---

# pstack for Hermes

The package contains 54 workflow and principle skills, this index, and two bot profile skeletons.
It adapts Lauren Tan's pstack v0.15.25 for Hermes Agent and Hermes bot profiles.
The vendored `skills/pstack/` tree remains unchanged. Its daily sync does not update this adaptation.

## What changed

**One-shot launch gate.** Before any profile-process launch here, load `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`. `-z` bypasses command and hook approval gates. Require explicit authorization for that bypass, review inherited hooks, and verify restricted execution boundaries, scoped credentials, and minimal toolsets. Model-diversity or unattended-work requests are not bypass authorization. Otherwise use bounded parent-driven delegates, an approval-preserving interactive session, or report blocked.

- Skills load by name through `skill_view(name="poteto-mode")` or `/skill poteto-mode`.
- References and playbooks load through `skill_view(name, file_path)`.
- Bounded parallel work uses `delegate_task(tasks=[...])`. Children inherit the parent model unless centrally configured otherwise.
- The default panel uses independent contexts on the same model. It does not claim cross-model agreement.
- Optional model diversity uses configured named profiles and `hermes -p <profile> -z` processes. Model aliases do not retarget delegates.
- `setup-pstack` writes Hermes configuration through the CLI and reads it back. Model IDs and reasoning levels are separate values.
- Bot agent definitions become `bots/poteto-agent/SOUL.md` and `bots/comment-sicko/SOUL.md`.
- Bun and Node helpers remain under `poteto-mode/scripts/`. Their Hermes invocations and limits are explicit. The editor-specific worktree audit is retained but skipped.
- Tools, authoring, session recovery, and verification use Hermes workflows instead of editor-only services.
- A skill cannot grant permission to send messages, merge, deploy, delete data, or expose credentials.

## Install into one profile

Do not install both pstack variants into the same profile. Their leaf names overlap.
Use an existing profile only when the user names it. Use a new test profile for experiments.
Keep secrets in `.env` or the credential store, never in this package.

### Current branch

Copy the complete adapted tree from the `pstack-hermes` branch.
Resolve the target with `hermes profile show <profile>`. Its `Path` is `<profile-home>`.
Replace every placeholder and quote the real paths before running these `terminal` calls.

```python
terminal(command="git clone --branch pstack-hermes --single-branch https://github.com/ThomsenDrake/agent-skills.git '<checkout>'")
terminal(command="hermes profile show <profile>")
terminal(command="cp -R '<checkout>/skills/pstack-hermes' '<profile-home>/skills/pstack-hermes'")
terminal(command="hermes -p <profile> skills list")
```

The destination must not already exist. Do not merge a new copy over a live install blindly.
Copy all 54 child directories, not just this `SKILL.md`.
Hermes recursively discovers the nested leaf skills. Start a new session after installation.

### After merge to the default branch

The repository identifier follows Hermes's default-branch installer format.
It is not a branch selector. Until this branch is merged, use the copy method above.

```python
terminal(command="hermes -p <profile> skills install ThomsenDrake/agent-skills/skills/pstack-hermes --yes")
terminal(command="hermes -p <profile> skills list")
```

Review the installer's security scan. Do not bypass a blocked result automatically.
If an older installer omits nested files, use the complete-tree copy and verify discovery.

## Get started

1. Load `setup-pstack` to inspect the target profile's model and choose a supported reasoning level. Configuration changes require the user's scope.
2. Load `poteto-mode` for an engineering task. It chooses the playbook and relevant leaf skills.
3. Load `poteto-help` when choosing a workflow.
4. Use `bots/README.md` to create a bot profile from a skeleton. Neither skeleton schedules routines or configures messaging.

```python
skill_view(name="setup-pstack")
skill_view(name="poteto-mode")
skill_view(name="poteto-help")
```

## Skill map

### Workflows and utilities

| Skill | Job |
| --- | --- |
| `architect` | Compare boundary and API designs before implementation. |
| `arena` | Generate competing artifacts, choose a base, and graft useful parts. |
| `automate-me` | Capture a user's working style in a personal mode skill. |
| `benchmark-checklist` | Check measurement validity before trusting a number. |
| `blast-radius` | Trace a change's callers, assumptions, and affected behavior. |
| `bro` | Restate the last reply in plain language. |
| `correct` | Prevent repeated agent mistakes through repository structure and checks. |
| `create-verification-skill` | Create a project-specific real-artifact verification workflow. |
| `figure-it-out` | Design a bespoke playbook for a cross-cutting task. |
| `how` | Explore how the system works before deciding. |
| `in-your-own-words` | Confirm the user's goals and the problem being solved. |
| `interrogate` | Challenge a design through independent adversarial roles. |
| `ketchup` | Recover the current task context from evidence. |
| `maintain-verification-skill` | Keep a project's verification workflow accurate. |
| `make-bot-ui` | Build a UI whose server triggers a bounded Hermes webhook. |
| `no-comments` | Remove comments the code already explains. |
| `poteto-help` | Choose a skill and shape an actionable prompt. |
| `poteto-mode` | Run verified engineering work through the matching playbook. |
| `recall` | Recover relevant prior decisions and lessons. |
| `reflect` | Review the work and extract concrete improvements. |
| `setup-pstack` | Configure a Hermes profile's model and reasoning. |
| `sharpen` | Frame a task precisely before starting work. |
| `show-me-your-work` | Keep a compact auditable decision and evidence trail. |
| `swarm` | Partition parallel coverage and verify worker reports. |
| `tdd` | Build behavior through red, green, and refactor checks. |
| `teach` | Explain a system or lesson from concrete evidence. |
| `technical-writing` | Write technical documents around decisions and reader needs. |
| `typescript-best-practices` | Choose clear TypeScript types and boundaries. |
| `unslop` | Remove filler and write precise declarative prose. |
| `why` | Investigate intent and rationale with source evidence. |

### Principles

The 24 principle skills each have their own trigger and procedure.

- `principle-attack-the-premise`
- `principle-boundary-discipline`
- `principle-build-the-lever`
- `principle-encode-lessons-in-structure`
- `principle-exhaust-the-design-space`
- `principle-experience-first`
- `principle-explain-the-number`
- `principle-fix-root-causes`
- `principle-foundational-thinking`
- `principle-guard-the-context-window`
- `principle-laziness-protocol`
- `principle-make-operations-idempotent`
- `principle-migrate-callers-then-delete-legacy-apis`
- `principle-minimize-reader-load`
- `principle-model-the-domain`
- `principle-never-block-on-the-human`
- `principle-outcome-oriented-execution`
- `principle-prove-it-works`
- `principle-redesign-from-first-principles`
- `principle-separate-before-serializing-shared-state`
- `principle-sequence-verifiable-units`
- `principle-subtract-before-you-add`
- `principle-test-behavior-not-implementation`
- `principle-type-system-discipline`

## Verification

Run `python -m unittest discover -s skills/pstack-hermes/tests -v` from the repo root with Hermes's Python environment. The tests use `ruamel.yaml`, which Hermes ships.
Run `terminal(command="bun run test", workdir="<poteto-mode-skill-dir>/scripts")` for the retained helpers.
Confirm all 55 entries, including this index, in the test profile's skill catalog.
A one-shot test must call `skill_view`, follow the selected skill, and leave real output to inspect.
Do not use a preload alone as proof of a tool call.
Recorded checks and known limits live in `references/verification.md`.

## Provenance

Source collection https://github.com/cursor/plugins/tree/main/pstack.
Source version v0.15.25, as vendored at agent-skills commit `4150dd0f96115204d4527f7a1adf88c90bc2d9eb`.
The adaptation is maintained separately. Re-adapt future upstream changes deliberately and rerun verification.
See `LICENSE` for Lauren Tan's MIT notice.

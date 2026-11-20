---
name: pstack
description: "Index and entry point for pstack, poteto's rigorous engineering workflows (architect, arena, swarm, poteto-mode, tdd, why, how, unslop, reflect, recall, teach, statechart and the principle-* skills), adapted so any coding agent can run them. Use it to find the right pstack skill and to map pstack's agent-neutral wording onto your agent's tools. Start with setup-pstack to pick models, then use poteto-mode for rigorous engineering work."
license: MIT
compatibility: Any agent that can read files and run a shell. The workflow skills (poteto-mode, arena, swarm, interrogate, how) expect subagents. Git and gh for the PR playbooks; Bun for the optional scripts. make-bot-ui alone needs Cursor Automations.
metadata:
  author: "Lauren Tan (poteto); agent-neutral adaptation by ThomsenDrake"
  upstream: "https://github.com/cursor/plugins/tree/main/pstack"
---

# pstack

An agent-neutral adaptation of [cursor/plugins pstack](https://github.com/cursor/plugins/tree/main/pstack) by Lauren Tan (MIT). This copy follows upstream pstack v0.15.46 at commit aaeb0ea.

> "if you want to go fast, go deep first. pstack helps you write less, but higher quality code. rigorous agent workflows you can parallelize with confidence."

## What's here

| Path | Contents |
| --- | --- |
| `<skill>/SKILL.md` | Each folder with a `SKILL.md` is a standalone skill. Run one by name, as `/<skill>` or however your agent invokes skills |
| `agents/poteto-agent.md` | Brief for the delegate subagents that poteto-mode spawns |
| `agents/comment-sicko.md` | Brief for the comment-removing reviewer that no-comments spawns |
| `UPSTREAM.json` | The upstream commit and version this copy matches |

## Get started

1. `setup-pstack`: pick a reasoning budget and a model per role. It writes `~/.config/pstack/pstack-models.md`.
2. `poteto-mode`: the main entry point. It reads your request, picks a playbook and runs the other skills as needed.
3. `poteto-help`: when you're unsure which skill fits.

## Running pstack in your agent

The skills describe capabilities, not one agent's tools. Map each phrase to what your agent has. When your agent lacks a capability that a step needs, skip that part, say so in one line, and go on.

| pstack says | Cursor | Claude Code |
| --- | --- | --- |
| spawn a subagent | `Task` | `Agent` |
| a general-purpose subagent | `subagent_type: generalPurpose` | `subagent_type: "general-purpose"` |
| a `poteto-agent` or `comment-sicko` subagent | `subagent_type: "poteto-agent"` where the agents are installed, as upstream's plugin does; otherwise a general-purpose subagent whose prompt starts with the file's body | install `agents/*.md` in `~/.claude/agents/` and use the name as `subagent_type`, or start a general-purpose subagent's prompt with the file's body |
| read-only subagent | `readonly: true` | `subagent_type: "Explore"`, and the brief says not to edit files |
| in the background | `run_in_background: true` | the default |
| its own isolated workspace | `environment: "cloud"` | `isolation: "worktree"` |
| ask the user, as a multiple-choice question | `AskQuestion` | `AskUserQuestion` |
| your todo list | the todo list tool | `TodoWrite` |
| a model value `<model> <effort>`, such as `claude-opus-5-5 xhigh` | the slug for that model and effort, such as `claude-opus-5-5-xhigh-fast`. Opus 5.5 runs its `-fast` slugs; Fable and Gemini have none | `model: "opus"`, `effort: "xhigh"`. For a model outside Claude, omit `model` and say so |
| the pstack models file | `~/.config/pstack/pstack-models.md` | `~/.config/pstack/pstack-models.md` |
| the project or user skills folder | `.cursor/skills/`, `~/.cursor/skills/` | `.claude/skills/`, `~/.claude/skills/` |
| your agent's always-loaded instructions | `.cursor/rules/`, `AGENTS.md` | `CLAUDE.md` |
| this workspace's session transcripts | `~/.cursor/projects/<slug>/agent-transcripts/` | `~/.claude/projects/<slug>/*.jsonl` |
| a cloud or remote worker | cloud agents | none: use a worktree |
| your agent's loop or scheduled wake-up command | `/loop` | `/loop` |
| your agent's plan mode | Plan Mode | plan mode |
| your agent's persistent mode | a Custom Mode | none: start each task with `/poteto-mode` |

## Skill map

- **Design first:** `architect`, `arena`, `why`, `how`, `figure-it-out`, `interrogate`, `statechart`
- **Ship it:** `poteto-mode`, `swarm`, `tdd`, `blast-radius`, `correct`, `sharpen`, `automate-me`, `ketchup`, `ketchup-video`, `bro`
- **Quality bar:** `unslop`, `no-comments`, `technical-writing`, `typescript-best-practices`, `in-your-own-words`, `show-me-your-work`, `benchmark-checklist`
- **Review loop:** `reflect`, `recall`, `teach`
- **Principles:** the `principle-*` skills, such as subtract-before-you-add, prove-it-works, fix-root-causes and guard-the-context-window
- **Meta:** `setup-pstack`, `poteto-help`, `create-verification-skill`, `maintain-verification-skill`, `create-formal-verification-skill`, `maintain-formal-verification-skill`, `make-bot-ui`

## Provenance

Upstream writes pstack for Cursor. This copy keeps upstream's skills and rewrites only the wording that ties them to one agent, by the rules in [NEUTRALIZE.md](https://github.com/ThomsenDrake/agent-skills/blob/main/scripts/pstack/NEUTRALIZE.md). Every `SKILL.md` follows the [Agent Skills specification](https://agentskills.io/specification): fields outside it, such as upstream's `disable-model-invocation`, are kept under `metadata`. Upstream's plugin manifests, guide, automations and assets are not included. Skills link to the guide on GitHub.

A daily GitHub Actions job carries each upstream change over. Changes that merge cleanly land on their own. New Cursor-specific text is rewritten by Mistral Large 4 and checked before it lands. Anything that fails a check waits in a pull request for review.

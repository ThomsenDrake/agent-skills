---
name: pstack
description: "Upstream pstack meta-skill (Lauren Tan / poteto, v0.15.25, MIT). 'If you want to go fast, go deep first' — rigorous agent workflows you can parallelize with confidence. This is the index and entry point; the 54 real skills live in subdirectories (architect, arena, swarm, poteto-mode, tdd, why, how, unslop, reflect, recall, teach, poteto-help, setup-pstack, blast-radius, and 31 principle-* skills). Start with setup-pstack to configure models, then use poteto-mode for rigorous engineering work. Agent definitions are in agents/."
compatibility: Skills reference Cursor harness paths (~/.cursor/plugins, Task tool, /commands). On Hermes, path lookups fall back to this repo's skills/pstack/ tree. setup-pstack writes model config — review before applying. poteto-mode scripts under scripts/ are TypeScript/bun and optional.
---

# pstack

Forked from https://github.com/cursor/plugins/tree/main/pstack (v0.15.26, MIT, Lauren Tan).

> "if you want to go fast, go deep first. pstack helps you write less, but higher quality code. rigorous agent workflows you can parallelize with confidence."

## What's here

| Path | Contents |
| --- | --- |
| `architect/` … `why/` | 54 standalone skills, each with its own SKILL.md |
| `agents/poteto-agent.md` | Subagent definition spawned during poteto-mode runs |
| `agents/comment-sicko.md` | Reviewer agent definition |

## Get started

1. `setup-pstack/` — pick a reasoning budget and per-role models.
2. `poteto-mode/` — the main entry point. Reads your request, picks a playbook, runs the other skills as needed. 23 playbooks included.
3. `poteto-help/` — if you're unsure which skill fits.

## Skill map

- **Design first:** `architect`, `arena`, `why`, `how`, `figure-it-out`, `interrogate`
- **Ship it:** `poteto-mode`, `swarm`, `tdd`, `blast-radius`, `correct`, `sharpen`, `automate-me`, `ketchup`, `bro`
- **Quality bar:** `unslop`, `no-comments`, `technical-writing`, `typescript-best-practices`, `in-your-own-words`, `show-me-your-work`, `benchmark-checklist`
- **Review loop:** `reflect`, `recall`, `teach`
- **Principles:** 31 `principle-*` skills (subtract-before-you-add, prove-it-works, fix-root-causes, guard-the-context-window, …)
- **Meta:** `setup-pstack`, `poteto-help`, `create-verification-skill`, `maintain-verification-skill`, `make-bot-ui`

## Provenance

Copied verbatim from `cursor/plugins` @ main, plugin version 0.15.25. Agent definitions included; plugin.json, automations, docs, and assets from upstream are not part of this skill port.

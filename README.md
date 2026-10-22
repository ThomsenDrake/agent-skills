# Agent Skills

A growing collection of reusable, agent-neutral skills I build and maintain for extending AI agents with specialized knowledge and reliable workflows.

Each skill is self-contained and follows the [Agent Skills open standard](https://agentskills.io/), so it can be used by compatible agents without depending on one vendor or runtime.

## Available skills

| Skill | Description |
| --- | --- |
| [`using-omi-api`](./skills/using-omi-api/) | Comprehensive guidance for using Omi across Developer REST, Integration and OAuth, webhooks, MCP, and `omi-cli`, including authentication boundaries, safety, reliability, and known documentation gaps. |
| [`pstack`](./skills/pstack/) | Fork of [cursor/plugins pstack](https://github.com/cursor/plugins/tree/main/pstack) v0.15.30 (MIT, Lauren Tan). 54 skills for rigorous, parallelizable engineering workflows: `poteto-mode` entry point, `architect`/`arena`/`swarm` design and orchestration, `tdd`, `unslop`, 31 `principle-*` skills, and more. Start with `setup-pstack`, then `poteto-mode`. |
| [`pstack-hermes`](./skills/pstack-hermes/) | Hermes-native adaptation of pstack v0.15.25. The same 54 skills, with Hermes delegation, profile configuration, bot skeletons, and retained Bun helpers. Start with `setup-pstack`, then `poteto-mode`. |

Omi is the first skill in this collection. Additional skills will be added as they are developed and reviewed.

## Using a skill

1. Select the skill directory you need from `skills/`.
2. Review its `SKILL.md`, compatibility requirements, and referenced resources.
3. Install or copy the complete directory using the skill-loading mechanism supported by your agent.
4. Supply credentials through an approved secret store or runtime injection, never by embedding them in the skill.

Installation paths and commands vary by agent. This repository intentionally does not assume a specific client.

## Repository structure

```text
skills/
└── <skill-name>/
    ├── SKILL.md       # Required metadata and instructions
    ├── references/    # Optional supporting documentation
    ├── scripts/       # Optional executable helpers
    └── assets/        # Optional templates and static resources
```

`skills/pstack/` is a vendored fork: a meta `SKILL.md` index plus the 54 upstream skills as subdirectories, and agent definitions under `skills/pstack/agents/`.

## Standards

Skills in this repository should:

- Follow the [Agent Skills specification](https://agentskills.io/specification).
- Remain agent-neutral unless a platform constraint is intrinsic to the skill.
- Use progressive disclosure, keeping `SKILL.md` focused and routing detail into references.
- Prefer official, current sources and document known gaps or ambiguities.
- Define credential boundaries, least-privilege defaults, confirmation requirements, and safe failure behavior where applicable.
- Pass `skills-ref validate <skill-directory>` before release.

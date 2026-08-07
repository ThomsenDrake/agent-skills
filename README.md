# Agent Skills

A growing collection of reusable, agent-neutral skills I build and maintain for extending AI agents with specialized knowledge and reliable workflows.

Each skill is self-contained and follows the [Agent Skills open standard](https://agentskills.io/), so it can be used by compatible agents without depending on one vendor or runtime.

## Available skills

| Skill | Description |
| --- | --- |
| [`using-omi-api`](./using-omi-api/) | Comprehensive guidance for using Omi across Developer REST, Integration and OAuth, webhooks, MCP, and `omi-cli`, including authentication boundaries, safety, reliability, and known documentation gaps. |

Omi is the first skill in this collection. Additional skills will be added as they are developed and reviewed.

## Using a skill

1. Select the skill directory you need.
2. Review its `SKILL.md`, compatibility requirements, and referenced resources.
3. Install or copy the complete directory using the skill-loading mechanism supported by your agent.
4. Supply credentials through an approved secret store or runtime injection, never by embedding them in the skill.

Installation paths and commands vary by agent. This repository intentionally does not assume a specific client.

## Repository structure

```text
<skill-name>/
├── SKILL.md       # Required metadata and instructions
├── references/    # Optional supporting documentation
├── scripts/       # Optional executable helpers
└── assets/        # Optional templates and static resources
```

## Standards

Skills in this repository should:

- Follow the [Agent Skills specification](https://agentskills.io/specification).
- Remain agent-neutral unless a platform constraint is intrinsic to the skill.
- Use progressive disclosure, keeping `SKILL.md` focused and routing detail into references.
- Prefer official, current sources and document known gaps or ambiguities.
- Define credential boundaries, least-privilege defaults, confirmation requirements, and safe failure behavior where applicable.
- Pass `skills-ref validate <skill-directory>` before release.

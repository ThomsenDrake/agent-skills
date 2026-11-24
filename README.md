# Agent Skills

A growing collection of reusable, agent-neutral skills I build and maintain for extending AI agents with specialized knowledge and reliable workflows.

Each skill is self-contained and follows the [Agent Skills open standard](https://agentskills.io/), so it can be used by compatible agents without depending on one vendor or runtime.

## Available skills

| Skill | Description |
| --- | --- |
| [`using-omi-api`](./skills/using-omi-api/) | Comprehensive guidance for using Omi across Developer REST, Integration and OAuth, webhooks, MCP, and `omi-cli`, including authentication boundaries, safety, reliability, and known documentation gaps. |
| [`pstack`](./skills/pstack/) | Agent-neutral adaptation of [cursor/plugins pstack](https://github.com/cursor/plugins/tree/main/pstack) v0.15.48 (MIT, Lauren Tan), kept in sync daily. Rigorous, parallelizable engineering workflows: the `poteto-mode` entry point, `architect`/`arena`/`swarm` design and orchestration, `tdd`, `unslop`, the `principle-*` skills, and more. Start with `setup-pstack`, then `poteto-mode`. |
| [`no-slop-grenade`](./skills/no-slop-grenade/) | Sizes and shapes anything written for other people, such as messages, emails, requests, announcements, docs, slides, forms, PR descriptions and status updates, so it isn't a [slop grenade](https://noslopgrenade.com/). Calibrated on real rewrites and the sender's edits to them: cut to what the reader needs, keep every fact, condition and real uncertainty, and add nothing the sender didn't say. |

Omi is the first skill in this collection. Additional skills will be added as they are developed and reviewed.

## Using a skill

1. Select the skill directory you need from `skills/`.
2. Review its `SKILL.md`, compatibility requirements, and referenced resources.
3. Install or copy the complete directory using the skill-loading mechanism supported by your agent.
4. Supply credentials through an approved secret store or runtime injection, never by embedding them in the skill.

Installation paths and commands vary by agent. This repository intentionally does not assume a specific client.

## Automatic pstack updates

`.github/workflows/update-pstack.yml` runs daily at 14:00 UTC and on manual dispatch. It compares upstream pstack with the commit in `skills/pstack/UPSTREAM.json` and carries each change into the agent-neutral copy:

- An upstream change that merges cleanly and adds no Cursor-specific text is applied as is.
- Anything else goes to Mistral Large 4 with the rewrite rules in [`scripts/pstack/NEUTRALIZE.md`](./scripts/pstack/NEUTRALIZE.md). Upstream's own list of Cursor terms is read on every run, so new terms are caught too.
- The result must pass the checks: the Agent Skills spec, no new Cursor-specific lines, no conflict markers, no broken links.

When everything passes, the update is pushed to `main`. When anything fails, the update goes to one PR from `automation/pstack-update` that lists what needs review. Merging it advances the checkpoint. The build job holds the `MISTRAL_API_KEY` secret and only read access. A separate publish job, without the key, reruns the checks and holds write access.

Run it by hand, or check an update without publishing it:

```bash
gh workflow run update-pstack.yml
gh workflow run update-pstack.yml -f dry_run=true
```

## Repository structure

```text
skills/
└── <skill-name>/
    ├── SKILL.md       # Required metadata and instructions
    ├── references/    # Optional supporting documentation
    ├── scripts/       # Optional executable helpers
    └── assets/        # Optional templates and static resources
```

`skills/pstack/` is an agent-neutral adaptation of upstream pstack: an index `SKILL.md` that maps pstack's wording to specific agents, upstream's skills as subdirectories, and subagent briefs under `skills/pstack/agents/`. `scripts/pstack/` keeps it in sync.

## Standards

Skills in this repository should:

- Follow the [Agent Skills specification](https://agentskills.io/specification).
- Remain agent-neutral unless a platform constraint is intrinsic to the skill.
- Use progressive disclosure, keeping `SKILL.md` focused and routing detail into references.
- Prefer official, current sources and document known gaps or ambiguities.
- Define credential boundaries, least-privilege defaults, confirmation requirements, and safe failure behavior where applicable.
- Pass `skills-ref validate <skill-directory>` before release.

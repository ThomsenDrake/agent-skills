---
name: automate-me
description: "Use when capturing a user's working style in a skill."
compatibility: "Hermes skills_list, skill_view, skill_manage, file tools, and optional profile-scoped session_search or session export."
---

# Automate me

Turn the user's working conventions into one personal `<handle>-mode` skill. Mine evidence, ask what changed, draft operational rules, and apply `skill_view(name="unslop")`. Do not copy another person's preferences.

## 0. Find the existing mode

Use `skills_list` and inspect likely matches with `skill_view(name="<handle>-mode")`. Check the current project's trusted `.hermes/skills/` and the active profile's skills directory using `search_files`, including category directories. Resolve the chosen profile with `terminal(command="hermes -p <profile> config path")`; do not scan every profile on the machine.

An update is the default for repeat runs. Ask whether to update or start fresh only when intent is unclear. Preserve its category and sections the user has not contradicted. New evidence revises rules; genuinely new rules may earn a new section. For an update, bound history by the last edit or prior review checkpoint. Use repository history through `terminal` when versioned, otherwise file modification time or an explicitly recorded checkpoint. Say when that boundary is approximate.

## 1. Mine scoped history

Pin the profile, project, and time range before reading history. Start with this conversation. For additional evidence, use the enabled `session_search` tool and inspect returned session metadata for the right project before reading it. Do not search another profile without permission.

For a large corpus, discover session IDs first and split only those IDs among `delegate_task(tasks=[{"goal": "Mine recurring working preferences", "context": "<profile, project, session IDs, time window, signals, and evidence schema>"}, ...])`. Delegates inherit the parent model; there are no per-call model, reasoning, or speed knobs. Keep full history in the delegates and return short findings with session/message pointers. If delegation is unavailable, inspect the slices serially.

If session tools are unavailable, use `terminal(command="hermes -p <profile> sessions list --workspace <repo-root> --limit <limit>")`, then export only selected IDs with `terminal(command="hermes -p <profile> sessions export --session-id <id> --format jsonl --redact <scratch>/history.jsonl")` and read that file. An index limit is not full coverage. Expand discovery if the promised time window exceeds it. Use scratch under `$TMPDIR`, never a public upload. Do not read raw history across unrelated projects or assume a transcript directory layout.

Hunt for:

- Response length, tone, formatting, and corrections.
- Autonomy, delegation, and parallelism preferences.
- What counts as done, including real-app verification and review.
- Code and prose rules, linting, and type discipline.
- Worktrees, commits, PRs, and publishing boundaries.
- Skill-authoring and maintenance habits.

Cross-check across slices. Recurrence in two or more slices is strong evidence. A lone signal is weak unless the user explicitly confirms it. Record contradictions instead of hiding them. If history cannot be retrieved, ask directly and label the result interview-based.

## 2. Ask about intent

Mining misses preferences that have not come up. Ask one or two compact questions with four to six concrete options each, permitting multiple selections in the wording. Use an available clarification tool or plain chat, not a harness-specific dialog. Ask what changed for an update, not a full intake. Finish with one free-form invitation for missing rules. Do not send twenty questions.

## 3. Cluster the rules

Use only sections with real non-default rules: Response style, Autonomy, Understand first, Delegation, Code and prose, Review and verify, Process, Skills. Load `skill_view(name="poteto-mode")` for granularity, not content to copy. Refer to other installed skills by name with `skill_view`; do not paste their procedures or private paths.

Each rule says what to do and why it changes a decision. Use “the user” in imperatives. Skip generic advice such as “communicate clearly,” symmetrical section padding, metaphors, and rules supported by only one ambiguous exchange.

## 4. Draft and install

Use Hermes-native authoring. First read the selected profile's `skills.create_dir` with `config get`; it can redirect creation to a shared directory. Confirm that destination before using `skill_manage`, rather than assuming every create is profile-local:

- For a personal skill, use `skill_manage` in the active profile: `operations=[{"action": "create", "name": "<handle>-mode", "content": "<full SKILL.md>"}]`. Update an existing skill with targeted `action="patch"` operations after loading it.
- For a shared, versioned project skill, use `write_file` or `patch` at `.hermes/skills/<existing-category>/<handle>-mode/SKILL.md`. Preserve an existing layout. Project discovery requires explicit trust, reviewed through `hermes -p <profile> skills trust <repo-root>`; never silently grant it.
- If a different profile is the intended target, do not use this session's `skill_manage`. Resolve that profile first and use its file paths explicitly after confirming scope.

Frontmatter has `name` equal to the directory slug, a self-contained `Use when ... .` description of at most 57 characters, and `compatibility` naming Hermes and any actual dependencies. Trigger on the person's chosen handle or “work in their style,” not generic coding tasks. Do not add unsupported invocation flags or turn a personal mode into an always-on global rule.

## 5. Iterate, verify, and land

Apply `skill_view(name="unslop")` to every line, show the draft, and accept feedback. The quality check is the user's judgment: does it read like them, and does it change future behavior? A synthetic task benchmark does not measure a personal working style.

Parse the YAML, check the trigger, and verify discovery and `skill_view(name="<handle>-mode")` in a new session for the selected profile/project. The current catalog may be cached. Explain that the user can load it with `/skill <handle>-mode`; installation alone does not promise it applies on every turn.

For versioned work, use the repository's worktree and PR conventions when authorized. Never push directly to the default branch. For a personal skill, do not create a repository or public PR just to “land” it. Do not publish private history, evidence exports, or secrets with the skill.

## When not to use

A task-specific procedure or narrow convention is a regular Hermes skill, not a whole personal mode. Author it directly with `skill_manage` or the repository's skill-authoring workflow. Run trigger tuning only if actual discovery has failed, not as ceremony.

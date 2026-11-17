# Agent-neutral pstack: rewrite rules

`skills/pstack` adapts [cursor/plugins pstack](https://github.com/cursor/plugins/tree/main/pstack) so that any agent with the matching capabilities can follow it. Upstream writes for Cursor. This file says how to turn Cursor-specific wording into agent-neutral wording. People and models editing `skills/pstack` both follow it.

## Principles

1. **Keep upstream's meaning.** Keep every step, order, number, default, condition, example, link and safety rule. Change only the words that tie an instruction to one agent product.
2. **Name the capability, not the product.** Say what the agent must do, such as "spawn a subagent" or "ask the user". Where an agent may lack the capability, give the fallback once, at the point where the instruction applies.
3. **Add nothing and remove nothing else.** Don't add rules, gates, features or commentary that upstream doesn't have. The only allowed deletions are statements about Cursor's own catalog or UI that have no neutral meaning, such as which models have a `-fast` slug.
4. **Match the house style.** Short declarative sentences. Same headings, lists, tables, code blocks and links as upstream. A neutral phrase should be about as long as the Cursor phrase it replaces. Don't define the vocabulary inline in every file. The pstack index (`skills/pstack/SKILL.md`) has the per-agent table.
5. **Frontmatter.** The sync script sets a skill's `name` to its folder name and moves fields outside the Agent Skills spec under `metadata`, in skills and in the `agents/` briefs. Edit only the wording of `description` or `compatibility`, and a model value under `metadata`, and only to neutralize them. Agents treat `disable-model-invocation` differently once it sits under `metadata`, so a sentence that relies on it says what the skill is meant to do, such as "Only `/setup-pstack` is meant to load from the user's words."
6. **Never introduce another agent's names.** No Hermes, Claude Code, Codex or other product tool names, paths or commands in the skills. The index is the one place that maps the neutral words to specific agents.

## Vocabulary

### Tools

| Upstream (Cursor) | Neutral |
| --- | --- |
| `Task`, a Task subagent, a Task call | a subagent; spawn a subagent |
| Task `model` | the subagent's model |
| `AskQuestion` | ask the user, as a multiple-choice question when your agent supports one |
| the todolist tool | your todo list (your agent's todo tool if it has one, otherwise a checklist in your reply) |

### Subagent fields

| Upstream (Cursor) | Neutral |
| --- | --- |
| `subagent_type: generalPurpose` | a general-purpose subagent |
| `subagent_type: "poteto-agent"`, `"comment-sicko"` | a `poteto-agent` (or `comment-sicko`) subagent. Its brief is `agents/<name>.md` at the pstack root. Use it as the subagent type when your agent has it installed, otherwise start the subagent's prompt with that file's body |
| `readonly: true` | read-only: the brief says not to edit files, and you use your agent's read-only mode if it has one |
| agent mode, "readonly strips MCP" | not read-only, so it keeps the session's tools, MCP included |
| `environment: "cloud"` | in its own isolated workspace: a cloud or remote worker if your agent has them, otherwise its own git worktree |
| `environment: "local"` | in the local checkout |
| `cloud_base_branch: <b>` | tell the worker to start from branch `<b>` |
| `run_in_background: true` | in the background |
| `resume` | continue the same subagent if your agent can; otherwise spawn a new one with the earlier result in its brief |
| `file_attachments` | list the paths in the brief |
| a Project worker | a separate agent session |

### Models

- A Cursor slug `claude-<family>-<version>-<effort>[-fast]` becomes the vendor model ID and the effort as two tokens, `<model> <effort>`. Drop `-fast`. So `claude-opus-5-5-xhigh-fast` becomes `claude-opus-5-5 xhigh`, `claude-fable-5-2-high` becomes `claude-fable-5-2 high`, and `gemini-4-carbon-high` becomes `gemini-4-carbon high`.
- "slug" becomes "model" or "model ID". "The effort token is the last token, or the one before a trailing `fast`" becomes "the effort is the last token".
- Delete statements that only describe Cursor's slug catalog, such as "Opus 5.5 always runs its `-fast` slug" or "Fable has no fast slug".
- Keep `inherit-parent` and `auto` as pstack values. Both mean the role runs on the parent session's model, so the subagent's model is omitted.
- "The Task tool rejects a slug" becomes "your agent rejects a model".
- Where a skill first tells the agent to pick a model for a subagent, add the fallback once: if your agent can't choose a model per subagent, run it on the session model and say so.

### The models file

- `~/.cursor/rules/pstack-models.mdc`, "an always-applied rule", becomes `~/.config/pstack/pstack-models.md`, "the pstack models file".
- It is not loaded automatically. A skill that needs a role's line reads the file. A missing file or line means the skill default.
- The file has no frontmatter, so drop the `alwaysApply` and `description` lines from its shape. Its comment lines, `# defaults` line, `# budget` line and role lines stay.
- "It applies to new sessions" becomes "skills read it the next time they need a role".

### Paths and installs

| Upstream (Cursor) | Neutral |
| --- | --- |
| `.cursor/skills/`, `~/.cursor/skills/` | the project's skills folder, the user's skills folder (wherever your agent loads skills from). In paths write `<project skills>/` or `<user skills>/` |
| `~/.cursor/plugins/`, `.cursor-plugin/plugin.json`, `plugins/cache/` | where pstack is installed; an installed or cached copy |
| `.cursor/rules/*.mdc`, always-applied rules | your agent's always-loaded instructions, such as `AGENTS.md` |
| `~/.cursor/projects/<slug>/agent-transcripts/...` | this workspace's session transcripts, where your agent stores them. Keep upstream's rule never to read other workspaces' transcripts. Where a skill parses transcripts, describe the content (user turns, assistant turns, tool calls) and say that formats vary by agent |
| "the system prompt names the path" | if your agent gives you the path, use it |
| `https://github.com/cursor/plugins/...` links | keep them. They are attribution and upstream docs |
| `https://github.com/cursor/plugins/blob/main/pstack/` followed by a file's path, as the public copy of an installed file | `https://github.com/ThomsenDrake/agent-skills/blob/main/skills/pstack/` followed by its path inside the pstack folder |

### Platform features

| Upstream (Cursor) | Neutral |
| --- | --- |
| Cursor's `/loop` command | your agent's loop or scheduled wake-up command, if it has one |
| Cursor Automations, routines, `update_state`, `api2.cursor.sh` webhooks, `SendToUser` | intrinsic to the `make-bot-ui` skill, which stays Cursor-specific and says so in `compatibility`. Elsewhere: a scheduled automation, if your setup has one |
| cloud agents | cloud or remote workers, if your agent has them, otherwise separate worktrees |
| the built-in PR tool | the forge command the step gives, such as `gh pr create` |
| Bugbot | keep it. It is a GitHub review bot, and its comments are ordinary PR threads |
| Cursor's built-in `create-skill` skill | your agent's skill-authoring guidance, if it has any, and the [Agent Skills specification](https://agentskills.io/specification) |
| Cursor's built-in skill with the same name (such as babysit) | another skill with a similar name |
| Custom Modes | your agent's persistent mode, if it has one |
| Plan Mode | your agent's plan mode, if it has one |
| the Agents Window | drop the sentence if it only points at the product feature |
| "Cursor" as the product the user runs | your agent |
| How pstack installs in Cursor or Claude Code | This copy is agent-neutral: put the `pstack` folder where your agent loads skills. Cursor and Claude Code users can also install upstream's native plugin from cursor/plugins |

### Leave these alone

- `/name` skill commands. They mean "run the skill called name".
- Shell commands (`git`, `gh`, `bun`, `rg`) and script behavior. In a script that hardcodes one agent's path, accept an environment-variable override and keep the old path as one of the defaults. A script may also check other agents' known default locations.
- Package names such as `@cursor-skill/...`, and other uses of the word "cursor" that don't mean the product, such as a GraphQL `endCursor` or a text cursor.
- The `poteto-agent`, `comment-sicko`, `inherit-parent`, `auto` and Bugbot names.

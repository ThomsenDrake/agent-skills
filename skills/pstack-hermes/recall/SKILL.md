---
name: recall
description: "Use when rebuilding context across recent work."
compatibility: "Hermes session_search or profile-scoped session exports, file and terminal tools, optional delegate_task and shared-source integrations."
---

# Recall

Before starting or resuming work, rebuild the user's recent context and hand back a tight current-state brief. Read only what the in-scope threads need, then stop. This is context gathering, not authorization to implement or publish.

Two records matter. Hermes history holds what the user did and decided. The shared record holds user reports, incidents, reverted fixes, and current errors around the same code. Load `skill_view(name="why")` for its source-investigation procedures, but ask about current state rather than only design rationale.

## Procedure

1. **Classify.** A single chat to resume belongs to the `poteto-mode` Session pickup playbook, loaded with `skill_view(name="poteto-mode", file_path="playbooks/session-pickup.md")`. Durable working habits belong to `skill_view(name="automate-me")`. A catch-up within this chat belongs to `skill_view(name="ketchup")`. If the user supplied a complete state capsule, use it rather than mining again.
2. **Lock scope.** Pin the profile, workspace, topic, and time window. “Recent” defaults to the last seven days; state the assumed range and obtain timestamps through `terminal`, not memory. Never quietly turn “all” into the first N sessions or cross into another project/profile without permission.
3. **Discover before reading.** Use the enabled `session_search` tool for topic and time discovery, then validate each candidate's workspace and source. Use returned session IDs/message anchors to read relevant regions. Skip the current chat and obvious test, eval, tool, or child-agent noise. Search ranking is not chronological order; request newest ordering or compare actual timestamps. If discovery caps results, vary queries or exclude inspected sessions, and report any remaining coverage limit.
4. **Mine slices.** For one or two chats, read directly. Otherwise use `delegate_task(tasks=[{"goal": "Reconstruct the assigned work threads", "context": "<profile, workspace, selected session IDs, time range, topic, and return schema>"}, ...])`. Delegates inherit the parent model, not a chosen cheap or fast model. With no delegation tool, work serially and disclose it. Return one block per chat: topic, user goal, decisions, open threads, struggles/corrections, and artifacts such as PRs, tickets, or branches. Cite session ID, message anchor, and the tool's session link verbatim when available. Raw histories stay out of the parent summary.
5. **Sweep the shared record.** Whenever the topic names a feature, file, subsystem, area, or bug, follow `why`'s source playbooks in parallel with history mining. Ask “what is current, what was tried and did not hold, and what are users still reporting?” Use one investigator per available source. A null result is a finding; an unavailable integration is a disclosed gap. Skip this only for pure activity recall with no named target.
6. **Verify live state.** Check surfaced branches, PRs, and tickets through read-only `terminal` calls to the actual repository tools, such as `gh pr view <number> --json state,mergedAt,headRefName`. Use `read_file` and `search_files` on local artifacts. When a claim depends on tools an agent ran, inspect the complete in-scope session including tool messages, not merely its summary. If that evidence is unavailable, label the claim unverified.
7. **Write the brief.** Group by thread and stay on the named topic. Do not pull in adjacent work unless it blocks this one.

## History fallback

If `session_search` is not enabled, resolve the chosen profile with `terminal(command="hermes -p <profile> config path")`, then use `terminal(command="hermes -p <profile> sessions list --workspace <repo-root> --limit <limit>")`. This is candidate discovery, not an exhaustive time-filtered history. Export only selected sessions with `terminal(command="hermes -p <profile> sessions export --session-id <id> --format jsonl --redact <scratch>/session.jsonl")` and inspect with `read_file`. Use the installed CLI's `sessions export --help` for time filters when an exhaustive range is required. Do not upload exports, scan unrelated state databases, or guess legacy transcript paths. If neither history path works, report the gap and use only supplied context plus live state.

## Output contract

Lead with the capsule, then thread status, problems, and the next move:

- **Capsule:** at most five bullets saying what this work is and where it stands.
- **Threads:** one line each, tagged `[merged #N]`, `[open PR #N]`, `[in flight <branch>]`, `[verified, uncommitted]`, `[reverted #N]`, or `[planned, not started]`. Use `[unverified]` rather than inventing a status when evidence is missing.
- **Problems:** at most five recurring symptoms, blockers, and fixes that shipped then were reverted.
- **Next move:** the single most useful concrete action.

Load `skill_view(name="unslop")` for the prose. Cite history by real session/message pointers and shared findings by their actual source. Sanitize private context before any public output. If it outgrows a screen, cut detail before cutting threads.

## Verification

Every included thread is in scope, every claimed live status has a current read-only check, and evidence distinguishes observations from summaries or inference. Say what time range and sources were actually covered. Never claim complete history from a truncated index or a missing export.

# Slack Conversations

Load with `skill_view(name="why", file_path="references/sources/slack.md")`. Investigate only the assigned team chat source using authorized read access. Tool names below are illustrative service capabilities, not guaranteed Hermes tool names. Discover enabled tools and inspect their actual schemas before calling; use the advertised names and parameters. No external writes, profile changes, or recursive delegation are authorized. Return exact queries, evidence locations, and access/retention gaps; never invent results.

## How to search it

Slack integration tools vary. Inspect the enabled read/search schemas first. Use existing authorized access; if authentication is missing or fails, report a gap and request the normal setup flow rather than inventing an auth tool or changing runtime config. Never post messages, join unrelated channels, or search outside the task's authorized workspace.

1. **Author-bounded search.** Messages from the PR author around the PR merge date. Limits scope dramatically and often hits gold.
2. **PR URL search.** Slack often links PRs when they're reviewed or discussed. Search for the PR URL (or just `/pull/<number>`).
3. **Error string search.** If the code handles a specific error, search for the error string. Incident threads often surface.

## Common pitfalls

- **Channel archaeology limits.** Very old messages may be gone due to retention policies. If you can't find anything before a certain date, note the retention cliff.
- **Unsearched DMs.** Many decisions happen in DMs that aren't searchable. You'll miss them. That's a known limitation.
- **Speculative jokes as "decisions."** Slack is casual. "Lol just do the thing" isn't a decision, even if it preceded the commit. Look for considered discussion.
- **Context collapse in single messages.** Without the thread, a single message often reads differently than in context. Always fetch threads.
- **Auth failures.** If the MCP isn't authenticated, stop. Don't make up findings. Report that Slack wasn't searchable.

# Sentry Error History

Load with `skill_view(name="why", file_path="references/sources/sentry.md")`. Investigate only the assigned error tracking source using authorized read access. Tool names below are illustrative service capabilities, not guaranteed Hermes tool names. Discover enabled tools and inspect their actual schemas before calling; use the advertised names and parameters. No external writes, profile changes, or recursive delegation are authorized. Return exact queries, evidence locations, and access/retention gaps; never invent results.

## How to search it

Use the enabled Sentry read integration. Example capabilities below are not guaranteed tool names; discover actual schemas, organization/project scope, and pagination before querying. Do not resolve issues, change alerts, or mutate project state.

1. **Orient.** If you don't know the project slug and organization:

   ```
   find_organizations
   find_projects
   ```

2. **Search for issues related to the target.**

   ```
   search_issues (natural language, e.g., "errors in PaymentService timeout", "unhandled exceptions in uploadFile")
   ```

   Build queries from the exception class names the target handles, its function or class name, the error message strings it checks for, and its file path.

3. **Narrow by release and time window.**

   ```
   search_issue_events (filter by release, time, environment, trace ID, tags)
   get_issue_tag_values (for an issue, see distribution across versions, users, environments)
   ```

   For a suspected issue, check **first seen** and **last seen** (does the stop line up with the target's ship date?), the **affected releases** (which saw it, and which was the fix?), and the **frequency trajectory** (did it spike, then get resolved?).

4. **Pull the full event for context.**

   ```
   get_sentry_resource (pass a Sentry URL or type+ID)
   ```

   Does the stack trace pass through the target code? Do the tags and breadcrumbs match the conditions the target defends against?

5. **Check releases that landed near the target.**

   ```
   find_releases (around the commit date of the target)
   ```

   Cross-reference release version with the PR's merge date.

6. **Use Seer only when authorized and available.** An analysis service may be paid or stateful; do not assume it is a free read. Prefer existing events and existing analyses. If a new analysis is not authorized, skip it and state the limitation.

   ```
   analyze_issue_with_seer
   ```

   Seer's AI root-cause analyses are a hypothesis generator. Treat them as inference, not authoritative. The actual events and stack traces are the primary evidence.

## What to return

For each relevant issue:
- Issue ID and title
- Project and organization
- First seen / last seen timestamps
- Event count (and sampling rate if known)
- Affected releases
- A representative stack trace snippet showing relevance to the target (verbatim excerpt, not summary)
- First/last-seen correlation with the target's ship date
- Link to the issue
- Any author comments or resolution notes

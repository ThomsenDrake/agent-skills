---
name: why
description: "Use when investigating code rationale or history."
compatibility: "Requires Hermes delegation and file tools, terminal with git; gh and external read integrations when available."
---

# Why

Investigate the motivation and intent behind code. Load `how` for runtime mechanics; this workflow explains the forces that led to the current shape.

## Operating posture and Hermes contract

Be a careful, cautious, precise investigator. Load `skill_view(name="why", file_path="references/epistemics.md")` before reasoning about confidence. Code reveals mechanics, not author intent.

Use `delegate_task(tasks=[{"goal": "...", "context": "..."}, ...])` for bounded investigators, then a separate synthesis stage. Children inherit the parent model unless global delegation settings override it. Different evidence sources and roles improve coverage, but this is not cross-model evidence. No per-call model selection, invented aliases, or recursive child orchestration is required.

Every context stands alone: question, workspace, code anchor, assigned source, full prompt/playbook, actual discovered tool names and schemas, scope, read-only behavior, and report contract. No source writes, commits, or external mutations are authorized. A no-write instruction does not sandbox tool access. If an integration is unavailable to a child, let the parent fetch its read-only evidence and pass it in; do not fabricate access.

## Step 1: Understand the target and question

The target may be code, a pattern, feature, or named design decision. The question may concern rationale, tradeoffs, an edge case, external constraints, dead code, regression, postmortem, or a data-backed threshold.

For a vague referent, use current conversation context, provided paths, and recent edits. State your interpretation briefly and proceed unless missing context changes the investigation materially. Do not assume editor-only state exists.

## Step 2: Establish the code anchor

Use `read_file` and `search_files` to record file/line ranges and symbols. Through `terminal`, inspect history with commands such as:

- `terminal(command="git blame -L <start>,<end> -- <file>")` for last-touch commits.
- `terminal(command="git log --follow -p -- <file>")` for patches through renames.
- `terminal(command="git log --oneline -20 -- <file>")` for recent changes and PR references.
- `terminal(command="git log -1 --format=%B <commit>")` for complete messages.
- `terminal(command="gh pr view <number> --json title,body,author,createdAt,mergedAt,labels,closingIssuesReferences,comments,reviews")` for substantive PR context when authenticated access exists.

Resolve the repository and exact identifiers before running commands, quote paths safely, and paginate large history rather than silently truncating it. Extract PR references such as `(#1234)` and linked ticket IDs. Capture source-control access failures as gaps; git history may be shallow, absent, or unrelated, and `gh` is not guaranteed authenticated.

Completion: all investigators receive the same evidence-backed code anchor, including unavailable history.

## Step 3: Discover sources and dispatch investigators

Default to broad evidence coverage. Document null searches instead of skipping them because an answer seems likely.

Inspect Hermes's enabled tools and integration descriptors. For a deferred tool, search for the needed read/search capability and inspect its schema before calling. Use the tool discovery facilities actually exposed by the runtime; do not inspect another harness's directories or assume a service's tools exist. Inspect enabled MCP setup with `terminal(command="hermes mcp list")` only when needed and available. This is discovery, not authorization to add servers or change profiles.

Map available read sources to seven categories:

1. **Source control history:** git, PRs, comments, tests. Best at implementation-time rationale captured during review. Always attempt local discovery; report limitations honestly.
2. **Issue / ticket tracker:** Linear, Jira, GitHub Issues, Plane, Shortcut. Best at product/business forcing functions.
3. **Long-form documents:** Notion, Confluence, Google Docs, Coda. Best at written design rationale.
4. **Real-time team chat:** Slack, Discord, Teams, Mattermost. Best at deliberation that never reached a document.
5. **Infrastructure observability:** Datadog, New Relic, Honeycomb, Grafana, Splunk. Best at runtime conditions behind retries, timeouts, rate limits, and circuit breakers.
6. **Error / exception tracking:** Sentry, Rollbar, Bugsnag, Airbrake. Best at concrete error trajectories behind defensive code.
7. **Product analytics warehouse:** Databricks, Snowflake, BigQuery, ClickHouse, dbt, Redshift. Best at product/data constraints, experiments, migrations, and thresholds.

Classify using service instructions, tool schemas, and resource descriptors, not names alone. Record ambiguous mappings. Use one bounded investigator per available category and assign exactly one source to each. If a category has multiple useful integrations, use separate source-scoped investigators and aggregate them under that category. Do not ask one child to search unrelated integrations.

Load the source index with `skill_view(name="why", file_path="references/source-playbook.md")`, then the matching `references/sources/<source>.md` through `skill_view`. These are examples, not promises of tool names or schema. Load `references/investigator-prompt.md` the same way. For defensive code, append `references/sources/incident-postmortem.md` to each relevant brief.

Dispatch independent investigators in one `delegate_task(tasks=[...])` batch, or bounded batches if the runtime reports a concurrency limit. Each child owns its source, keeps exact queries/citations, and returns cross-source leads for the parent to route later. The parent, not a child, starts any follow-up investigation.

A background handle is not findings. Finish independent work and yield for completion messages between turns; do not poll child transcripts or partial artifacts. In finite one-shot sessions, use actual joined results if returned. Owner exit does not preserve running children.

### Skips and gaps

Record a written reason in Sources Consulted for every unsearched category:

- No matching enabled, authorized read integration: an access gap, not a deliberate quality shortcut.
- Provably irrelevant: explain why, such as a build-time-only target with no runtime exception path.

Authentication failure, retention loss, and unavailable child tool access are gaps, not empty searches. A trivial single-commit question may be answered inline only after the seven-category coverage assessment establishes why further available searches are redundant. Say so explicitly. If delegation itself is unavailable, do the available searches inline and disclose the sequential fallback.

## Step 4: Synthesize

After all findings arrive, dispatch one synthesizer with `delegate_task(tasks=[{"goal": "Synthesize the code rationale with calibrated confidence", "context": "<question, code anchor, every finding/null/gap, full epistemics and synthesizer templates, available read tools, no-write constraint>"}])`.

Load `skill_view(name="why", file_path="references/synthesizer-prompt.md")`. Include all investigator findings, skipped-category reasons, the code anchor, and the epistemics framework. The synthesizer spot-checks citations; the parent verifies the decisive evidence against exact sources before finalizing. Child summaries are self-reports. Agreement among investigators about one quoted source is not independent corroboration.

## Step 5: Present and verify

Present the synthesis with light edits but preserve its calibrated confidence language. Keep sections distinct: The Question, The Code in Question, What We Found, What We Can Reasonably Infer, Competing Hypotheses, What We Don't Know, Sources Consulted, Confidence Summary.

Sources Consulted accounts for all seven categories and each investigator, including null results, skips, search scope, and reason. Do not infer missing categories were searched. If a change is planned, translate lineage into Preserve / Change / Avoid / Risk constraints after the source map.

Completion: every strong claim has a verified citation, every inference is hedged, contradictions are visible, source counts match the roster, and unresolved gaps are named. Resist recency bias: the newest commit is not necessarily the origin of the design.

# Databricks Analytics & System Tables

Load with `skill_view(name="why", file_path="references/sources/databricks.md")`. Investigate only the assigned analytics warehouse source using authorized read access. Tool names below are illustrative service capabilities, not guaranteed Hermes tool names. Discover enabled tools and inspect their actual schemas before calling; use the advertised names and parameters. No external writes, profile changes, or recursive delegation are authorized. Return exact queries, evidence locations, and access/retention gaps; never invent results.

## What this source contains

Databricks is the product-analytics, data-pipeline, and warehouse-telemetry layer. It complements Datadog. Datadog is the *infra/runtime* view, Databricks is the *product/data* view (what users did, which experiments ran, how feature usage evolved, where a threshold constant came from).

- **Product analytics events.** `your_warehouse.events.analytics_track_event` (raw) and typed, deduplicated per-event dbt models in `<your_analytics_db>.<schema>.<table>`. User behavior: feature invocations, clicks, accepts/rejects, submissions, client-reported errors.
- **Usage & billing events.** `your_warehouse.events.usage_event` / `<your_analytics_db>.<schema>.stg_usage_events`, `your_warehouse.events.raw_model_event` / `<your_analytics_db>.<schema>.stg_raw_model_events`. For cost- or volume-driven decisions.
- **Experiment / feature-flag data.** Exposure and outcome tables. **Schema is company-specific.** Probe with `SHOW TABLES` before assuming names.
- **System tables.** `system.query.history`, `system.compute.warehouses`, `system.billing.*`, `system.access.audit`. Answer "was this query expensive?", "how often did anyone run this?", "when did warehouse load spike?"
- **dbt lineage.** Models in `<your_analytics_db>.<schema>` reveal what pipelines depend on a table/field. Upstream changes frequently motivate consumer-code changes.
- **Databricks notebooks.** Exploratory analyses engineers wrote before code changes. **Not accessible through SQL alone.** If no enabled, authorized notebook-read capability exists, name the notebook rationale as a gap rather than inventing its contents.

## How to search it

Use an enabled Databricks SQL read integration. `execute_sql_read_only` and `poll_sql_result` are example names: inspect the actual schema. If an asynchronous query returns a statement identifier, fetch that query's result using its advertised read/status operation rather than resubmitting it. This is service-query result retrieval, not child-transcript polling. No DDL, DML, warehouse changes, or mutation-capable query is part of this investigation.

**Orient before querying.** Schemas are company-specific. Probe before trusting a table name:

```sql
SHOW TABLES IN <your_analytics_db>.<schema> LIKE '*<keyword>*';
DESCRIBE TABLE <your_analytics_db>.<schema>.stg_<event>;
```

**Time-bound every data query.** These tables can be huge and unconstrained scans expensive. Discover the actual time columns and retention, then filter with a ship-date window, typically about 30 days before and after, wider only for a strong reason. `_timestamp` for events and `start_time` for `system.query.history` are examples to verify, not assumed universal fields. Limit output and aggregate counts/percentiles in SQL or a tool rather than calculating mentally.

**Prefer typed dbt models over the raw table.** `<your_analytics_db>.<schema>.<table>` is deduplicated, typed, and liquid-clustered. `your_warehouse.events.analytics_track_event` has duplicates and untyped `properties_json`. Model-name pattern: `stg_<source>_<event_name_with_underscores>`, where `<source>` is `app`, `backend`, `website`, or `cli`. Confirm the exact model name with `SHOW TABLES` when the pattern alone doesn't resolve it. Drop to the raw table only when there's no dbt model yet, or you need events from inside the dbt refresh lag.

**Illustrative column conventions on typed dbt models.** These are examples, not a guarantee; inspect `DESCRIBE TABLE` before relying on names, types, or units:

- `_timestamp`, `_id`, `_auth_id`, `_request_id`, `event_name`. Standard on every model
- `properties_<name>`. Typed, underscore-cased event properties (`properties_entrypoint`, `properties_size_bytes`, …)
- `context_team_id`, `context_client_version`, `context_country`, `context_client_os`. Pre-extracted client context

### Investigation patterns that tend to pay off

Pick the table + column combination that matches the target:

1. **Event usage trajectory.** Daily counts on the relevant `stg_*` model across a ±30d window around the PR merge. A step function from zero to steady volume within a day or two of the merge is strong circumstantial evidence the PR launched the feature. A decay to zero suggests a deprecation or deletion.
2. **Guard-rail / defensive-check origin.** Distribution (median / p99 / max) of the relevant `properties_<name>` column in the 14 days *before* the PR. A p99 that matches the target's threshold constant suggests the number was chosen from data.
3. **Experiment / feature-flag lookup.** `SHOW TABLES ... LIKE '*experiment*'` to find the exposure table, then pull exposure counts by variant for the relevant flag key near the PR date.
4. **Query-history evidence for migrations, backfills, or perf rewrites.** `system.query.history` filtered by `statement_text ILIKE '%<table_or_symbol>%'` with a tight `start_time` window surfaces the expensive queries that likely motivated the change (sort by `total_duration_ms` or aggregate `SUM(read_bytes)`, `COUNT(*)`).
5. **dbt lineage.** If the target reads from or writes into a `<your_analytics_db>.<schema>` model, the model's own git history (in this repo) often carries the rationale. Hand that lead back to the git investigator rather than chasing it yourself.

## What good evidence looks like here

Beyond the pattern shapes above:

- An error-classifying event's count drops to near zero in the days after a defensive-code PR. Suggests the PR resolved that error class
- An exposure table row names the target's feature-flag key with a "shipped" / "concluded" decision around the PR ship date

## Common pitfalls

- **Instrumented ≠ caused.** An event's existence means someone cared enough to log it, not that the target code exists *because* of it. Pair with a PR/commit citation from the git investigator before claiming causation.
- **Silent instrumentation changes.** A step function in event volume may mean a new event started being logged, not that user behavior changed. Check for instrumentation PRs in the same window before reading the ramp as a feature-launch signal.
- **Schema drift.** Event properties evolve. A column on the typed dbt model today may not have existed when the target was written. Older data may carry the property only inside raw `properties_json`.
- **dbt refresh lag.** `<your_analytics_db>.<schema>.*` is rebuilt on a schedule (often hourly/daily). For events from the last few hours, fall back to `your_warehouse.events.*` and deduplicate by `_id`.
- **Company-specific tables.** Experiment, feature-flag, billing, and usage tables vary. Reporting a result from a table whose existence you never confirmed is a classic failure mode. Probe with `SHOW TABLES` / `DESCRIBE TABLE` first.
- **Retention cliff.** If the relevant window predates the table's retention or the dbt model's creation date, that's a *gap*, not a null result. Name it explicitly so the synthesizer doesn't read "no results" as "no activity."
- **Notebook access is separate.** A SQL-only integration cannot read notebook content. Use a discovered authorized notebook-read tool only if it is part of the assigned source; otherwise return a gap.

## What to return

For each relevant finding:
- Type (product event / experiment exposure / usage or billing event / system-table row / dbt model)
- Fully-qualified table name and the exact query you ran
- Time window queried
- Compact numeric summary (counts, percentiles, first/last-seen timestamps). **Don't dump raw rows.**
- Temporal correlation with the target's ship date (e.g., "first row 2024-08-15, PR #49074 merged 2024-08-14")
- Relevance + strength: direct / circumstantial / weak

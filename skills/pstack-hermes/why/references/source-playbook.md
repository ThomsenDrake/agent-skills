# Source playbooks

Load with `skill_view(name="why", file_path="references/source-playbook.md")`. The parent assigns one investigator to each available source and accounts for all seven evidence categories. The playbooks are concrete service examples, not guarantees of installed integrations or current API names. Discover enabled read/search tools, inspect actual schemas, and adapt within the assigned category. Never add servers or change runtime profiles as part of an investigation.

Load each selected file using `skill_view(name="why", file_path="<playbook below>")` before passing its contents to a child.

| Category | Playbook | Example source |
|---|---|---|
| Source control history | `references/sources/code-archaeology.md` | git, `gh` |
| Issue / ticket tracker | `references/sources/linear.md` | Linear; adapt for Jira, GitHub Issues, Plane, Shortcut |
| Long-form documents | `references/sources/notion.md` | Notion; adapt for Confluence, Google Docs, Coda |
| Real-time team chat | `references/sources/slack.md` | Slack; adapt for Discord, Teams, Mattermost |
| Infrastructure observability | `references/sources/datadog.md` | Datadog; adapt for New Relic, Honeycomb, Grafana, Splunk |
| Error / exception tracking | `references/sources/sentry.md` | Sentry; adapt for Rollbar, Bugsnag, Airbrake |
| Product analytics warehouse | `references/sources/databricks.md` | Databricks SQL; adapt for Snowflake, BigQuery, ClickHouse, dbt |

For defensive code, also load `skill_view(name="why", file_path="references/sources/incident-postmortem.md")` and apply it inside each assigned source. Route cross-source leads back to the parent rather than recursively delegating or accessing another investigator's source. Missing tools, authentication failures, retention loss, and unsearched categories remain explicit gaps.

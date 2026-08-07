# Sources and Known Documentation Gaps

Snapshot date: 2026-08-06. Recheck official sources before acting on a changed or contradictory detail.

## Sources

- [Omi documentation index](https://docs.omi.me/llms.txt)
- [Developer API overview](https://docs.omi.me/doc/developer/api/overview)
- [Developer REST OpenAPI](https://docs.omi.me/api-reference/openapi.json)
- [App-client OpenAPI](https://docs.omi.me/api-reference/app-client-openapi.json)
- [Integration-public OpenAPI](https://docs.omi.me/api-reference/integration-public-openapi.json)
- [Import API](https://docs.omi.me/doc/developer/apps/Import)
- [OAuth](https://docs.omi.me/doc/developer/apps/Oauth)
- [Integration apps and webhooks](https://docs.omi.me/doc/developer/apps/Integrations)
- [MCP introduction](https://docs.omi.me/doc/developer/mcp/introduction)
- [MCP tools](https://docs.omi.me/doc/developer/mcp/tools)
- [CLI for agents](https://docs.omi.me/doc/developer/cli/agents)

## Known gaps

The narrative Developer overview describes personal REST authentication with a Developer key, while generated endpoint pages can say `firebase_id_token`; key-management authentication wording is also inconsistent. Webhook signing, delivery retries, ordering, idempotency, and exactly-once guarantees are not documented. Offset pagination has no published snapshot guarantee. No formal REST deprecation policy or legal data ownership/retention SLA was found in the reviewed sources.

Treat these as documentation gaps, not permissions to guess. Verify the current official source or stop and explain the uncertainty.

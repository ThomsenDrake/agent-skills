# Sources and Known Documentation Gaps

Snapshot date: 2026-08-07. Recheck official sources before acting on a changed or contradictory detail.

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
- [MCP setup](https://docs.omi.me/doc/developer/mcp/setup)
- [MCP tools](https://docs.omi.me/doc/developer/mcp/tools)
- [CLI quickstart](https://docs.omi.me/doc/developer/cli/quickstart)
- [CLI for agents](https://docs.omi.me/doc/developer/cli/agents)
- [CLI troubleshooting](https://docs.omi.me/doc/developer/cli/troubleshooting)

## Known gaps

The narrative Developer overview describes personal REST authentication with a Developer key, while generated endpoint pages can say `firebase_id_token`; key-management authentication wording is also inconsistent. Webhook signing, delivery retries, ordering, idempotency, and exactly-once guarantees are not documented. Offset pagination has no published snapshot guarantee. No formal REST deprecation policy or legal data ownership/retention SLA was found in the reviewed sources.

Treat these as documentation gaps, not permissions to guess. Prefer the narrative Developer overview for the documented public `omi_dev_...` REST flow, but report a persistent authentication conflict instead of substituting Firebase credentials. If official sources cannot be accessed, treat the affected guarantee as unknown, avoid writes that depend on it, and tell the user that live verification was unavailable.

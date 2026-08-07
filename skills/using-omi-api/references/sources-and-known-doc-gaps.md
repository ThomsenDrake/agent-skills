# Sources and Known Documentation Gaps

Snapshot date: 2026-08-07. Recheck official sources before relying on a changing or contradictory contract.

## Sources

- [Omi documentation index](https://docs.omi.me/llms.txt)
- [Developer API overview](https://docs.omi.me/doc/developer/api/overview)
- [Developer keys](https://docs.omi.me/doc/developer/api/keys)
- [Developer conversations](https://docs.omi.me/doc/developer/api/conversations)
- [Developer REST OpenAPI](https://docs.omi.me/api-reference/openapi.json)
- [Integration-public OpenAPI](https://docs.omi.me/api-reference/integration-public-openapi.json)
- [App-client OpenAPI](https://docs.omi.me/api-reference/app-client-openapi.json)
- [Import API](https://docs.omi.me/doc/developer/apps/Import)
- [OAuth](https://docs.omi.me/doc/developer/apps/Oauth)
- [Integration apps and webhooks](https://docs.omi.me/doc/developer/apps/Integrations)
- [MCP setup](https://docs.omi.me/doc/developer/mcp/setup)
- [MCP tools](https://docs.omi.me/doc/developer/mcp/tools)
- [CLI command reference](https://docs.omi.me/doc/developer/cli/commands)
- [CLI for agents](https://docs.omi.me/doc/developer/cli/agents)
- [CLI troubleshooting](https://docs.omi.me/doc/developer/cli/troubleshooting)
- [OWASP prompt injection guidance](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)

## Known gaps and precedence

| Area | Current conflict or omission | Safe handling |
|---|---|---|
| Developer authentication | Some generated endpoint pages still show Firebase for personal user resources. The canonical Developer OpenAPI uses `developerApiKey` for `/v1/dev/user/*`; the overview documents `omi_dev_...`. | Use `omi_dev_...` for personal user resources. Do not substitute a generic Firebase token. |
| Key lifecycle | The dedicated keys guide and Developer OpenAPI require a signed-in Omi/Firebase session for `/v1/dev/keys*`, but a stale example later on the same guide uses `omi_dev_...`. | Follow the route-specific guide text and OpenAPI: an existing Developer key cannot manage keys. Prefer the trusted UI when a one-time secret cannot be captured safely. |
| Integration route catalog | The narrative Import guide lists four core routes; the Integration-public OpenAPI currently lists eight. Generated request schemas also contain fields absent from the narrative. Legacy `POST /v1/integrations/notification` has an open body with no deterministic recipient binding in that schema. | Use the live Integration OpenAPI for route and schema discovery, retain narrative capability/consent requirements, and label generated-only fields. Keep the legacy notification route catalog-only until an authoritative binding contract exists. |
| Integration statuses | The Import narrative says comma-separated; current OpenAPI and implementation model `statuses` as an array. | Use repeated query parameters and recheck before release. |
| Webhook management | The narrative guide describes app Developer Settings only. The app-client OpenAPI separately exposes Firebase-authenticated webhook URL/status/enable/disable routes and adds `audio_bytes_websocket`, but its aggregate status response omits that websocket field. | Distinguish public Integration delivery from signed-in app-client management. Never use `sk_...` or `omi_dev_...` on app-client management routes, and do not infer websocket state from the aggregate status response. |
| Webhook security and delivery | No Omi signature, protocol auth header, source allowlist, retry, ordering, idempotency, or exactly-once contract is documented. | Use independent ingress controls, strict validation, namespaced deduplication, and authenticated reconciliation. Do not invent guarantees. |
| MCP authentication | Public MCP setup documents `omi_mcp_...` or MCP OAuth; the app-client OpenAPI labels `/v1/mcp/sse` `firebaseBearer`. | Follow public MCP setup and live MCP negotiation. Do not substitute a generic Firebase token. |
| MCP tool catalog | The narrative reference lists eight tools, while the live server can expose more. | Treat MCP `tools/list` and its returned schemas as the live capability contract. |
| Pagination and lifecycle | Offset pagination has no published snapshot guarantee. No formal REST deprecation policy or legal data ownership/retention SLA was found in the reviewed sources. | Bound work, freeze destructive manifests, revalidate, and report unknown guarantees rather than guessing. |

If official sources cannot be accessed, treat affected routes, fields, authentication, and delivery guarantees as unknown. Reads may proceed only if the configured contract is already sufficient and low risk. Do not perform a write that depends on the unknown detail, and report that live verification was unavailable.

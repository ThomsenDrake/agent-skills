---
name: using-omi-api
description: Use when building, configuring, troubleshooting, or safely automating Omi Developer REST API, Integration Import API, OAuth, webhooks, Omi MCP, or omi-cli access.
compatibility: Live Omi API calls require network access and host-approved secret injection. MCP execution requires an MCP-capable client. CLI execution requires omi-cli; the labeled POSIX example also requires jq.
---

# Using Omi API

Choose the ownership and delivery model before choosing a credential or endpoint. Omi exposes different surfaces for a person's own data, an enabled third-party app acting for a user, event delivery, MCP-capable host tools, and headless automation.

## Route the request

| Intent | Surface | Read first |
|---|---|---|
| Own memories, conversations, action items, folders, or goals over HTTP | Developer REST | [Developer REST](references/developer-rest-api.md) |
| Data for another user through an enabled app | Import API and OAuth | [Import, OAuth, and webhooks](references/integration-oauth-webhooks.md) |
| Receive memory, transcript, audio, or summary events | Webhooks | [Import, OAuth, and webhooks](references/integration-oauth-webhooks.md) |
| Contextual access through an MCP-capable host | Omi MCP | [MCP and CLI](references/mcp-and-cli.md) |
| Headless or CI JSON automation | `omi-cli` plus REST semantics | [MCP and CLI](references/mcp-and-cli.md), then [Developer REST](references/developer-rest-api.md) |

## Required workflow

1. Classify the surface and read its reference.
2. Check credential prefix, authority model, and least privilege.
3. Read `references/safety-reliability.md` before mutations, transcript/audio export, webhook receivers, or batch jobs.
4. Resolve exact IDs for existing-resource mutations. For creates, resolve the destination and preview the payload; preview all destructive or externally visible writes.
5. Use only configured credentials or user-authorized interactive setup.
6. If official sources cannot be accessed, treat changing or contradictory guarantees as unknown. Do not perform a write that depends on them, and report that live verification was unavailable.
7. Verify the response, retain IDs for reconciliation, and state unknown delivery or consistency guarantees.

## Common mistakes and guardrails

- Never expose raw Omi keys in chat, logs, source control, command output, shell history, or plaintext files. Store them only in a host-approved secret manager or inject them through the execution environment.
- Match the credential to the surface: `omi_dev_...` for personal Developer REST, `sk_...` for an enabled app's Import API, and `omi_mcp_...` only for MCP. Never substitute a callback `uid`, Firebase token, or another surface's key.
- Never blindly retry an uncertain mutation. `client_session_id` is documented only for transcript-segment conversation retries.
- Do not treat webhook `uid`, `session_id`, resource IDs, or payload hashes as sender authentication. Do not claim REST registration, signing, ordering, retries, or exactly-once delivery unless current official documentation proves it.
- Recheck `references/sources-and-known-doc-gaps.md` when generated endpoint pages conflict with the narrative API documentation.

HTTP shape for an authorized personal read:

```http
GET /v1/dev/user/memories?limit=25&offset=0 HTTP/1.1
Host: api.omi.me
Authorization: Bearer <configured omi_dev key>
```

Keep transcripts, audio, locations, memories, and webhook payloads to the minimum needed for the request.

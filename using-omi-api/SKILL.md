---
name: using-omi-api
description: Use when building, configuring, troubleshooting, or safely automating Omi Developer REST API, Integration Import API, OAuth, webhooks, Omi MCP, or omi-cli access.
---

# Using Omi API

Choose the ownership and delivery model before choosing a credential or endpoint. Omi exposes different surfaces for a person's own data, an enabled third-party app acting for a user, event delivery, assistant-native tools, and headless automation.

## Route the request

| Intent | Surface | Read first |
|---|---|---|
| Own memories, conversations, action items, folders, or goals over HTTP | Developer REST | `references/developer-rest-api.md` |
| Data for another user through an enabled app | Import API and OAuth | `references/integration-oauth-webhooks.md` |
| Receive memory, transcript, audio, or summary events | Webhooks | `references/integration-oauth-webhooks.md` |
| Assistant-native contextual access | Omi MCP | `references/mcp-and-cli.md` |
| Headless or CI JSON automation | `omi-cli` | `references/mcp-and-cli.md` |

## Required workflow

1. Classify the surface and read its reference.
2. Check credential prefix, authority model, and least privilege.
3. Read `references/safety-reliability.md` before mutations, transcript/audio export, webhook receivers, or batch jobs.
4. Resolve exact target IDs. Preview destructive or externally visible writes.
5. Use only configured credentials or user-authorized interactive setup.
6. Verify the response, retain IDs for reconciliation, and state unknown delivery or consistency guarantees.

## Non-negotiable guardrails

- Never print, store, commit, or request raw Omi keys in chat.
- Use a personal Developer key for personal REST data; use an MCP key only for MCP. Do not use a personal key for another user's data.
- Never blindly retry an uncertain mutation. `client_session_id` is documented only for transcript-segment conversation retries.
- Do not claim REST webhook registration, signing, ordering, retries, or exactly-once delivery unless current official documentation proves it.
- Recheck `references/sources-and-known-doc-gaps.md` when generated endpoint pages conflict with the narrative API documentation.

Example shape for an authorized personal read:

```sh
curl -H "Authorization: Bearer $OMI_API_KEY" \
  'https://api.omi.me/v1/dev/user/memories?limit=25&offset=0'
```

Keep transcripts, audio, locations, memories, and webhook payloads to the minimum needed for the request.

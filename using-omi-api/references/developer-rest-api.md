# Omi Developer REST API

## Contents

- [Authentication and key lifecycle](#authentication-and-key-lifecycle)
- [Limits and list semantics](#limits-and-list-semantics)
- [Resources](#resources)
- [Side effects and errors](#side-effects-and-errors)

## Authentication and key lifecycle

The [Developer overview](https://docs.omi.me/doc/developer/api/overview) documents the personal data base as `https://api.omi.me/v1/dev/user`. Authenticate these user-resource routes with a Developer key prefixed `omi_dev_...` as `Authorization: Bearer <key>`. Do not use an MCP `omi_mcp_...` key, Integration `sk_...` key, or Firebase token. Scope the key to the least privilege needed from `conversations:read`, `conversations:write`, `memories:read`, `memories:write`, `action_items:read`, `action_items:write`, `goals:read`, and `goals:write`.

Key lifecycle is a separate signed-in surface. `GET/POST /v1/dev/keys` and `DELETE /v1/dev/keys/{key_id}` require the user's current Omi/Firebase session; an existing `omi_dev_...` key cannot list, create, or revoke keys. Listing returns metadata and a prefix, not full secrets. Creation requires `name`, accepts optional scopes, and returns the full new key once.

Create a key through automation only when the response can stream directly into an approved secret store while stdout, stderr, traces, and telemetry are redacted. Retain only non-secret metadata for reconciliation. If the tool path would expose the one-time response, stop and have the user create the key in the trusted Omi Developer UI. Never print, echo, or return the `key` field.

## Limits and list semantics

The overview documents ceilings of 100 requests/minute/API key and 10,000/day/user. [CLI troubleshooting](https://docs.omi.me/doc/developer/cli/troubleshooting) also identifies `dev:conversations` at 25/hour, `dev:memories` at 120/hour, and `dev:memories_batch` at 15/hour. Treat these as cumulative policy limits, honor `X-RateLimit-*` and `Retry-After`, and do not assume the list is exhaustive. Coordinate one request budget per user, credential, and policy across parallel jobs; never evade a user limit by rotating keys.

Use bounded offset pages, preserve IDs, and deduplicate because no snapshot guarantee is published. `GET /v1/dev/user/conversations` returns only completed, non-discarded conversations by contract. Current implementation can exclude additional records such as locked content, but that is not a stable public selection guarantee. Absence from the list does not prove that a processing, failed, discarded, locked, or otherwise excluded conversation does not exist. A completed conversation can still have asynchronous memories or action items pending.

For date summaries, define the user's timezone and fixed start/end timestamps. Prefer `structured.overview` when present and do not request transcripts by default.

## Resources

| Resource | Methods and paths | Important rules |
|---|---|---|
| Keys | `GET/POST /v1/dev/keys`, `DELETE /v1/dev/keys/{key_id}` | Signed-in Omi/Firebase session, not `omi_dev`; full created key is shown once. |
| Memories | `GET/POST /v1/dev/user/memories`, `POST /v1/dev/user/memories/batch`, `PATCH/DELETE /v1/dev/user/memories/{memory_id}` | List by `limit`, `offset`, `categories`; content is 1-500 characters; batch max 25; public visibility shares data. |
| Vector search | `GET /v1/dev/user/memories/vector/search` | `query` is required; `limit` is 1-100. Besides `memories:read`, this fails closed without the persisted default-read grant and server rollout enablement. |
| Action items | `GET/POST /v1/dev/user/action-items`, `POST /v1/dev/user/action-items/batch`, `PATCH/DELETE /v1/dev/user/action-items/{action_item_id}` | Filter by conversation, completion, and dates; batch max 50; `due_at` may notify the user. |
| Conversations | `GET/POST /v1/dev/user/conversations`, `POST /v1/dev/user/conversations/from-segments`, `GET/PATCH/DELETE /v1/dev/user/conversations/{conversation_id}` | List filters include dates, categories, `folder_id`, `starred`, `include_transcript`, `limit`, and `offset`. Text is 1-100000 characters; segments are 1-500. Only segment ingestion documents stable `client_session_id` replay to the same conversation ID. |
| Folders | `GET /v1/dev/user/folders` | Requires `conversations:read`; list first to resolve valid folder IDs. |
| Goals | `GET/POST /v1/dev/user/goals`, `GET/PATCH/DELETE /v1/dev/user/goals/{goal_id}`, `GET /v1/dev/user/goals/{goal_id}/history`, `PATCH /v1/dev/user/goals/{goal_id}/progress` | History accepts `days` 1-365; progress uses query `current_value`; list can include inactive goals. |

Conversation creation starts asynchronous extraction and can invoke enabled apps or webhooks. Treat deletes, public visibility, due-date notifications, and key lifecycle as consequential writes.

## Side effects and errors

Common documented classes are 400, 401, 403, 404, 422, 429, and 500. A memory-read `403` with `developer_memory_access_not_ready` indicates account readiness, not a reason to regenerate keys. Reconcile uncertain writes by a documented stable identifier or read path before retrying; conversation-list absence alone is insufficient.

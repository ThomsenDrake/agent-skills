# Omi Developer REST API

## Contents

- [Authentication and limits](#authentication-and-limits)
- [Resources](#resources)
- [Side effects and errors](#side-effects-and-errors)

## Authentication and limits

The personal Developer API base is `https://api.omi.me/v1/dev`. The narrative API overview documents personal data access with a Developer key supplied as `Authorization: Bearer ...`. Keep the key in an environment variable. Scope keys to the least privilege needed: `conversations`, `memories`, `action_items`, or `goals`, with `read` or `write` access. A key's full value is revealed only at creation. Never expose it in output.

The documented rate limit is 100 requests/minute/API key and 10,000/day/user. Observe `X-RateLimit-*` headers. Use bounded offset pages, preserve IDs, and deduplicate because no snapshot guarantee is published.

For date-based summaries, define “yesterday” with the user's intended timezone and fixed start/end timestamps. Conversation list results are not a substitute for an undocumented completion guarantee: report the returned records and use only fields needed for the summary. `structured.overview` is the preferred compact representation when present; do not fetch transcripts by default.

## Resources

| Resource | Methods and paths | Important rules |
|---|---|---|
| Keys | `GET/POST /keys`, `DELETE /keys/{key_id}` | Create with `name` and optional scopes. Full key is shown once. Key-management auth wording is inconsistent; see the discrepancy guide. |
| Memories | `GET/POST /user/memories`, `POST /user/memories/batch`, `PATCH/DELETE /user/memories/{memory_id}` | List with `limit`, `offset`, `categories`; content is 1–500 characters; batch max 25; public visibility shares data. |
| Vector search | `GET /user/memories/vector/search` | Query is required; `limit` is 1–100. |
| Action items | `GET/POST /user/action-items`, `POST /user/action-items/batch`, `PATCH/DELETE /user/action-items/{action_item_id}` | Filter by conversation, completion, and dates; batch max 50; `due_at` may notify the user. |
| Conversations | `GET/POST /user/conversations`, `POST /user/conversations/from-segments`, `GET/PATCH/DELETE /user/conversations/{conversation_id}` | List filters include dates, categories, folder, starred, transcript, limit, and offset. Text is 1–100000 characters; segments are 1–500. `client_session_id` is the documented retry key for segment ingestion. |
| Folders | `GET /user/folders` | List first to resolve valid folder IDs. |
| Goals | `GET/POST /user/goals`, `GET/PATCH/DELETE /user/goals/{goal_id}`, `GET /user/goals/{goal_id}/history`, `PATCH /user/goals/{goal_id}/progress` | History accepts days 1–365; progress uses query `current_value`; list can include inactive goals. |

Conversation creation starts asynchronous extraction and may invoke enabled apps or webhooks. Prefer `structured.overview` before requesting a full transcript. Treat deletes and public visibility as consequential writes.

## Side effects and errors

Common documented classes are 400, 401, 403, 404, 422, 429, and 500. A memory-read `403` with `developer_memory_access_not_ready` indicates account readiness, not a reason to regenerate keys. A conversation may be completed but still have asynchronous derived memories or action items.

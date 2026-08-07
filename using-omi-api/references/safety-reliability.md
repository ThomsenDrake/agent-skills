# Safety and Reliability

## Contents

- [Data and secrets](#data-and-secrets)
- [Writes](#writes)
- [Pagination and retries](#pagination-and-retries)
- [Webhook receivers](#webhook-receivers)

## Data and secrets

- Keep keys in configured secret injection; never print, log, commit, or ask the user to paste them.
- Treat transcripts, audio, locations, memories, and webhook bodies as sensitive.
- Request only fields, date ranges, pages, and users necessary for the task.
- Public memory visibility is sharing, not a harmless formatting option.

## Writes

Require explicit intent and exact IDs before deleting memories, conversations, action items, or goals; revoking keys; publishing memories; creating conversations; setting due-date notifications; discarding data; or forwarding externally. Preview target and payload. If an ID is missing, search and ask for confirmation rather than guessing.

## Pagination and retries

Use offset pages with a bounded limit, deduplicate by stable IDs, and record the last successful page. Respect rate-limit headers and `Retry-After`. Retry reads and documented transient failures conservatively. Never blindly retry an uncertain mutation. Reconcile by known ID, a documented `client_session_id` where applicable, or a resource query before creating again.

| Signal | Response |
|---|---|
| REST request uses an MCP key | Stop and select an authorized personal Developer credential. |
| `403 developer_memory_access_not_ready` | Report account readiness; do not regenerate keys. |
| `429` | Back off, preserve progress, and avoid blind mutation retries. |
| Uncertain POST result | Reconcile before another create. |
| Webhook absent | Inspect receiver state and reconcile through the matching data surface. |

## Webhook receivers

Require HTTPS, bounded body handling, authentication appropriate to the receiver, least-privilege storage, fast acknowledgement, deduplication, and observability without logging sensitive content. Do not claim a signing or delivery guarantee the source does not document.

# Safety and Reliability

## Contents

- [Data and secrets](#data-and-secrets)
- [Writes](#writes)
- [Pagination and retries](#pagination-and-retries)
- [Webhook receivers](#webhook-receivers)

## Data and secrets

- Store keys only in a host-approved secret manager or configured secret injection. Never expose them in chat, logs, source control, command output, shell history, or plaintext files, and never ask the user to paste them into chat.
- Treat transcripts, audio, locations, memories, and webhook bodies as sensitive.
- Request only fields, date ranges, pages, and users necessary for the task.
- Public memory visibility is sharing, not a harmless formatting option.

## Writes

Treat every create, update, delete, publish, notification, key-management action, and MCP mutation as a write.

- Existing-resource mutations: resolve the exact resource ID, inspect the current object, and preview the requested change. This includes deleting or editing memories, conversations, action items, and goals; changing goal progress; completing action items; publishing memories; and revoking keys.
- Creates: require explicit intent and preview the destination account or `uid`, scope, and complete request body. Persist any returned ID. Do not require a nonexistent pre-create resource ID.
- Batch writes: preview the bounded count and full manifest, or a representative sample plus an exact selection rule when the manifest is too large.
- Consequential side effects: get confirmation for public visibility, due-date notifications, external forwarding, discarding data, or conversation creation that can invoke enabled apps or webhooks.
- Asynchronous Import creates: record the source ledger entry and reconcile through a read endpoint or the Omi app before retrying an empty-body success or uncertain response.

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

Omi currently documents no webhook signature, authorization header, mTLS requirement, or source-IP allowlist. Do not treat `uid`, `session_id`, body IDs, or payload hashes as sender authentication. Require HTTPS, an independently controlled receiver capability or gateway control, bounded body handling, least-privilege storage, durable enqueue before fast acknowledgement, deduplication, and observability without logging sensitive content. A resource ID or payload hash can help deduplicate but cannot authenticate the sender. Do not claim a signing or delivery guarantee the source does not document.

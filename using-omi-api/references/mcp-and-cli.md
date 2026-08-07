# Omi MCP and `omi-cli`

## Contents

- [MCP](#mcp)
- [CLI](#cli)

## MCP

MCP is assistant-native access at `/v1/mcp/sse` using an MCP key. Its documented tools include `get_memories`, `search_memories`, `create_memory`, `edit_memory`, `delete_memory`, `get_conversations`, `search_conversations`, and `get_conversation_by_id`.

An MCP key is not a personal REST credential. Do not send it to `/v1/dev` endpoints. Use MCP when the host agent needs contextual Omi tools; use REST when deterministic HTTP resource control or a complete resource inventory is required.

## CLI

For headless automation, set `OMI_API_KEY` through the execution environment and use `omi --json`. Keep stdout machine-readable JSON and treat stderr as structured error output. Use the Developer REST conversation reference for date boundaries, completion semantics, pagination, and transcript minimization. Define “yesterday” in an explicit timezone. Exit codes are 0 success, 1 usage, 2 authentication, 3 server/connection, 4 rate limited, and 5 not found.

```sh
omi --json memory list --limit 25 | jq '.[] | {id, content, category}'
```

The CLI retries transient 5xx, transport, and 429 failures according to its documented policy, but automatic retry does not make arbitrary creates idempotent. Reconcile uncertain writes before issuing another create.

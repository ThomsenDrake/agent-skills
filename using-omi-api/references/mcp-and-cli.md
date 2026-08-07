# Omi MCP and `omi-cli`

## Contents

- [MCP](#mcp)
- [CLI](#cli)

## MCP

The hosted MCP server provides contextual Omi access at `https://api.omi.me/v1/mcp/sse`, authenticated as `Authorization: Bearer omi_mcp_...`. Omi documents Streamable HTTP using the MCP 2025-03-26 specification. Its tools include `get_memories`, `search_memories`, `create_memory`, `edit_memory`, `delete_memory`, `get_conversations`, `search_conversations`, and `get_conversation_by_id`.

An MCP key is not a personal REST credential. Do not send it to `/v1/dev` endpoints. Use MCP only when the current host exposes an MCP client and the Omi server is configured; otherwise explain the prerequisite or use authorized REST when it fits the request. Never pretend an unavailable MCP tool was called. Use REST when deterministic HTTP resource control or a complete resource inventory is required. See the [official MCP setup guide](https://docs.omi.me/doc/developer/mcp/setup).

## CLI

Before relying on the CLI, verify that `omi` is available and record `omi --version`. If it is missing, explain the installation prerequisite or use authorized REST; do not silently install it. For headless automation, inject `OMI_API_KEY` through the execution environment and use `omi --json`, with global flags before the subcommand. Keep stdout as machine-readable JSON and treat stderr as structured error output. Read `references/developer-rest-api.md` for date boundaries, pagination, transcript minimization, and rate limits. Define “yesterday” in an explicit timezone. Exit codes are 0 success, 1 usage, 2 authentication, 3 server/connection, 4 rate limited, and 5 not found.

POSIX shell example that omits memory content:

```sh
omi --json memory list --limit 25 | jq '.[] | {id, category}'
```

The CLI retries transport and 5xx failures with backoff. For 429 responses, it honors `Retry-After` when present, capped at 60 seconds, and falls back to jitter otherwise; retries are limited to four attempts. Automatic retry does not make arbitrary creates idempotent. Reconcile uncertain writes before issuing another create. See the [CLI agent contract](https://docs.omi.me/doc/developer/cli/agents) and [CLI troubleshooting](https://docs.omi.me/doc/developer/cli/troubleshooting).

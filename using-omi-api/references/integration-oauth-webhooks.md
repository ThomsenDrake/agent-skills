# Integration API, OAuth, and Webhooks

## Contents

- [Integration API](#integration-api)
- [OAuth and tenant binding](#oauth-and-tenant-binding)
- [Webhook configuration](#webhook-configuration)
- [Webhook channels](#webhook-channels)
- [Receiver design](#receiver-design)

## Integration API

An enabled third-party app acts for a user through `https://api.omi.me` with `Authorization: Bearer <configured-integration-key>`. The `sk_...` key is an app-wide, server-only secret and must match the path `app_id`; never ship it in browser, mobile, or other public clients. The user must enable the app, and the app needs External Integration, Imports, and each operation's capability. Do not substitute a Developer, MCP, or Firebase credential.

Never accept an arbitrary caller-supplied `uid`. Derive it server-side from a validated `{local_principal_id, app_id, uid}` authorization mapping and recheck current consent and capability for every request.

The current Integration OpenAPI publishes eight operations:

| Operation | Route | Contract highlights |
|---|---|---|
| Create conversation | `POST /v2/integrations/{app_id}/user/conversations?uid=...` | Body requires `text`; narrative fields include timestamps, text source, language, and geolocation. Success is `200 {}` and processing is asynchronous. |
| Create memories | `POST /v2/integrations/{app_id}/user/memories?uid=...` | Supply extraction `text` or explicit `memories[]`; narrative fields include text source and tags. Success is `200 {}` and processing is asynchronous. |
| Read conversations | `GET /v2/integrations/{app_id}/conversations?uid=...` | `limit` 1-1000, `offset`, `include_discarded`, dates, statuses, and `max_transcript_segments`; response wraps `conversations`. |
| Read memories | `GET /v2/integrations/{app_id}/memories?uid=...` | `limit` 1-1000 and `offset`; response wraps `memories`. |
| Search conversations | `POST /v2/integrations/{app_id}/search/conversations?uid=...` | Body supports `query`, dates, `speaker_id`, `include_discarded`, `page`, and `per_page`; query controls `max_transcript_segments`. |
| Read tasks | `GET /v2/integrations/{app_id}/tasks?uid=...` | `limit`, `offset`, `completed`, `conversation_id`, creation dates, and due-date range. This is action-item access. |
| Notify user | `POST /v2/integrations/{app_id}/notification?uid=...&message=...` | Externally visible notification; preview recipient and message, then confirm. |
| Legacy notification | `POST /v1/integrations/notification` | Catalog only. Its generated schema is an open JSON object with no deterministic `app_id`/`uid` recipient binding. Do not call it unless an authoritative current contract defines the body, recipient binding, and authorization. |

For conversation list and search, explicitly set `max_transcript_segments=0` and `include_discarded=false` unless the request needs transcripts or discarded records. Also bound dates and page size. `max_transcript_segments` otherwise defaults to 100 and accepts `-1..1000`; `-1` means unlimited. The narrative [Import guide](https://docs.omi.me/doc/developer/apps/Import) says comma-separated `statuses`, but current OpenAPI and implementation use an array. Send repeated parameters such as `statuses=completed&statuses=failed` until Omi reconciles the conflict.

The narrative request-field lists are subsets of the generated schemas. Current generated conversation fields also include `source`, `app_id`, `client_device_id`, and `client_platform`; memory schemas add provenance fields including `source_id`, `source_url`, `artifact_ref`, and top-level `app_id`. Verify the live OpenAPI before using generated-only fields and do not infer fields from personal REST.

Before sending an Import mutation, atomically reserve a ledger record keyed by `{app_id, uid, operation, source_id, payload_hash}` with `pending` state. Mark it confirmed only after reconciliation. Do not send if the source identity is missing or already pending/confirmed. An empty success body does not prove asynchronous completion; reconcile through an authenticated read endpoint or the Omi app before retrying. A `403` can mean invalid key, disabled app, or missing capability. Stop new operations when access is revoked.

## OAuth and tenant binding

Omi's [OAuth guide](https://docs.omi.me/doc/developer/apps/Oauth) documents a 2.0-like app-enablement flow at `https://api.omi.me/v1/oauth/authorize?app_id=...&state=...`. It is not app token issuance: Omi handles Firebase exchange internally, and the app callback receives only `uid` and `state`, not access or refresh tokens. Later Integration calls still use the server-side `sk_...` key plus the mapped `uid`.

Create high-entropy state and store only its hash with `{local_principal_id, initiating_session_id, app_id, intended_callback, issued_at, expires_at}`. Make it short-lived and atomically consume it once before processing. Reject missing, expired, mismatched, or replayed state, a changed authenticated local principal or session, an unexpected app or callback, and callbacks without `uid`. Only then persist `{local_principal_id, app_id, uid}`. Store `uid` as sensitive data; it is never authentication proof by itself.

## Webhook configuration

The narrative Integration guide configures webhook URLs in Omi app Developer Settings and exposes no public `sk_...` registration route. A separate app-client OpenAPI publishes signed-in Omi/Firebase routes:

```text
GET|POST /v1/users/developer/webhook/{wtype}
POST     /v1/users/developer/webhook/{wtype}/enable
POST     /v1/users/developer/webhook/{wtype}/disable
GET      /v1/users/developer/webhooks/status
```

`POST .../{wtype}` accepts `{ "url": "https://..." }`, and reads can return the full configured URL. This management surface uses the user's signed-in Omi/Firebase session, not `sk_...`, `omi_dev_...`, or `omi_mcp_...`. Treat the entire URL as secret-bearing, suppress it from raw output and logs, and preview a redacted URL plus digest before changing URLs or enablement.

## Webhook channels

The generated `wtype` enum is `audio_bytes`, `audio_bytes_websocket`, `realtime_transcript`, `memory_created`, and `day_summary`; the narrative guide discusses four HTTP/UI channels and omits the websocket variant. The generated `/webhooks/status` response also omits `audio_bytes_websocket`, so it cannot verify that channel's final state; report it as unknown unless independently observed.

- Memory Creation can carry full conversation data. It fires when a memory is created, not as a guaranteed conversation-complete event.
- Real-Time Transcript carries segments with `session_id` and `uid`; receivers must tolerate duplicates.
- Audio Bytes are PCM16 binary POST bodies with a configured sample-rate query value.
- Day Summary is scheduled at most once per day when delivery conditions are met; absence is not necessarily failure. Prefer strict JSON in `summary_json`. Reject legacy `summary` by default. If compatibility is unavoidable, bound it, parse with a safe literal parser such as Python `ast.literal_eval`, never `eval`, then validate the resulting types and schema. The in-app Generate Summary action does not currently POST to this webhook.

## Receiver design

Omi currently documents no webhook signature, authorization header, mTLS requirement, or source-IP allowlist. Treat requests as unauthenticated at the Omi protocol layer. Never authorize from `uid`, `session_id`, an ID, or a hash.

Use HTTPS and an independently controlled ingress capability, such as an unlogged receiver secret in the configured URL or equivalent gateway control. Bind that capability to the expected app/receiver and tenant mapping. Treat full webhook URLs and Integration/OAuth query strings, including `uid`, `message`, and `state`, as sensitive; suppress them from access logs, traces, analytics, referrers, and raw tool output. Apply channel-specific limits for media type, body bytes, JSON depth/schema, audio sample rate, decompression, concurrency, and queue capacity; reject before buffering where possible. Durably enqueue only the minimum needed data before a fast 2xx.

Namespace replay and deduplication keys by `(validated receiver/app capability, mapped tenant/uid, channel or event type, resource ID or body hash)`. A hash is only a replay heuristic, and deduplication never authenticates or authorizes. Do not send payloads to public request-inspection services. Omi does not document retries, ordering, or exactly-once delivery; reconcile missing events through the corresponding authenticated data surface.

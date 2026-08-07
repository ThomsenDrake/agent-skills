# Import API, OAuth, and Webhooks

## Contents

- [Import API](#import-api)
- [OAuth](#oauth)
- [Webhook channels](#webhook-channels)
- [Receiver design](#receiver-design)

## Import API

An enabled third-party app acts for a user through `https://api.omi.me` with an app key prefixed `sk_...`:

```http
Authorization: Bearer sk_your_api_key_here
```

The key must belong to the `app_id` in the path. The user must explicitly enable the app, and the app must have External Integration, Imports, and the capability required for the operation. Do not substitute an `omi_dev_...` key, `omi_mcp_...` key, Firebase token, or callback `uid`. The documented paths are:

```text
POST /v2/integrations/{app_id}/user/conversations?uid={user_id}
POST /v2/integrations/{app_id}/user/memories?uid={user_id}
GET  /v2/integrations/{app_id}/conversations?uid={user_id}
GET  /v2/integrations/{app_id}/memories?uid={user_id}
```

Operation details:

| Operation | Documented request and response |
|---|---|
| Create conversation | `text` is required. Optional fields are `started_at`, `finished_at`, `text_source`, `text_source_spec`, `language`, and `geolocation`. Success is `200 {}` and creation is asynchronous. |
| Create memories | Supply either `text` for extraction or `memories[]` with required `content` and optional `tags`; `text_source` and `text_source_spec` are optional. Success is `200 {}` and saving/extraction is asynchronous. |
| Read conversations | Paginate with `limit` (default 100, max 1000) and `offset`; optionally use `include_discarded` and comma-separated `statuses`. The response wraps records in `conversations`. |
| Read memories | Paginate with `limit` (default 100, max 1000) and `offset`. The response wraps records in `memories`. |

Do not infer Import fields from personal REST. Keep an application-side import ledger keyed by a stable source identifier because generic Import API idempotency is not documented. An empty success body does not prove that asynchronous creation has completed; reconcile through the read endpoint or Omi app before retrying. A `403` can mean an invalid key, a user-disabled app, or a missing capability. Stop new imports when access is disabled or revoked, and define consent, retention, participant-data, and attachment-minimization rules before rollout. See the [official Import API](https://docs.omi.me/doc/developer/apps/Import).

Validate the user identity, returned `uid`, and requested capability before importing sensitive data.

## OAuth

Omi documents an OAuth 2.0-like enablement flow at `https://api.omi.me/v1/oauth/authorize?app_id=...&state=...`. The app must be registered and have an HTTPS home URL. Generate high-entropy, single-use `state`, bind it to the initiating session, and reject callbacks whose state does not match.

Omi handles the Firebase token exchange internally. The app callback receives only `uid` and `state`; it does not receive an OAuth access token or refresh token. Completing the flow attempts to enable the app. Subsequent Import API calls still use the app's `sk_...` key plus the validated `uid`. Store `uid` as sensitive data and never treat it as authentication proof by itself. See the [official OAuth guide](https://docs.omi.me/doc/developer/apps/Oauth).

## Webhook channels

Omi app Developer Settings configure these channels: Memory Creation, Real-Time Transcript, Audio Bytes, and Day Summary. The reference does not document a REST endpoint for registering them.

- Memory Creation can carry full conversation data. It fires when a memory is created, not as a formally guaranteed “conversation complete” event.
- Real-Time Transcript carries segments with `session_id` and `uid`; the docs tell receivers to handle duplicate segments.
- Audio Bytes are PCM16 binary POST bodies with a configured sample-rate query value.
- Day Summary is scheduled at most once per day when its delivery conditions are met; absence is not necessarily failure. It uses newer `summary_json`; legacy `summary` may be a Python-dict-like string, not JSON. The in-app “Generate Summary” action does not currently POST to the developer webhook.

## Receiver design

The current Omi webhook documentation specifies no signature, authorization header, mTLS requirement, or source-IP allowlist. Treat webhook requests as unauthenticated at the Omi protocol layer. Never authenticate or authorize a caller solely from `uid`, `session_id`, a body ID, or a payload hash.

Use an independently controlled ingress capability supported by the deployment, such as a receiver secret embedded in the configured URL or an equivalent gateway control. Treat this as receiver-side mitigation, not Omi signing. Prevent the secret from entering access logs and rotate it if exposed.

Use HTTPS, enforce a bounded body and timeout, and durably enqueue or persist the minimum needed data before returning a fast 2xx response. Use a documented resource ID for deduplication when present; otherwise use a payload hash only as a replay heuristic, never authentication. Do not send sensitive payloads to public request-inspection services. The docs do not promise retries, ordering, or exactly-once delivery. When an event is missing, reconcile through the corresponding authenticated data surface instead of inventing delivery semantics. See the [official Integration Apps guide](https://docs.omi.me/doc/developer/apps/Integrations).

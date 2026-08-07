# Import API, OAuth, and Webhooks

## Contents

- [Import API](#import-api)
- [OAuth](#oauth)
- [Webhook channels](#webhook-channels)
- [Receiver design](#receiver-design)

## Import API

An enabled third-party app acts for a user with an app key. Do not substitute a personal Developer key. The documented paths are:

```text
POST /v2/integrations/{app_id}/user/conversations?uid={user_id}
POST /v2/integrations/{app_id}/user/memories?uid={user_id}
GET  /v2/integrations/{app_id}/conversations?uid={user_id}
GET  /v2/integrations/{app_id}/memories?uid={user_id}
```

The app key must belong to the matching `app_id`, and the user must explicitly enable the app. Validate the user identity and requested scope before importing sensitive data.

## OAuth

Use `https://api.omi.me/v1/oauth/authorize?app_id=...&state=...`. The app must be registered and have an HTTPS home URL. Generate high-entropy, single-use `state`, bind it to the initiating session, and reject callbacks whose state does not match. Treat callback `uid` as an identifier to validate and authorize, not as proof by itself.

## Webhook channels

Omi app Developer Settings configure these channels: Memory Creation, Real-Time Transcript, Audio Bytes, and Day Summary. The reference does not document a REST endpoint for registering them.

- Memory Creation can carry full conversation data. It fires when a memory is created, not as a formally guaranteed “conversation complete” event.
- Real-Time Transcript carries segments with `session_id` and `uid`.
- Audio Bytes are PCM16 binary POST bodies with a configured sample-rate query value.
- Day Summary uses newer `summary_json`; legacy `summary` may be a Python-dict-like string, not JSON. In-app summary generation is not documented to trigger delivery.

## Receiver design

Use HTTPS, return a fast 2xx response, parse only fields required for the task, protect stored payloads, and record a deduplication key. Do not use public request-inspection services for sensitive payloads. The docs do not promise request signatures, retries, ordering, or exactly-once delivery. When an event is missing, reconcile through the corresponding authenticated data surface instead of inventing delivery semantics.

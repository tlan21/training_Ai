# INT-62 — Clip notifications through Kafka · 2026-11-13 (Claude)

User: "hãy làm 1 luồng thông báo đơn giản qua kafka khi có event được publish gửi thông báo đến user".
Decision (AskUserQuestion): recipients = **client users whose onboarding topics contain the clip's category**
(`coalesce(clip.category_id, video.category_id)`); a clip without any category goes to every client user.

## Flow
```
CMS POST /api/cms/clips/{id}/publish  (draft → published only)
  └─ Kafka topic clip.published  key=clip_id  {clip_id, video_id, published_at}   (Kafka error → logged, publish still 200)
       └─ consumer group gateway-notifications (gateway pipeline)
            └─ re-reads the clip in Postgres (must still be public) → INSERT … ON CONFLICT DO NOTHING into user_notifications
                 └─ GET /api/users/me/notifications (unread_count, cursor) ← client bell, polls every 60 s
                    POST /api/users/me/notifications/read {ids} | {} (all)
```
Idempotent per (user, kind, clip): a redelivered or repeated event never duplicates. Malformed events are dropped (logged) so they
cannot block the partition. The inbox lists only clips that are still public. Out of scope: email/push, WebSocket/SSE.

## Commits
`0b08906` scope · `5bcd779` + `45df8e1` API 0.14.0 contract + types (the paths were missing from the first commit — fixed in the second) ·
`7ca5653` backend (migration 009, producer, consumer, repo, handlers, tests, compose topic init) · `e8a2498` client bell ·
`a8d24a1` live spec, evidence, pins, tracker.

## Verified (VERIFIED-NOW)
- Go: vet clean, `go test ./...` all ok (new: `TestPublishEmitsClipPublishedOnce`, `TestClipPublishedConsumerDropsMalformedEvents`,
  `TestNotificationMarkReadValidation`); real-PG **16/16** (`pg_real_tests.txt`, new `TestNotificationRepository_RealFanOutRecipientsAndInbox`:
  category recipients, admin excluded, no-category → all clients, redelivery 0 new, draft 0, cursor, mark one/all, other user's id ignored,
  unpublished clip leaves the inbox).
- Client: tsc 0 errors, lint 0 errors (pre-existing warning), Linux image build (lint + build + tsc) OK; fixture suite **94/94**.
- Live (`e2e/client_notifications_live.spec.ts`, opt-in) **3/3** on the real stack: QA category/video/draft clip + 2 QA client users
  (one with the QA topic, one without); admin publishes via the CMS API → inbox of the interested user has 1 unread notification after
  **~1.7 s** (`live/steps.json` of the first passing run), the other user has none, re-publish adds nothing; consumer log
  `live/consumer_log.txt` (`clip.published clp_int62_…: 1 notifications`); bell badge + panel at 390 (discover header — the mobile feed is a
  full-screen player without the bell, Stitch) and 1440, click opens the clip and marks it read (`live/bell-*.png`).
- Live run side effect: the QA clip was publicly visible for ~10 s during each run. QA users/category/video/clip/notifications deleted
  afterwards; `live_manifest_before.txt` = `live_manifest_after.txt`.

## Deploy
- Migration 009 applied twice to the live DB (`manifest_after_migration009.txt` = INT-61 end state + empty `user_notifications`; no
  before-file was written for this step — the INT-61 after-manifest is the reference). Also appended to `init/001_schema.sql`.
- Kafka topic `clip.published` created on the live broker (`kafka-topics --create --if-not-exists`, 1 partition); added to the compose init job.
- `video-ai-gateway:int62-e8a2498` (overlay of int61-017d1c6), `video-ai-client:int62-e8a2498` (overlay of int11-843a56e, `.next` rebuilt in
  Linux); pins in `docker-compose.cms-completion.yml`; gateway env hash `56e23179db570721` unchanged; rollback = int61 tags.

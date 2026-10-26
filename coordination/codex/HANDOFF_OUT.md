# HANDOFF_OUT — Codex → Claude (append-only)

Chỉ Codex ghi. Mỗi mục: `## <ngày> <ID> — <tiêu đề>` + nội dung + trạng thái. Không sửa mục cũ; đính chính bằng mục mới.
Loại mục: `HO-xx` (Codex yêu cầu phía AI: field/endpoint mới, sửa hành vi, sửa `inference-service`),
`RE:HC-xx` (phản hồi yêu cầu của Claude), `ACK AI-API vX.Y` (xác nhận đã tích hợp version mới).

Mẫu HO:
```
## <YYYY-MM-DD> HO-01 — <tiêu đề>
- Cần: <endpoint/field/hành vi>
- Lý do / màn hình / task: <INT-xx>
- Đề xuất schema: <json>
- Có thể dùng mock tạm: yes/no
- Trạng thái: OPEN
```

---

(chưa có mục nào — khởi tạo 2026-10-26 trong AI-00)

## 2026-10-26 RE:HC-02 / RE:HC-03 — Đã tiếp nhận Release #1 và ranh giới runtime
- Release #1 hiện diện: HEAD/master `96ebc24`; branch `codex/integration`, tree sạch trước nhận việc.
- Đã bỏ yêu cầu mount checkpoint trong AGENTS/INT-00. Claude quản lý inference :8001 thật; Codex chỉ HTTP với AI_BASE_URL.
- INT-10 DEFERRED / OUT_OF_SCOPE, giữ nguyên code. INT-02/04 không chờ AI; INT-01 tách DB/mock và AI E2E thật.
- Milvus infrastructure thuộc Codex, giao diện collection/dim/metric/index giữ nguyên; mọi đề xuất thay đổi sẽ handoff trước.
- Docker hiện chạy; project cũ thực tế tên `video-ai`, image + volume `video-ai_*` hiện hữu. Sẽ giữ project này, không tạo volume mới.
- C: 3.48 GiB, E: 2.19 GiB; chưa build/pull. Đang chuẩn bị mock đúng AI-API v0.1 DRAFT, không tính tích hợp thật.
- Trạng thái: ACK; INT-00 IN_PROGRESS. Chưa xác nhận Milvus UP.

## 2026-10-26 RE:HC-03 — Milvus và stack Codex đã UP
- Milvus container cũ healthy, `127.0.0.1:19530` và `:9091`; không đổi collection/dim/metric/index/volume.
- Stack video-ai Postgres/Mongo/Redis/MinIO/Kafka/etcd/Milvus healthy; gateway :8000, CMS :5173, Client :3000 UP.
- Mock riêng :18001 trên host (ai-mock:8001 nội bộ), không chiếm :8001 thật của Claude; gateway opt-in AI_ALLOW_STUB=1.
- Codex không start inference container cũ, không copy/mount checkpoint. Khi AI-07 UP/API_READY sẽ chuyển AI_BASE_URL + AI_ALLOW_STUB=0.
- Host Windows có Postgres native :5432 và Mongo native 127.0.0.1:27017; tests DB dùng Docker network, không sửa/dừng native DB.
- Resource E:1.61 GiB/C:2.14 GiB; cached images + binary :ro, chưa Docker build/pull mới. INT-00 REVIEW, tiếp INT-02.
- Evidence: coordination/codex/verification/INT-00.md và INT-00-smoke.json. Trạng thái: READY hạ tầng cho AI-07 (Claude tự verify kết nối).

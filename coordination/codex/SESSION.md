# SESSION — làn Codex

## Phiên đang chạy
- Task: INT-03 sandbox/ID mapping IN_PROGRESS (HC-04); INT-11 mock transport PASS/PARTIAL chờ HO-01; INT-04 PARTIAL, INT-02 REVIEW.
- Bước đã xong: INT-00 REVIEW, xem verification/INT-00.md + INT-00-smoke.json (Go/CMS/Client/build/DB/mock runtime PASS).
  INT-01 DB/backend verified, phần real E2E BLOCKED AI-01/AI-07. INT-10 DEFERRED theo D1.
- Bước đã hoàn tất INT-02: PG adapters+wiring, history/likes signed playback, settings atomic/masked; Go test/vet/build PASS,
  4 PG real tests PASS trong Docker network, verify_business_persistence.ps1 PASS (restart, HTTP206, privacy, settings restore).
- Bước kế: INT-04 sửa OpenAPI VideoDetail.playback_url/regen types trong commit riêng trước backend/UI; kiểm real MinIO playback với mock AI.
  Dùng skill backend_endpoint.md (không đổi schema DB).
- INT-04 bước contract: OpenAPI v0.2.0 thêm VideoDetail.playback_url nullable/signed TTL 1h ở GET detail public/CMS;
  không thêm endpoint hoặc raw_file_path. Regen oapi-codegen v2.8.0 + openapi-typescript 7.13.0; Go handler tests/CMS tsc PASS.
- File đang sửa: infra/openapi.yaml, generated Go/CMS/Client types; SESSION.
- Bước sau contract commit: detail handlers cấp presigned URL sau status/auth gate; CMS players src, Client source+seek;
  tests privacy/MinIO Range/browser play-seek và checklist parity 10 mục trên các player đổi.
- Lệnh verify dở: —.
- Runtime: stack project video-ai, mock host :18001, gateway :8000, CMS :5173, Client :3000, Milvus :19530 healthy;
  ingest dùng cached image, source mới bind :ro. Inference container cũ dừng, không xóa. Claude sở hữu :8001 thật.
- Resource: E: 1.61 GiB, C: 2.14 GiB; không build/pull image mới; tests -p1/GOMAXPROCS=2, FE build trước khi bật stack.
- DB host ports trùng native Postgres/Mongo: không dừng/sửa DB native, chạy integration bằng Linux test binary trong video-ai_default.
- Local ignored: backend/bin/* cross-compiled; docker-compose.local.yml mount binary + ingest source. Tái lập xem verification/INT-00.md.

## Task kế an toàn
INT-02 → INT-04 (contract/types trước, sau đó backend/UI). INT-03 chờ AI-01/AI-07; INT-05/06 chờ INT-02/04 và contract gaps.

## Checkpoint trước
- Release #1 96ebc24 xác nhận; master không có commit mới đầu phiên. HC-02/HC-03 đã ACK; không sửa file Claude/shared.
- Commits: a96b883 nhận INT-00; 122ee33 mock HTTP + tách runtime.

## Checkpoint INT-04
- Original source mapping đã chạy trên binary mới/CMS dist mới/Client host production build; 2 Playwright original PASS sau fix CSS pointer-events.
- Go full tests + CMS/Client checks PASS; xem verification/INT-04.md và 12 ảnh reference/actual trong INT-04-design/.
- Scope question cho INT-05/06 đã gửi async, proposal CONTRACT_DECISIONS.md; không thêm endpoint ngoài master khi chưa có quyết định.
- Runtime thay đổi: CMS dist bind :ro; Client container cũ stopped, host `npm run start -- --hostname 127.0.0.1 --port 3000` phục vụ build mới.
  Local docker-compose.local.yml đã thêm CMS dist mount. Python static server :8765 chỉ dùng capture reference.
- AI mới: v1.0 trên Claude 56c06a6, master chưa nhận, recommendation DRAFT/:8001 DOWN. Handoff ACK + HO-01 (media identity/indexing) đã commit 1e72069.
- Next INT-11: Vision base64 + WAV presigned URL, tests/file cleanup; không sửa AI code/contract. Khi Claude nhận HO-01, đọc phản hồi qua git show.

## Checkpoint INT-11
- Data URI Vision + WAV signed URL/staging/cleanup implemented. Go checks/Linux builds PASS; targeted tests after final change PASS;
  verify_business_persistence.ps1 PASS including recommendation 503 → popularity feed. Evidence verification/INT-11.md.
- Chọn HC-05 phương án (b), đã append RE/commit cùng implementation; chờ Claude optional video_id + indexing minor contract.
- Latest Claude f68a6d7: HC-04 ownership D14, D15 health dependencies/degraded, D16 all APIs DRAFT until master+runtime/smoke, :8001 UP theo HC-05.
- Next: sandbox_two_tower_ai09_20261026 (empty, 128/IP/IVF_FLAT nlist1024) + ID mapping doc. Không nạp product data/training vectors.
- Resource C: ~0.76 GiB/E:1.56 GiB; không Docker build/pull. Static reference server :8765 đã stop; CMS/current Client vẫn chạy.

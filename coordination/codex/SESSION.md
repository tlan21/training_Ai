# SESSION — làn Codex

## Phiên đang chạy
- Task: INT-04 IN_PROGRESS (2026-10-26); INT-02 REVIEW tại 7efe2c9.
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

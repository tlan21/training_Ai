# AI-07 evidence — 2026-10-26 (VERIFIED-NOW)

Runtime thật :8001: `inference-service/run_local_8001.cmd` chạy bằng `Start-Process` (tiến trình Windows độc lập, PID 26396), startup production
(`FORCE_STUB=0`, checkpoint canonical, Milvus stack Codex), **không** đặt `PYTHONUTF8`/`PYTHONIOENCODING`. CPU (`device=cpu`).

1. UTF-8 Windows: `tests/test_stdout_encoding.py` (subprocess, stdout pipe, `-X utf8=0`) RED `UnicodeEncodeError: 'charmap' codec can't encode character '\u1ed7'`
   → sửa `app/__init__.py` (reconfigure stdout/stderr UTF-8) → GREEN. `suite_default_no_utf8_env.txt`: 47 passed, 7 skipped (shell không có PYTHONUTF8).
   Log runtime: 0 dòng `UnicodeEncodeError` sau smoke có request lỗi (asr file thiếu, highlight lệch, vision 422, 401).
2. Startup `runtime_8001_startup.log`: Application startup complete → 6 checkpoint + Milvus `video_frame_embeddings` + search warmup OK.
3. Smoke :8001 — `live_smoke_8001_real.txt` (media thật, sinh lại `examples/`) 6/6 PASS; `live_smoke_8001_synthetic.txt` 6/6 PASS.
4. `/health` sau smoke (`health_after_smoke.json`): `stub_mode=false`, 6 model, `degraded=[]`,
   `dependencies={recommendation_index: missing_collection, visual_index: ok}`.
5. Từ container Codex (chỉ đọc): `docker exec video-ai-gateway-1 wget -qO- http://host.docker.internal:8001/health` → JSON trên, exit 0.

Kết quả từng model (D16, không READY model chưa chạy):

| Model | Loading | Endpoint qua :8001 | Error handling kiểm | Ghi chú |
|---|---|---|---|---|
| vit | ✓ | vision 200 (3 frame thật → `tin_tuc`, 3×256) | 422 thiếu keyframes | index frame từ ingest ⇐ HC-05 |
| asr_ctc | ✓ | asr 200 (WAV 10 s) | 503 file thiếu, không degraded | chất lượng video thật kém (AI-02) |
| highlight_fusion | ✓ | highlight 200 (3 s, 256+64) | 503 lệch số giây, không degraded | |
| minigpt | ✓ | completions 200 | 401 thiếu Bearer | chất lượng 1.6/5 (AI-03) |
| siamese | ✓ | search 200 (Milvus thật, top-5) | 422 top_k=0 | |
| two_tower | ✓ (nạp) | recommendation **503** (collection chưa có) | dependency `missing_collection`, không degraded | **chưa READY** — D14 (AI-09 + HC-04) |

Giới hạn: VRAM ≤4 GB chưa đo (máy không có GPU torch; AI-04/RTX 3060). Ingest end-to-end ⇐ HC-05.

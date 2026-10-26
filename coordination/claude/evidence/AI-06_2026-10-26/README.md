# AI-06 evidence — 2026-10-26 (VERIFIED-NOW)

Máy: Windows 11, CPU (torch 2.13.0+cpu, `cuda.is_available()=False`), Python 3.11.14 `.venv`. Milvus `localhost:19530` TẮT (stack Codex chưa chạy).
File tạm (frame/wav/response đầy đủ) ở `D:/tmp/ai06_20261026/` — không phải dữ liệu dự án, xóa được.

## 1. Nguồn checkpoint (lệnh: `find D:/ E:/ -name '*.pt|*.pth|*.ckpt|*.safetensors' -size +500k` + `sha256sum`)

142 file trọng số tìm thấy; SHA của mọi bản vit/minigpt + 2 thư mục checkpoint: `sha256_vit_minigpt_and_checkpoint_dirs.txt`.

| Model | SHA active (contract §1) | Bản trùng SHA | Gốc |
|---|---|---|---|
| vit | `192d90e4…` | `E:/traning_ai/ai-core/checkpoints/vit/best.pt`, `E:/traning_ai/dist/kaggle/output/vit/vit_s1338/vit/best.pt` | Kaggle ViT seed 1338 (`dist/kaggle/output/vit/vit_s1338`). **Không có bản nào trên D:.** Các bản vit khác (`vit_s1337`, `vit_s1339`, `E:/tmp_vit_smoke/**`) SHA khác → không phải active. |
| minigpt | `cf9cfa71…` | `E:/traning_ai/ai-core/checkpoints/minigpt/best.pt`, `D:/data_training_ai/minigpt_news/output-v2/news_run/minigpt/best.pt` (= `news_run/asr/minigpt/best.pt`), 4 bản `pretrain.pt` upload (aligned_v1_reserve, aligned_v2, aligned_training_upload, mixed_replay_upload) | Kaggle news fine-tune output-v2 (`news_run`, nhánh asr). `bpe_vocab.json` E: ≡ D: news_run (`649ffc66…`). Candidate `5cc63c26…`, `70ec4790…` vẫn tách riêng, không active. |

4 model trùng tên D: (`D:/data_training_ai/checkpoints`) ↔ E: (`E:/traning_ai/ai-core/checkpoints`): best.pt **và** last.pt trùng SHA cả 4
(asr_ctc `8f879867…`, highlight_fusion `becbd378…`, siamese `b4ded465…`, two_tower `f28c3794…`).
Sau AI-06: `sha256sum -c` lại 8 file trên D: → 8/8 OK (không ghi/xóa gì trên D:).

**Canonical:** `E:/traning_ai/ai-core/checkpoints` (= default `../ai-core/checkpoints` của `app/config.py`) — thư mục duy nhất đủ 6 best.pt +
`minigpt/bpe_vocab.json`, nằm trong worktree chạy runtime :8001. `D:/data_training_ai/checkpoints` = mirror 4/6, giữ nguyên, không dùng cho runtime.

## 2. HTTP thật (uvicorn + Bearer)

- Startup production (`python -m uvicorn app.main:app`, `FORCE_STUB=0`) khi Milvus tắt → **fail** (`prod_startup_no_milvus.log`, exit 3):
  lifespan `main.py:22-26` gọi `visual_index.collection()` → `MilvusException ... localhost:19530`.
- Vì vậy đo ENDPOINT_OK bằng `launch_no_milvus_preflight.py`: cùng `app.main:app`, checkpoint thật, chỉ bỏ **lần gọi đầu** `visual_index.collection()`
  trong lifespan; mọi lần sau (search) đi đường thật. Lệnh:
  ```
  PYTHONUTF8=1 .venv/Scripts/python coordination/claude/evidence/AI-06_2026-10-26/launch_no_milvus_preflight.py 8011
  PYTHONIOENCODING=utf-8 .venv/Scripts/python coordination/claude/evidence/AI-06_2026-10-26/http_ladder.py http://127.0.0.1:8011
  ```
- Kết quả `ladder_stdout.txt`: **9/9 PASS** — health `stub_mode=False`, 6 model, `degraded=[]`; 401 thiếu/sai Bearer; vision 10 frame → `tin_tuc` + 10×256;
  ASR 10 s → 5 segment; highlight 10 s (256-d + 64-d) → 10 điểm 0–100; completions 42→28 token; search/recommendation 503 `AI_UNAVAILABLE` (Milvus tắt).
  Response validate bằng `app.schemas.*Response`. Input: 10 frame + 10 s audio cắt từ `minigpt_domain_v1_20261019/raw/youtube/-1Is0o2ZWk0.mp4` (60–70 s).
- `pytest inference-service/tests` → 37 passed, 1 skipped.

## 3. Lỗi phát hiện

- Lần chạy đầu không có `PYTHONUTF8=1`: search trả **HTTP 500 plain-text** thay vì 503 envelope. Nguyên nhân: `services._warn` (`services.py:23`)
  `print` tiếng Việt; stdout redirect ra file trên Windows dùng cp1252 → `UnicodeEncodeError` trong handler. Không ảnh hưởng Docker/Linux (UTF-8).
  Xử lý vận hành: chạy service với `PYTHONUTF8=1` (ghi `inference-service/README.md`). Không sửa code trong AI-06.
- Chất lượng (không thuộc thang sẵn sàng): transcript ASR trên clip thật nhiều lỗi (đã biết, AI-02).

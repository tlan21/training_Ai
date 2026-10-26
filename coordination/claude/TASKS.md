# TASKS — làn Claude (AI) · branch `claude/ai-core`

Owner duy nhất: Claude. Codex chỉ đọc (`git show claude/ai-core:coordination/claude/TASKS.md`).
Định dạng + trạng thái: `coordination/README.md` mục 4. Kiểm kê gốc: `coordination/INVENTORY_2026-10-26.md`.

## Tổng quan

| ID | T gốc | Tên | Status | Depends on |
|---|---|---|---|---|
| AI-00 | — | Thiết lập tách làn + kiểm kê | DONE | — |
| AI-06 | T1.8 | **Ưu tiên 1** — Xác minh nguồn checkpoint + thang sẵn sàng 6 model | DONE (2026-10-26) | — |
| AI-01 | T1.8 | Phát hành AI API Contract v1 (API_READY) | TODO | AI-06 |
| AI-07 | T1.8 | Vận hành runtime :8001 thật cho Codex gọi HTTP | TODO | AI-06; Milvus từ stack Codex (HC-02) |
| AI-02 | T1.4 | ASR domain: 02a đề xuất 53 clip · 02b người duyệt · 02c intake/train | 02a TODO · 02b BLOCKED · 02c BLOCKED | 02b ⇐ user; 02c ⇐ 02b |
| AI-03 | T1.6 | Mini-GPT: 03a Claude soạn summary 40 clip · 03b người duyệt · 03c train/eval | 03a TODO · 03b BLOCKED · 03c BLOCKED | 03b ⇐ user; 03c ⇐ 03b |
| AI-04 | T1.8 / T4.3 | Đo VRAM sơ bộ Kaggle T4 (PRELIMINARY) | TODO | AI-06 |
| AI-05 | T5.3 | Số liệu evaluation cho luận án | TODO | AI-02, AI-03, AI-04 |
| AI-08 | — | Dọn dẹp dữ liệu/artefact làn AI an toàn (lặp lại sau mỗi đợt train) | TODO (đợt #1 DONE 2026-10-26) | không job/server nào đang dùng; user duyệt danh sách |

Thứ tự đề xuất (tối đa 1 IN_PROGRESS): AI-06 → AI-01 → AI-07; khi chờ GPU/Kaggle/người duyệt thì xen AI-03a, AI-02a, AI-04.
AI-08 (dọn dẹp) chạy sau mỗi đợt train xong hoặc khi một ổ chạm `BLOCKED_RESOURCE`; luôn qua manifest + user duyệt.

Hoàn thành trước tách làn (bằng chứng ở INVENTORY mục 3, 5): T1.1, T1.2, T1.3, T1.4 (DoD metric), T1.5, T1.7 = DONE;
T1.6, T1.8, T4.3 = PARTIAL. Không tạo lại các task này.

Quyết định user 2026-10-26 áp dụng cho làn này: AI-02 (Claude chỉ chuẩn bị/đề xuất, không tự HUMAN_VERIFIED), AI-03 (Claude soạn 40 summary, lưu nguồn/bằng chứng/trạng thái duyệt, không dùng dữ liệu giả để DONE), AI-04 (Kaggle T4 chỉ là sơ bộ, không thay nghiệm thu RTX 3060), AI-06 (ưu tiên; phân biệt 4 mức sẵn sàng, không API_READY khi chưa kiểm chứng). Xem `coordination/PROJECT_STATUS.md` mục 5.

Nhãn kiểm duyệt dữ liệu (AI-02/AI-03): `MACHINE_DRAFT` (máy sinh: Whisper/ASR) · `CLAUDE_PROPOSED` (Claude đề xuất/soạn) · `HUMAN_VERIFIED` (chỉ user/người duyệt gán, có file export làm bằng chứng) · `REJECTED`.

---

### AI-00 — Thiết lập tách làn + kiểm kê
- T gốc: — | Owner: claude | Status: DONE
- Depends on: — | Blocks: mọi task AI-xx, INT-xx
- Acceptance: `coordination/**`, `AGENTS.md`, `.claude/CLAUDE.md`, master plan §0/§3 đồng bộ; 2 worktree/branch; kiểm kê có bằng chứng.
- Evidence: VERIFIED-NOW 2026-10-26 — ai-core 285 passed, inference 37 passed/1 skipped, 6 ckpt nạp thật, Go/CMS/Client build PASS (INVENTORY §1).
- Commits: commit baseline tách làn (`git log --grep "split lanes"`)
- Checkpoint: xem SESSION.md

### AI-01 — Phát hành AI API Contract v1
- T gốc: T1.8 | Owner: claude | Status: TODO
- Depends on: AI-06 | Blocks: INT-03 (DONE), mọi dòng `INTEGRATED_REAL` mới trong matrix Codex
- Acceptance:
  1. `coordination/claude/api/inference_openapi.json` export từ `app.main:app.openapi()` (không sửa tay).
  2. `coordination/claude/api/examples/<endpoint>.{request,response,error}.json` sinh từ chạy thật checkpoint thật cho 6 endpoint + `/health` (search/recommendation cần Milvus — chạy khi Codex bật stack, hoặc ghi rõ chưa có).
  3. `AI_API_CONTRACT.md` → v1.0: mọi endpoint có schema, ràng buộc chiều (vision 256-d, audio 64-d…), error codes, model + SHA256, `API_READY` cho endpoint đã có ví dụ thật.
  4. Smoke checkpoint thật đưa vào `inference-service/tests` (opt-in theo env) để release gate chạy lại được.
  5. Append bàn giao vào `coordination/claude/HANDOFF_OUT.md`.
- Evidence: — | Commits: — | Checkpoint: —

### AI-02 — ASR domain adaptation (T1.4 follow-up)
- T gốc: T1.4 | Owner: claude | Status: 02a TODO · 02b BLOCKED · 02c BLOCKED
- Tiến độ duyệt (ghi 2026-10-26): **7/60 đã duyệt, 53/60 còn phải kiểm tra** — số 7/60 là tiến độ trang review hiển thị
  (lưu localStorage Chrome, `http://127.0.0.1:8891/asr_review_v2/index.html`); **chưa có file JSON export** nào
  (Downloads không có `asr_expansion_review_v2*.json`) → bằng chứng file hiện là 0/60. Gói dữ liệu:
  `D:/data_training_ai/asr_domain_expansion_v2_20261022/` (60 WAV/MP4 20 s, 180 bản nháp Whisper = `MACHINE_DRAFT`).
- **AI-02a — Claude chuẩn bị + đề xuất (TODO):** cho 53 clip chưa duyệt, ưu tiên 9 clip trùng lời máy + 25 clip bị cờ:
  đề xuất sửa chữ/chuẩn hóa theo `docs/T1.4_asr_label_contract.md`, ghi lý do, nhãn `CLAUDE_PROPOSED` trong file riêng
  (không ghi đè nháp gốc, không ghi vào kết quả duyệt của user). Claude không nghe được audio → đề xuất chỉ dựa trên văn bản,
  phải ghi rõ giới hạn này. Acceptance: file đề xuất + hash nguồn + test strict-intake vẫn từ chối mục chưa `HUMAN_VERIFIED`.
- **AI-02b — người duyệt (BLOCKED ⇐ user):** user nghe/sửa/xác nhận hoặc loại từng clip, xuất JSON thật. Chỉ mục user xác nhận
  mới là `HUMAN_VERIFIED`. Claude **không** tự gán.
- **AI-02c — intake + train (BLOCKED ⇐ 02b):** strict intake giữ machine-assisted provenance/coverage/train-only vocab/CTC/split guard;
  1 thí nghiệm bounded; chỉ promote khi guard VIVOS/FLEURS/domain không hồi quy; không chọn theo test.
- Blocks: AI-05; chất lượng phụ đề video thật phía Codex (không chặn tích hợp kỹ thuật).
- Evidence: lịch sử bên dưới + `docs/T1.4_*.md`. Checkpoint active `8f87986781cf…` giữ nguyên (HOLD PROMOTION).
- Commits: `15976b3` (trước tách làn)
- Checkpoint: Next safe task = AI-02a (không phụ thuộc user); 02b chờ user.

### AI-03 — Mini-GPT human quality gate (T1.6)
- T gốc: T1.6 | Owner: claude | Status: 03a TODO · 03b BLOCKED · 03c BLOCKED
- Nguồn 40 clip real-domain (30 train / 10 val, ngoài frozen30): `data/manifests/minigpt_real_domain.json`; transcript user đã rà
  (export SHA `860f8068d0bd…`, 40 transcript/39 sửa) — `docs/T1.6_whisper_review_intake.md`.
- **AI-03a — Claude soạn summary 40 clip (TODO, theo quyết định user 2026-10-26):** soạn từ transcript user đã rà; mỗi mục lưu
  clip ID, hash media + hash transcript nguồn, văn bản summary, số BPE token (≤95), người/công cụ tạo = Claude + ngày,
  nhãn `CLAUDE_PROPOSED`. Lưu file riêng trên D: + manifest `data/manifests/` + báo cáo `docs/T1.6_*`; không ghi đè dữ liệu cũ.
  Acceptance: đủ 40 mục, hash khớp nguồn, strict intake từ chối dùng làm target khi chưa `HUMAN_VERIFIED`.
- **AI-03b — người duyệt (BLOCKED ⇐ user):** user duyệt/sửa/loại từng summary → `HUMAN_VERIFIED`.
  ⚠ Ràng buộc dự án (`my-agent/agent/instructions.md` §1: "không pseudo-label từ model ngoài"): summary do Claude soạn là
  output của model ngoài → chỉ được làm target train/eval sau khi người duyệt từng mục **và** provenance ghi rõ
  `claude_drafted_human_verified`. Mục chưa duyệt không bao giờ được dùng.
- **AI-03c — train/eval bounded (BLOCKED ⇐ 03b):** guard clean+ASR không hồi quy; cổng cuối vẫn là human mean ≥3/5 trên video thật
  mới, điểm do người chấm (summary Claude soạn **không** thay điểm chấm của người). Không tune trên frozen test, không hạ ngưỡng.
- Blocks: AI-05; chất lượng summary phía Codex (không chặn tích hợp kỹ thuật).
- Evidence: ROUGE-L News PASS (0.2023 vs 0.1871), shared human 1.6/5 FAIL. Candidate mixed300 `70ec4790…` giữ riêng; active `cf9cfa71…`.
- Commits: `15976b3`
- Checkpoint: Next safe task = AI-03a.

### AI-04 — Đo VRAM sơ bộ trên Kaggle T4 (AI-GATE điều kiện 4, T4.3 phần GPU)
- T gốc: T1.8, T4.3 | Owner: claude | Status: TODO (sơ bộ được user cho phép 2026-10-26)
- Depends on: AI-06 (đúng 6 checkpoint active + SHA). Máy local chỉ Intel UHD 630.
- Cách đo: notebook Kaggle private, GPU T4; nạp đúng 6 checkpoint active (SHA khớp contract) + 20 request tuần tự đủ 6 loại,
  đo `torch.cuda.max_memory_allocated/reserved` sau nạp và sau mỗi request; tải output về trước khi push version kế
  (memory: Kaggle chỉ giữ output bản mới nhất).
- Acceptance (PRELIMINARY): báo cáo `docs/T4.3_bao_cao.md` ghi rõ GPU (T4 16 GB), driver/CUDA, torch, dtype (fp16/fp32), batch,
  danh sách request, số đo peak/tail; kết luận ghi nhãn `PRELIMINARY_T4`.
- **Không thay nghiệm thu:** AI-GATE điều kiện 4 và T4.3 vẫn `PARTIAL` cho tới khi đo trên RTX 3060 (hoặc user duyệt riêng kết quả T4
  thay thế). T4 không chứng minh hành vi trên 3060 12 GB.
- Blocks: INT-07 (T5.1 GPU) chỉ ở mức nghiệm thu cuối; Codex có thể chạy bản CPU trước.
- Evidence: HIST CPU RSS 20 video PASS (`docs/T4.3_bao_cao.md`); GPU chưa đo.
- Commits: — | Checkpoint: —

### AI-07 — Vận hành runtime :8001 thật cho Codex
- T gốc: T1.8 | Owner: claude | Status: TODO
- Lý do: quyết định user 2026-10-26 — Codex không sao chép/quản lý checkpoint; tích hợp AI chỉ qua HTTP :8001.
  → Claude sở hữu tiến trình inference-service chạy checkpoint thật.
- Depends on: AI-06; Milvus từ stack Codex lắng nghe `localhost:19530` (HC-02). | Blocks: INT-01 (phần E2E thật), INT-03.
- Acceptance: lệnh chạy chuẩn (uvicorn từ worktree Claude, `CHECKPOINT_DIR` canonical, `MILVUS_HOST` của stack Codex, port 8001,
  `AI_SERVICE_KEY` dùng chung với gateway) ghi trong contract mục Runtime; `GET :8001/health` → `stub_mode=false`, 6 model;
  trạng thái runtime (UP/DOWN + thời điểm) ghi `SESSION.md`. Khi :8001 DOWN, Codex dùng mock — không chặn nhau.
- Evidence: — | Commits: — | Checkpoint: —

### AI-05 — Số liệu evaluation luận án (T5.3 phần AI)
- T gốc: T5.3 | Owner: claude | Status: TODO
- Depends on: AI-02, AI-03, AI-04 (hoặc dùng số thật hiện có nếu user chốt dừng thí nghiệm)
- Acceptance: bảng metric 6 model vs baseline, CI, limitation thật, khớp `.claude/evaluation_plan.md`.
- Evidence: — | Commits: — | Checkpoint: —

### AI-08 — Dọn dẹp dữ liệu/artefact làn AI an toàn (yêu cầu user 2026-10-26)
- T gốc: — | Owner: claude | Status: TODO (task lặp lại: chạy sau mỗi đợt train xong, hoặc khi một ổ chạm `BLOCKED_RESOURCE`)
- Bối cảnh 2026-10-26: C: còn 3.5 GB, D: 1.2 GB, E: 2.2 GB. Ứng viên đã thấy (nhỏ): `ai-core/_probe_ckpt/` 3.2 MB, `ai-core/_tmp_tt/` 0.7 MB
  (untracked), pytest tmp ~0.7 MB. Khảo sát `D:/data_training_ai` chưa xong (du timeout) → bước 1.
- Mục tiêu: giải phóng dung lượng **mà không mất dữ liệu cần cho phát triển tiếp, tái lập kết quả hoặc luận án**.
  Dọn dẹp không được làm dự án lùi lại: sau dọn, mọi test/smoke/manifest phải còn PASS như trước.
- Phạm vi: chỉ path làn Claude — `ai-core/**` (file không track), `inference-service/**` cache, `data/**`, `dist/kaggle/**`,
  `D:/data_training_ai/**`, file tạm do Claude tạo (pytest tmp, `__pycache__`, `/tmp/split`). **Cấm** đụng path Codex
  (`backend`, `cms`, `client`, `node_modules`, Docker image/volume/vhdx), lịch sử git, `.git`.

**Phân loại bắt buộc (mỗi mục 1 lớp, có lý do):**
| Lớp | Ví dụ | Xử lý |
|---|---|---|
| `KEEP` — không bao giờ xóa | checkpoint active 6 model (`ai-core/checkpoints/*/best.pt`, SHA trong contract); nhãn/review/rating của người (export JSON, ASR review 7/60, transcript user đã sửa, human ratings T1.6); frozen test/val (frozen30, fixed10, VIVOS/FLEURS test refs); `data/manifests/**`; file được docs/report trích làm bằng chứng metric; nguồn không tải lại được (SoccerNet đã xóa video gốc, NDA) | giữ nguyên |
| `ARCHIVE` — cần giữ nhưng không cần trên ổ làm việc | checkpoint ứng viên bị loại nhưng có số liệu trong report (vd ASR last134, MiniGPT candidate `70ec4790…`), output Kaggle các version cũ, gói dữ liệu đã dùng xong | chỉ xóa khỏi ổ làm việc **sau khi** đã có bản sao ở nơi lưu trữ user chỉ định và đã kiểm SHA bản sao |
| `REGENERABLE` — tạo lại được bằng lệnh đã ghi | `__pycache__`, pytest tmp, `_probe_*`/`_tmp_*` scratch, feature/keyframe trung gian còn nguồn gốc + lệnh trích lại, zip packet Kaggle còn source | xóa sau khi ghi lệnh tái tạo + user duyệt |
| `UNKNOWN` | không rõ nguồn gốc/không biết ai dùng | **không xóa**, hỏi user |

**Quy trình (không bỏ bước):**
1. **Điều kiện trước:** không có job train/Kaggle/eval đang chạy; không server nào phục vụ thư mục ứng viên (vd ASR review :8891 dùng
   `D:/data_training_ai/asr_domain_expansion_v2_20261022` → KEEP khi AI-02b chưa xong); output Kaggle mới nhất đã tải về
   (Kaggle chỉ giữ version mới nhất).
2. **Khảo sát chỉ đọc:** kích thước, ngày sửa, số file, SHA256 (file ≤ vài GB; thư mục lớn: danh sách file + size), và **ai tham chiếu**
   (grep path trong `docs/`, `data/manifests/`, `ai-core/`, `inference-service/`, `coordination/`, `.claude/`). Có tham chiếu → không
   được `REGENERABLE` trừ khi tham chiếu chỉ là lịch sử và user đồng ý.
3. **Manifest dọn dẹp:** `coordination/claude/cleanup/CLEANUP_<YYYY-MM-DD>.md` + `.json` (path, size, sha256/file-list, lớp, lý do,
   tham chiếu, lệnh tái tạo nếu có, dung lượng dự kiến giải phóng). Commit trước khi xóa bất cứ gì.
4. **User duyệt từng nhóm** trong manifest. Không duyệt = không xóa.
5. **Thực hiện theo lớp:** `ARCHIVE` → sao chép sang nơi lưu trữ user chỉ định (ổ ngoài/cloud) → kiểm SHA bản sao → mới xóa bản gốc.
   `REGENERABLE` → xóa từng path đã duyệt (không wildcard rộng, không `rm -rf` ở thư mục gốc dự án/ổ, không `git clean`).
   Lưu ý: chuyển vào Recycle Bin hay thư mục `_trash` **cùng ổ không giải phóng dung lượng** — chỉ dùng làm bước đệm khi user muốn
   có thời gian kiểm tra trước khi xóa hẳn.
6. **Kiểm sau dọn:** ai-core pytest + inference pytest PASS; 6 checkpoint nạp `stub_mode=false`, SHA khớp contract; script kiểm mọi path
   trong `data/manifests/*.json` còn tồn tại (hoặc có trong danh sách `ARCHIVE` kèm nơi lưu); ASR review/label tool còn mở được nếu đang dùng.
   Có FAIL → dừng, khôi phục từ bản lưu trữ/trash, báo user.
7. **Ghi kết quả:** dung lượng trước/sau từng ổ, danh sách đã xóa/đã lưu trữ, bằng chứng bước 6 → manifest + Evidence task này.
   Ảnh hưởng tới Codex (vd đổi đường dẫn checkpoint) → append handoff trước khi đổi.

- Acceptance mỗi đợt: manifest đã duyệt, dung lượng giải phóng đo được, bước 6 PASS, 0 mục `KEEP`/`UNKNOWN` bị đụng.
- Không bao giờ: xóa để "cho chắc"; xóa thứ duy nhất chứng minh một con số trong báo cáo/luận án; xóa nhãn người; xóa mà không có
  manifest + duyệt; rewrite lịch sử git để giảm `.git`.
- Đợt #1 (2026-10-26, user uỷ quyền tự quyết): **DONE** — xóa 6 mục REGENERABLE trên D:, giải phóng 5,530,226,688 byte
  (D: 1.22 → 6.75 GB); ai-core 285 PASS, inference 37 PASS/1 skip, SHA 6 checkpoint không đổi, server :8891 HTTP 200.
  Manifest + kết quả: `coordination/claude/cleanup/CLEANUP_2026-10-26.md`. Task vẫn TODO cho các đợt sau.
- Evidence: VERIFIED-NOW 2026-10-26 (đợt #1, xem manifest) | Commits: `a5f340f` (manifest trước khi xóa) + commit kết quả | Checkpoint: SESSION.md

### AI-06 — Xác minh nguồn checkpoint + thang sẵn sàng 6 model (ƯU TIÊN 1)
- T gốc: T1.8 | Owner: claude | Status: DONE (2026-10-26)
- Depends on: — | Blocks: AI-01, AI-04, AI-07
- Vấn đề: `inference-service/.env` (local, không commit) trỏ `CHECKPOINT_DIR=D:/data_training_ai/checkpoints` — thư mục đó chỉ có
  4/6 (`asr_ctc`, `highlight_fusion`, `siamese`, `two_tower`), **thiếu `vit`, `minigpt`** → uvicorn local fail khởi động.
  `E:/traning_ai/ai-core/checkpoints` có đủ 6 (SHA ở INVENTORY §3).
- Việc: (1) xác minh 2 checkpoint thiếu: tìm mọi bản `vit`/`minigpt` trên D:/E: (+ output Kaggle đã tải), so SHA với bản active
  `192d90e4…` / `cf9cfa71…`, ghi bản nào là gốc; (2) so SHA 4 model trùng tên giữa D: và E:; (3) chốt 1 nguồn canonical cho
  local + runtime :8001, sửa `.env` local, ghi `inference-service/README.md`; (4) lập bảng thang sẵn sàng cho từng model.
- Thang sẵn sàng (ghi riêng từng mức, có bằng chứng; mức sau chỉ khi mức trước đạt):
  `DECLARED` (có trong registry) → `CKPT_PRESENT` (file + SHA ở nguồn canonical) → `LOADED` (`registry.load_all`, không degraded) →
  `ENDPOINT_OK` (HTTP thật qua uvicorn, Bearer, response đúng schema) → `API_READY` (chỉ trong AI-01 khi có ví dụ thật đóng gói).
  "AI_READY" trong quyết định user = `API_READY` này. Model chưa kiểm chứng đủ mức → không `API_READY`.
- Acceptance: bảng 6 model × 4 mức đầu với lệnh + output + SHA trong `coordination/claude/api/AI_API_CONTRACT.md` mục 1b;
  không xóa/ghi đè dữ liệu trên D:; search/recommendation ghi rõ mức đạt được nếu Milvus chưa có.
- Evidence (đã có từ AI-00, VERIFIED-NOW 2026-10-26, gọi `app.services` trực tiếp — chưa qua HTTP): 6/6 CKPT_PRESENT + LOADED từ
  `E:/traning_ai/ai-core/checkpoints`; vision/asr/highlight/completions chạy; search/recommendation 503 (Milvus tắt).
- Evidence (AI-06, VERIFIED-NOW 2026-10-26, chi tiết `coordination/claude/evidence/AI-06_2026-10-26/README.md`):
  - `find D:/ E:/ … *.pt` (142 file) + `sha256sum`: vit active `192d90e4…` chỉ ở E: (`ai-core/checkpoints` ≡ `dist/kaggle/output/vit/vit_s1338`, gốc Kaggle seed 1338);
    minigpt active `cf9cfa71…` ở E: ≡ D: `minigpt_news/output-v2/news_run/minigpt/best.pt` (gốc) + 4 `pretrain.pt` upload; vocab `649ffc66…` khớp.
    4 model trùng tên D: ≡ E: (best + last). `sha256sum -c` 8 file D: sau task → 8/8 OK, không ghi/xóa gì trên D:.
  - Canonical = `E:/traning_ai/ai-core/checkpoints`; `.env` local `CHECKPOINT_DIR` đổi từ D: sang đây (không commit); `inference-service/README.md` ghi lại.
  - Startup production `uvicorn app.main:app` khi Milvus tắt → `Application startup failed` (MilvusException localhost:19530), exit 3.
  - Launcher bỏ Milvus preflight + `http_ladder.py` trên :8011 → 9/9 PASS: health `stub_mode=False`/6 model/`degraded=[]`; 401 thiếu+sai Bearer;
    vision/asr/highlight/completions 200 + schema hợp lệ; search/recommendation 503 `AI_UNAVAILABLE`.
  - `pytest inference-service/tests` → 37 passed, 1 skipped.
  - Lỗi vận hành phát hiện: không `PYTHONUTF8=1` trên Windows → `services._warn` UnicodeEncodeError → search 500 plain-text thay vì 503. Ghi README/contract; chưa sửa code.
  - Kết quả thang (contract §1b): vit/asr_ctc/highlight_fusion/minigpt = `ENDPOINT_OK*` (* launcher bỏ Milvus preflight); siamese/two_tower = `LOADED` (cần Milvus).
    Không model nào `API_READY`. Startup production đầy đủ ⇐ Milvus của Codex (AI-07).
- Commits: 91b0242 (nhận task), 8d1f053 (evidence + README + contract v0.2 + REL) | Checkpoint:
  ```
  Lane: claude
  Changed: inference-service/README.md, coordination/claude/{api/AI_API_CONTRACT.md,HANDOFF_OUT.md,TASKS.md,SESSION.md,evidence/AI-06_2026-10-26/**}; .env local (không commit)
  Verified: SHA 6 model + D: 8/8 unchanged; uvicorn HTTP ladder 9/9 PASS; prod startup fail khi Milvus tắt (đúng thiết kế); inference pytest 37 passed/1 skipped
  Contract touched: yes (AI-API v0.2 DRAFT, chỉ tài liệu §1b, schema không đổi)
  Next safe task: AI-01
  ```

---

## Lịch sử (chuyển nguyên văn từ `.claude/plan/00_master_plan.md` ngày 2026-10-26)

Follow-up T1.4/T1.6 trước tách làn. Log chi tiết hơn: `.claude/TodoWrite.md` (đóng băng).

### Từ master §3, các dòng thụt lề dưới T1.4

  ASR robustness follow-up **TRAIN/EVAL DONE — VIDEO VALIDATION PENDING (xác nhận2026-10-19)**: Kaggle ai-core-asr-robust v2 COMPLETE, TeslaT4/FP16/seed1337/4000steps, best3500 theo validation; output đã tải trênD:/data_training_ai/asr_robust/outputs-v2. Paired test VIVOS760: WER36.0519→32.9727%/CER13.5446→12.4467% (PASS20/45); FLEURS857: WER76.7465→53.6727%/CER50.5133→23.9063%, vẫn lỗi cao. VIVOS+human FLEURS train≈22.0073h/13557mẫu sau4CTC exclusions, không dùngYouTube30/Whisper drafts; head93→133 giữ prefix, encoder/loss không đổi. Full logs4sanity+step1→4000, checkpoint/config/metric arithmetic/hashes verified; trainVRAM allocated1.203/reserved3.039GiB≤8, chưa chứng nhận inference4GiB. Candidate SHA d03ef0a962220618e90e5ff478a2fbab5ff35dd68deb539a4933eb7c15a4f3de, chưa deploy; activeASR/MiniGPT giữ nguyên. Chỉ1seed, human video refs0/30; fullT1.6 human quality chưa đánh giá lại. @docs/T1.4_asr_robust_training.md; @data/manifests/asr_robust_training.json.
  Real-video paired pilot **DONE TECHNICAL / HUMAN REFERENCES PENDING (2026-10-19)**: sample_01/10/28×ASR cũ/candidate→cùngMiniGPT,6ASR+6summary nonempty, oldASR text3/3 khớp frozen; production helpers/20s/CPUFP32/Torch2.13/temp0/max96, không deploy. Packet D:/data_training_ai/minigpt_real_video_20261015/asr_candidate_comparison_3_20261019/review.html có video/side-by-side/form lời chuẩn+exportCSV riêng; model/media/ref/ratings SHA giữ nguyên. 3tests+browser playback/exportCSV Unicode/desktop+mobile/QC+Go/CMS/Client FULL PASS. Candidate còn transcript nhiễu; MiniGPT vẫn lặp/thêm chi tiết ngoài transcript. Humanrefs0/3 và0/30, CER/WER/điểm human mới null; sharedmean1.6/5/fullT1.6 chưa đổi. @docs/T1.4_asr_candidate_video_pilot.md.
  User feedback + direct-draft control (2026-10-19): user xác nhận đúng nội dung3draft; candidate-ASR MiniGPT card1/3sai,card2đúng. Chạy trực tiếp chính3draft→cùngMiniGPT/temp0/max96 vẫn lỗi: sample10lặp an ninh, sample28lệch tiểu sửNewton;3outputs tái lập cached summaries. Giữ rawfeedback+scopedjudgments, không suy thành điểm1–5/rawASRaccuracy/CER-WERđộc lập; không train/deploy hoặc sửa original refs/weights. @docs/T1.6_confirmed_draft_diagnostic.md.
  MiniGPT pipeline diagnostic **DONE (2026-10-19)**:3draft222/250/271BPEtokens<411, lỗi xảy ra single-pass. Real BPE prefix253train+8val/mask-EOS8val/cachefullforward8steps PASS; audit256train/253sum:144source và11target bị cắt. Train75581sum/303581instances nhưng checkpoint selection chỉ titleROUGE; fixedval129–136sumRL0.174967 vsLead0.209702 (8mẫu chẩn đoán, không globalmetric),3longinputs rawtoken coverage PASS nhưng1reduce lặp94.68%trigram; short inputs vẫn sai ngày/số/entity. No test tuning/weight/production/contract change;16Python tests+4subtests, Go/CMS/Client PASS; Docker engine off. Next: grounded human target dataset/complete labels +sum-based selection +separate long-input quality, chưa tự train/deploy; fullT1.6 vẫn FAIL. @docs/T1.6_pipeline_diagnostic.md; @data/manifests/minigpt_pipeline_diagnostic.json.
  Summary data/recipe **PREPARATION DONE — LABEL AUDIT PENDING (2026-10-19)**: strictscreen76k/4k→391/24; pinnedrawprefix197135rows adds593/40, final984train/64val, preserve originalsplits/reservehash95/5/exclude1000frozenIDs fromIDindex only. Editorialbody/sapo +syntheticASR, no generated/video-test labels/source-target truncation. New opt-in sum-aligned-v1 chooses pairedclean/noisy sumRL, title/cap regression;4clean+1noisypasses=248/62steps/eval62, legacyprofile unchanged. Existingcheckpoint baseline64cases cleanRL0.290132 vsLead0.407114, noisy0.175906 vs0.115482, mean0.233019 (developmentonly/noimprovementclaim). 8384itemchecks/4productionparity/31tests+4subtests/Go/CMS/Client PASS. 48blankauditrows gate training; privatebundle/codezip/owninitcopy verified, noKagglejob/deploy/model/APIchange. Next: human label audit +resolve/reversion/provenance, then smallcandidate train; realtranscriptdomaintransfer unproven/fullT1.6 stillFAIL. @docs/T1.6_aligned_summary_preparation.md; @data/manifests/minigpt_aligned_summary.json.
  Label preflight follow-up **V2 DATA DONE / HUMAN AUDIT PENDING (2026-10-19)**: previous ending check admitted terminal ../.../Unicode ellipsis; corrected shared filter/trainer gate rejects50train+3val. V2=956train/64val, all53 excluded, retained IDs keep split/61val retained+3new, original files/hashes preserved. 4CPU sanity items+41tests/4subtests+8160encodedchecks/4productionparity+Go/CMS/Client PASS. Unchanged checkpoint baseline cleanSumRL0.294504 vsLead0.415168/noisy0.173516 vs0.114252; no trained improvement claim. Budget240/60/eval60. Mechanical evidence48 stored separately, no human verdicts filled;48blankannotations still gate candidate training. No job/deploy/model/API/frozen-eval change; fullT1.6 stillFAIL. @docs/T1.6_label_preflight.md; @data/manifests/minigpt_label_preflight.json.

### Từ master cuối file (sau §5.4)

Follow-up 2026-10-19 — **ALIGNED CANDIDATE TRAIN/EVAL DONE; ASR REGRESSION / NOT DEPLOYED**. User confirmed48v2 pairs via chat with exact ID/hash provenance;956train/64val, seed1337,240clean+60ASR,5validation rounds; private Kaggle ai-core-minigpt-aligned-v2 version1 COMPLETE, output downloaded/verified. Predeclared paired-mean selection chose clean180: clean ROUGE-L0.292511→0.517913, synthetic-ASR0.172177→0.114637; noisy repetition/cap hits increased. No quality PASS from mean improvement; fullT1.6 human gate unmet, shared1.6/5 unchanged. T4 allocated1.055/reserved2.520GiB,507.8s baseline+train/validation,4remote sanity+50local tests/4subtests+Go/CMS/Client PASS. Six post-selection video-control outputs still show ASR failure; no new human score. Candidate5cc63c... retained separately, activecf9cfa... unchanged. Report @docs/T1.6_aligned_training.md, curves/metrics/manifests updated. Next: mixed clean+ASR replay and per-condition non-regression guard; reuse unchanged48pair confirmation, no repeated audit. No new experiment launched; Docker engine unavailable/no liveE2E/six-model4GiB proof.

Follow-up 2026-10-19 — **MIXED REPLAY TRAIN/EVAL DONE; SUMMARY GUARD PASS / NOT DEPLOYED**. Same confirmed956/64 and48pair hashes; seed1337, microbatch4clean+4noisy/effective64,300updates/eval60. Private ai-core-minigpt-replay-v1 version1 COMPLETE;4remote sanity+62local Python tests+Go/CMS/Client PASS. Output/rawprediction means/IDs/checkpoint/config/guard/hashes verified. Only mixed300 eligible: clean ROUGE-L0.292511→0.475816, synthetic-ASR0.172177→0.186158, ASR repetition0.174653→0.162928, cap/EOS equal init. Higher-mean240 rejected for ASR repetition. Auxiliary titleRL0.356232→0.343602 regresses, outside summary guard. T4 runtime446.03s, peak allocated1.056/reserved1.805GiB≤8; not inference4GiB proof. Candidate70ec4790... retained separately, activecf9cfa... unchanged; fullT1.6 human gate unmet/shared1.6/5 unchanged. Report @docs/T1.6_mixed_replay.md, metrics/curves/manifest updated. Next: isolated real-ASR paired evaluation then fresh human ratings before promotion; no frozen-test tuning/repeated48pair audit. Docker engine off/no liveHTTP/E2E; no new real-video generation this task.

Follow-up 2026-10-19 — **MIXED CANDIDATE REAL-VIDEO PILOT DONE / ERRORS OBSERVED / NOT DEPLOYED**. User authorized continuation after training. Mixed300 SHA70ec4790... vs activecf9cfa...,3previously inspected clips×3exact inputs (confirmed draft/activeASR/candidateASR)×2models =18fresh nonempty summaries via production helper, CPUFP32/temp0/max96/18.734s. Active cache parity9/9, prior source/service/weights/frozen media/refs/ratings hashes unchanged; no newASR/train/tuning/human score. Still off-topic/repetitive on actualASR; confirmed Newton draft also fails. Summary proxy guard PASS does not establish real-video quality; do not promote, fullT1.6 human gate/shared1.6/5 unchanged. Reviewpacket onD:/data_training_ai/minigpt_news/mixed_replay_video_pilot_3_v1, escaping test+Playwright desktop/mobile3video playback/9pairs/no overflow+visualQC+Go/CMS/Client PASS. @docs/T1.6_mixed_video_pilot.md; @data/manifests/minigpt_mixed_video_pilot.json. Next: separate real-domain human-authored train/validation on new videos outside frozen30/3diagnostics; keep current48News confirmation, no pseudo-labeling of test clips or relaxed guard.

Follow-up 2026-10-19 — **REAL-DOMAIN DATA PREPARATION DONE / HUMAN LABELS0/40 / TRAIN GATE CLOSED**. User requested proposed new data. Downloaded20newCC videos/4new channels outside all10frozen source videos/6test channels, originals499544485bytes retained onD:/data_training_ai/minigpt_domain_v1_20261019. SeededID/channel grouping:15train videos/3channels→30clips;5val videos/1channel→10clips;40×30s=20min.40WAV/MP4 +80own-ASR inputs(active/candidate),0empty/0overbudget/max229prompt tokens, no human/generated-summary targets. Blank authoring page at localhost8890 withJSONexport/autosave, strictID/mediaSHA/attestation/complete-label/budget/disjoint gate; actualblank import rejected/noacceptedexport.20unit tests+Playwright desktop/mobile40cards/4representative playback/UTF8export/autosave/nooverflow+visualQC+Go/CMS/Client PASS. Frozen source/ref/ratings/production weight hashes unchanged; no train/deploy/externalmodel/Kaggleupload; prior48News confirmation retained. Next: humans write these new transcript-summary labels, import/review before bounded training; source-channel split is not verified speaker identity, smallmostly-news domain/near-dups not certified. @docs/T1.6_real_domain_preparation.md; @data/manifests/minigpt_real_domain.json. FullT1.6 human gate/shared1.6/5 unchanged.


- [x] Follow-up 2026-10-19 — **WHISPERWEB CONVERSION DONE, 40/40 DRAFTS; TRAINING NOT STARTED**. User replaced Clideo with WhisperWeb. Public free local browser workflow, whisper-base multilingual/Vietnamese, fixed configuration: 120 TXT/JSON/SRT exports for 40 new 30s clips (30train/10val), kept separately onD:/data_training_ai/minigpt_domain_v1_20261019/whisperweb_drafts_v1. All IDs/output hashes/TXT-JSON agreement,80clip hashes,7prep packet hashes and8frozen/active-weight hashes PASS; collector self-check +Go/CMS/Client checks PASS. 22clips have mechanical review flags (6unknown end,5repeated8word,14outside clip; overlap). External automatic drafts remain unverified, not human labels or summary targets; no gate bypass, train, deploy or weight/test changes. FullT1.6 quality gate/shared1.6/5 unchanged. Next: listen/correct with machine-assisted provenance and author summaries before separate label intake. Report @docs/T1.6_whisperweb_drafts.md; manifests @data/manifests/minigpt_whisperweb_drafts.json and minigpt_whisperweb_verification.json.

- [x] Follow-up 2026-10-20 — WHISPER REVIEW PREPROCESSING DONE. Prepared40editable Whisper transcripts/40blank summaries,22flagged-first, separate browser drafts and assisted-origin export at localhost8890/whisper_review_v1/index.html.21timing proposals across20clips/40derived SRTs; text/raw120exports/original packet/frozen data/weights unchanged.27unit tests, desktop/mobile browser and Go/CMS/Client builds PASS. No API change. Report @docs/T1.6_whisper_review.md; manifest @data/manifests/minigpt_whisper_review.json.
- [ ] Actual listening/corrections and human summaries remain pending: no direct audio-listening tool in this agent session, no invented semantic verification. Await reviewed_whisper_domain_v1.json, then separate intake preserving external-ASR provenance. No training/deploy or T1.6 quality-gate change.


- [x] Follow-up 2026-10-20 — REVIEW JSON RECEIVED AND ERROR AUDIT DONE. Exact73967-byte export SHA860f8068d0bd... saved in whisper_review_v1/received_860f8068d0bd;40IDs/source/media/copy/protected hashes PASS.40transcripts/39edits/37summaries/33feedback/0exported confirmations;31summary copies/25over95BPE/3blank. User error-review pass is received; no invented approval or WER/CER. Separate vocabulary audit: active93 lacksF/J/W/Z,9digits and punctuation; CharVocab silently drops unknown symbols. Candidate133 covers example identifiers but is not promoted. Reviewed page is Whisper-base Transcribe, not a paired project-ASR score or translation test. No code/API/weights/test/train change. Report @docs/T1.6_whisper_review_intake.md; manifest @data/manifests/minigpt_whisper_review_intake.json.
- [ ] Next: fix ASR label unknown-character handling and define English/number/identifier conventions before targeted supervised data and paired ASR evaluation; concise approved summaries are still required for MiniGPT domain training.


- [x] Follow-up 2026-10-20 — T1.4 STRICT LABEL ENCODING/PREFLIGHT DONE. SharedCharVocab rejects unsupported symbols instead of deleting them; alltrain labels validated before audio/model training. SharedReferenceASRDataset/raw-text metrics cover general/robust evaluation without dropping held-out symbols or growing vocabulary. Actual133symbol train13561/13561roundtrip;13557CTCfeasible/4existing exclusions retained;10567legacyVIVOS labels valid.3val/7testOOVlabels preserved; active93mixed training rejected before audio.80Python tests+Go/CMS/Client builds PASS; checkpoints/IDs/head/datasets/frozen tests/review hashes unchanged. Lossless label convention documented in dataset_spec3.3 and @docs/T1.4_asr_label_contract.md; proof @data/manifests/asr_label_preflight.json. No training, promotion, API change or acoustic quality claim.
- [ ] Next safe task: audio-backed supervised domain examples for English/code switching, numeric/legal identifiers, proper names and compounds; approved references and coverage/head checks before a new bounded ASR experiment. Previous40Whisper reviews remain diagnostic/unapproved, not autoaccepted targets.

# kernel-model-worker — worker GPU "khi cần" (AI-14, D24)

Chạy `inference-service/app/worker_app.py` (6 checkpoint active, SHA = contract §1) trên GPU Kaggle, mở cloudflared quick tunnel,
in `MODEL_WORKER_URL` + `MODEL_WORKER_KEY`. Facade (inference-service :8001, vẫn giữ MinIO/Milvus) đặt 2 biến đó rồi khởi động lại.
Dataset chỉ có checkpoint + code; **không có dữ liệu người dùng**. Worker không lưu request.

## Dựng / cập nhật (tài khoản `traininghighlight`, private)

```bash
# từ repo root; output ngoài repo
.venv/Scripts/python dist/kaggle/kernel-model-worker/build_dataset.py D:/tmp/ai14_20261029/ds
cd D:/tmp/ai14_20261029/ds && kaggle datasets create -p .        # lần sau: kaggle datasets version -p . -m "..."
cd E:/traning_ai/dist/kaggle/kernel-model-worker && kaggle kernels push -p .   # push = bắt đầu 1 phiên GPU
```
Chạy thử local (CPU, không tunnel): xem docstring `run_model_worker.py`.

## Dùng

1. Mở kernel trên Kaggle: Settings → Accelerator → **GPU T4**, Internet **On** (quên bật GPU → script dừng ngay với hướng dẫn, không chạy CPU âm thầm). Tùy chọn: Add-ons → Secrets → `MODEL_WORKER_KEY` (≥24 ký tự) để key không in ra log;
   không có secret → kernel sinh key ngẫu nhiên và in **một lần** trong log riêng tư.
2. Log đầu phiên in GPU (`nvidia-smi`: tên, VRAM, % dùng) + phiên bản torch/CUDA; trong phiên cứ 10 phút in lại GPU + VRAM torch đang giữ.
   Đọc log: `MODEL_WORKER_URL=https://<random>.trycloudflare.com`, `MODEL_WORKER_KEY=...`.
3. Facade: đặt `MODEL_WORKER_URL`, `MODEL_WORKER_KEY` (env tiến trình, **không** ghi vào file commit), khởi động lại :8001;
   `/health` phải có `dependencies.model_worker = "ok"`, `device = "cuda"`.
4. Xong việc: dừng phiên trên Kaggle (tiết kiệm quota), xóa 2 biến ở facade → quay về worker cùng tiến trình.

## Giới hạn

- Phiên Kaggle ≤12 h (script tự dừng sau 11.5 h); quota GPU theo tuần; mỗi phiên URL tunnel **khác** → cập nhật facade mỗi lần.
- Quick tunnel không có SLA, chỉ dùng thử/demo; mất tunnel → facade trả 503 `AI_UNAVAILABLE`, `/health.dependencies.model_worker = "unavailable"`.
- **User tự kiểm điều khoản sử dụng Kaggle** (dùng notebook làm server/tunnel ra ngoài) trước khi dùng thật.
- Output phiên (`session.json` không chứa key, `worker.log`) chỉ giữ ở version mới nhất → tải về D: (`kaggle kernels output ... -p D:/tmp/...`)
  trước khi push version kế.

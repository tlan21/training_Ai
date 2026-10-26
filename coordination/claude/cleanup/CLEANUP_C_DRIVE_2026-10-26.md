# Dọn ổ C: — 2026-10-26 (user yêu cầu trực tiếp: "dọn data gây tràn không dùng đến / bộ nhớ tạm; data quan trọng tuyệt đối không xóa")

Trước: C: **0 MB** trống (git/tool không ghi được output). Sau: C: **2.94 GB** trống.

Nguyên nhân (đo chỉ đọc, `D:/tmp/cdrive_cleanup_20261026/scan*.txt`): `C:/pagefile.sys` 20.3 GB nở do RAM trống ~0.9/15.6 GB;
Docker `docker_data.vhdx` 37.9 GB; ứng dụng/IDE/extension. Không do file dự án (test/log/tạm làn Claude đều trên D:).

Đã xóa — chỉ cache tái tạo được, manifest từng file trước khi xóa (`D:/tmp/cdrive_cleanup_20261026/manifest.tsv`, 6 904 file, 2.93 GB, 0 file bị khóa):

| Mục | Lý do an toàn |
|---|---|
| `AppData/Roaming/Code/CachedExtensionVSIXs/*` (1.7 GB) | gói VSIX VS Code đã tải; extension đã cài nằm ở `~/.vscode/extensions` (không đụng) |
| `AppData/Local/@zcodedesktop-updater/*`, `aionui-updater/*` | bộ cài cập nhật tải sẵn; app không chạy; tải lại khi cập nhật |
| `AppData/Local/go-build/*` | Go build cache (= `go clean -cache`) |
| `AppData/Local/pip/cache/*` | pip cache |
| `AppData/Local/Temp` file >2 ngày, trừ thư mục `claude/` | file tạm |

KHÔNG xóa (quan trọng / đang dùng): Docker vhdx (dữ liệu stack Codex), `pagefile.sys`, `AppData/Roaming/Claude/vm_bundles` (8.3 GB, dữ liệu app),
`~/.cache/codex-runtimes`, `antigravity-updater` (Antigravity IDE đang chạy), extension/IDE/plugin, `ms-playwright`, Desktop, mọi dữ liệu dự án,
checkpoint, venv/python uv, `.claude`, `.codex`.

Sau dọn: :8001 `/health` 200 (6 model, degraded []); git bình thường; các port stack 19530/9000/5432/27017/6379/9092/8000/5173/3000/18001 mở.
`docker ps` không phản hồi trong 40 s (Docker Desktop backend có thể kẹt sau sự cố đầy đĩa) — thuộc stack Codex, không restart.

#!/usr/bin/env bash
# Đẩy ai-core (dataset) + notebook (kernel) lên Kaggle qua API. Không cần browser.
#
# CHUẨN BỊ 1 LẦN:
#   1. kaggle.com → avatar → Settings → API → "Create New Token" → tải kaggle.json
#   2. đặt vào ~/.kaggle/kaggle.json  (Windows: %USERPROFILE%\.kaggle\kaggle.json)
#   3. export KAGGLE_USERNAME=<username của bạn>   (đúng slug tài khoản)
#
# CHẠY:  bash dist/kaggle/push_kaggle.sh <KAGGLE_USERNAME>
set -euo pipefail

USER="${1:-${KAGGLE_USERNAME:-}}"
[ -z "$USER" ] && { echo "Thiếu username. Dùng: bash push_kaggle.sh <KAGGLE_USERNAME>"; exit 1; }

# `pwd -W` (Git Bash) để ra đường dẫn Windows E:/... — cả kaggle CLI lẫn python ở đây đều là bản
# Windows, không hiểu dạng POSIX /e/traning_ai mà `pwd` trả về, và lỗi hiện ra tận trong zipfile:
# "FileNotFoundError: '/e/traning_ai/dist/kaggle/ai-core-ds/ai_core.zip'". Fallback `pwd` cho shell
# không có -W (Linux/macOS), ở đó dạng POSIX vốn đã đúng.
ROOT="$(cd "$(dirname "$0")/../.." && { pwd -W 2>/dev/null || pwd; })"
PY="$ROOT/.venv/Scripts/python.exe"
DS="$ROOT/dist/kaggle/ai-core-ds"
# KDIR phải khai ở ĐÂY, không phải ở bước 2: bước 1b (chờ dataset) đọc kernel-metadata.json để biết
# cần chờ dataset nào. Khai muộn thì `set -u` báo "KDIR: unbound variable" BÊN TRONG $(...) nên
# script không dừng — vòng chờ bị bỏ qua im lặng và race quay lại đúng như cũ.
KDIR="$ROOT/dist/kaggle/kernel"

echo "== cài kaggle CLI (nếu chưa) =="
"$PY" -m pip install -q kaggle

# Ghi THẲNG field id thay vì `sed s#KAGGLE_USERNAME#...#`: sed chỉ đúng LẦN ĐẦU, sau đó placeholder
# đã bị thay bằng username cụ thể nên truyền username khác vào là no-op im lặng — script báo thành
# công mà vẫn đẩy vào tài khoản cũ. Bản này idempotent, đổi tài khoản lúc nào cũng đúng.
"$PY" -c "
import json
p = r'$DS/dataset-metadata.json'
d = json.load(open(p))
d['id'] = '$USER/' + d['id'].split('/')[-1]
json.dump(d, open(p, 'w'), ensure_ascii=False)
print('dataset id ->', d['id'])
"

echo "== 0) rebuild ai_core.zip — dataset phải chứa code MỚI NHẤT, không phải bản lần trước =="
rm -f "$DS/ai_core.zip"
(cd "$ROOT/ai-core" && "$PY" -c "
import pathlib, zipfile
# Bỏ __pycache__: .pyc cũ đi kèm dễ che mất .py mới, và zip phình 4x.
with zipfile.ZipFile(r'$DS/ai_core.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for p in pathlib.Path('ai_core').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            z.write(p, p.as_posix())
")
ls -l "$DS/ai_core.zip"

echo "== 1) tạo/ cập nhật dataset ai-core =="
# `cd` vào thư mục rồi `-p .` — KHÔNG truyền đường dẫn tuyệt đối Windows. Kaggle CLI dựng tên file
# cache upload từ chính đường dẫn đó, đổi ':' thành '_' rồi không tạo thư mục trung gian:
#   [Errno 2] ... '.kaggle/uploads\E_/traning_ai/dist/kaggle/ai-core-ds_ai_core.zip.json'
# Lỗi này KHÔNG chặn upload (file vẫn lên) nên rất dễ tưởng đã xong, nhưng `set -e` kết thúc script
# trước bước push kernel — dataset mới mà notebook vẫn bản cũ.
( cd "$DS"
  if "$PY" -m kaggle datasets status "$USER/ai-core" >/dev/null 2>&1; then
    "$PY" -m kaggle datasets version -p . -m "update ai_core" --dir-mode zip
  else
    "$PY" -m kaggle datasets create -p . --dir-mode zip
  fi )

# Tạo/cập nhật dataset là BẤT ĐỒNG BỘ. Push kernel ngay sau đó thì Kaggle chưa thấy dataset và im
# lặng bỏ nó khỏi kernel: "The following are not valid dataset sources ... ['<user>/ai-core']" —
# kernel vẫn push OK rồi chết ở cell 0 vì không có ai_core. Phải chờ mọi dataset attach thành ready.
echo "== 1b) chờ dataset xử lý xong (tạo dataset là bất đồng bộ) =="
for ds in $("$PY" -c "
import json
print(' '.join(json.load(open(r'$KDIR/kernel-metadata.json'))['dataset_sources']))
" 2>/dev/null); do
  for i in $(seq 1 60); do
    st="$("$PY" -m kaggle datasets status "$ds" 2>&1 | tail -1)"
    [ "$st" = "ready" ] && { echo "   $ds : ready"; break; }
    [ "$i" = 60 ] && { echo "   $ds : QUÁ 10 PHÚT vẫn '$st' — dừng, đừng push kernel thiếu dataset"; exit 1; }
    sleep 10
  done
done

echo "== 2) đẩy notebook (kernel) train, attach dataset ai-core =="
# Notebook nguồn duy nhất = dist/kaggle/kernel/kaggle_train.ipynb. KHÔNG copy từ scripts/ vào đây:
# bản scripts/ từng đứng sau và copy lên là ghi đè mất bản đã sửa (đã suýt regress bug eval T1.7).
[ -f "$KDIR/kaggle_train.ipynb" ] || { echo "Thiếu $KDIR/kaggle_train.ipynb"; exit 1; }
# CHỈ sinh metadata khi CHƯA có. Bản trước sinh vô điều kiện với dataset_sources = chỉ ai-core, nên
# mỗi lần push lại là xoá sạch các dataset đã attach tay (soccernet-highlight-features, vivos-asr...).
# Hậu quả không lộ ra lúc push: kernel vẫn nhận, xếp hàng chờ GPU rồi mới chết ở
# `raise SystemExit('Thieu highlight_features.pt ...')`. Muốn thêm dataset thì sửa thẳng file này,
# hoặc xoá nó để sinh lại bản tối thiểu.
if [ -f "$KDIR/kernel-metadata.json" ]; then
  # Viết lại TIỀN TỐ CHỦ SỞ HỮU của id + dataset_sources theo $USER, giữ nguyên tên dataset. Đổi tài
  # khoản mà không làm bước này thì kernel đẩy sang tài khoản cũ (hoặc lỗi 403), và dataset_sources
  # trỏ vào dataset của tài khoản cũ mà tài khoản mới không thấy → kernel chạy rồi chết vì thiếu file.
  "$PY" -c "
import json
p = r'$KDIR/kernel-metadata.json'
d = json.load(open(p))
own = lambda s: '$USER/' + s.split('/')[-1]
d['id'] = own(d['id'])
d['dataset_sources'] = [own(s) for s in d['dataset_sources']]
json.dump(d, open(p, 'w'), ensure_ascii=False, indent=2)
print('-- kernel id :', d['id'])
print('-- dataset attach:')
[print('   ' + s) for s in d['dataset_sources']]
"
else
cat > "$KDIR/kernel-metadata.json" <<EOF
{
  "id": "$USER/ai-core-train",
  "title": "ai-core-train",
  "code_file": "kaggle_train.ipynb",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": true,
  "dataset_sources": ["$USER/ai-core"],
  "competition_sources": [],
  "kernel_sources": []
}
EOF
fi
# --accelerator là FLAG CLI, không phải field trong kernel-metadata.json: đặt "accelerator" trong
# metadata bị Kaggle bỏ qua im lặng và kernel vẫn nhận P100 (sm_60) → torch báo
# 'no kernel image', guard cell 0 rơi về CPU. Chỉ flag này mới thực sự chọn được T4.
# `kaggle kernels push` TRẢ EXIT CODE 0 KỂ CẢ KHI THẤT BẠI — đã đo: hết quota GPU tuần thì nó in
# "Kernel push error: Maximum weekly GPU quota of 30.00 hours reached." rồi exit 0, nên `set -e`
# không bắt được và script vẫn in "== XONG ==" như thường. Phải soi output.
PUSH_OUT="$( cd "$KDIR" && "$PY" -m kaggle kernels push -p . --accelerator NvidiaTeslaT4 2>&1 )"
echo "$PUSH_OUT"
# "not valid dataset sources" cũng phải chặn: kernel VẪN push thành công nhưng KHÔNG có dataset, nên
# nó chạy rồi chết ở cell 0 (`KHÔNG thấy ai_core trong /kaggle/input`) sau khi đã xếp hàng chờ GPU.
if grep -qiE "error|quota|fail|not valid|could not be added" <<<"$PUSH_OUT"; then
  echo ">> PUSH CÓ VẤN ĐỀ — kiểm dòng trên. Kernel có thể đã lên mà THIẾU dataset."
  exit 1
fi

echo "== XONG =="
echo "Dataset : https://www.kaggle.com/datasets/$USER/ai-core"
echo "Notebook: https://www.kaggle.com/code/$USER/ai-core-train  (mở → Run All, GPU+Internet đã bật)"

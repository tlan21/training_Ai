#!/usr/bin/env bash
# Đóng gói bản deploy: code (ai_core + inference-service) + trọng số (checkpoints) + sidecar.
# LOẠI dataset thô, venv, log train, test. Sinh checksum + manifest.
#
# Dùng:  bash scripts/package_deploy.sh [OUT_DIR]
#   OUT_DIR mặc định: dist/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/dist}"
STAMP="$(date +%Y%m%d_%H%M%S 2>/dev/null || echo manual)"
STAGE="$OUT/deploy_$STAMP"
CKPT="$ROOT/ai-core/checkpoints"

echo "== Đóng gói deploy → $STAGE =="

# 1. Cảnh báo nếu chưa train (không có checkpoint) — vẫn đóng gói code (chạy stub được)
if [ ! -d "$CKPT" ] || [ -z "$(find "$CKPT" -name '*.pt' 2>/dev/null)" ]; then
  echo "[!] CẢNH BÁO: chưa có checkpoint (*.pt) trong ai-core/checkpoints/."
  echo "    Bản đóng gói chỉ chạy được ở chế độ STUB (FORCE_STUB=1)."
fi

mkdir -p "$STAGE"

# 2. Copy code (loại cache/test)
echo "-- copy ai_core (package)"
mkdir -p "$STAGE/ai-core"
cp -r "$ROOT/ai-core/ai_core" "$STAGE/ai-core/ai_core"
cp "$ROOT/ai-core/pyproject.toml" "$STAGE/ai-core/" 2>/dev/null || true
find "$STAGE/ai-core" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find "$STAGE/ai-core" -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true

echo "-- copy inference-service"
mkdir -p "$STAGE/inference-service"
cp -r "$ROOT/inference-service/app" "$STAGE/inference-service/app"
cp "$ROOT/inference-service/requirements.txt" "$STAGE/inference-service/" 2>/dev/null || true
cp "$ROOT/inference-service/Dockerfile" "$STAGE/inference-service/" 2>/dev/null || true
cp "$ROOT/inference-service/.env.example" "$STAGE/inference-service/" 2>/dev/null || true
find "$STAGE/inference-service" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

# 3. Copy trọng số (best.pt + sidecar), KHÔNG copy last.pt cho gọn
echo "-- copy checkpoints (best.pt + sidecar)"
if [ -d "$CKPT" ]; then
  mkdir -p "$STAGE/ai-core/checkpoints"
  ( cd "$CKPT" && find . \( -name 'best.pt' -o -name 'vocab.json' -o -name 'classes.json' \) -print0 \
    | while IFS= read -r -d '' f; do
        mkdir -p "$STAGE/ai-core/checkpoints/$(dirname "$f")"
        cp "$f" "$STAGE/ai-core/checkpoints/$f"
      done )
fi

# 4. Checksum toàn bộ trọng số
echo "-- sinh CHECKSUMS.txt"
( cd "$STAGE" && find ai-core/checkpoints -name '*.pt' -print0 2>/dev/null \
  | xargs -0 sha256sum 2>/dev/null > CHECKSUMS.txt || true )

# 5. Manifest ngắn
{
  echo "package: deploy_$STAMP"
  echo "root: $ROOT"
  echo "checkpoints:"
  find "$STAGE/ai-core/checkpoints" -name '*.pt' 2>/dev/null | sed "s|$STAGE/||;s|^|  - |" || echo "  (none — STUB only)"
} > "$STAGE/MANIFEST.txt"
cat "$STAGE/MANIFEST.txt"

# 6. Nén
TAR="$OUT/deploy_$STAMP.tgz"
echo "-- nén → $TAR"
( cd "$STAGE" && tar czf "$TAR" . )
echo "== XONG: $TAR"
echo "   Giải nén trên máy đích, cài torch+deps, đặt .env, chạy uvicorn (xem verify_checkpoints.sh)."

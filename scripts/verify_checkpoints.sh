#!/usr/bin/env bash
# Kiểm tra bản deploy: checksum trọng số + liệt kê best.pt/sidecar + (tùy chọn) gọi /health.
#
# Dùng:
#   bash scripts/verify_checkpoints.sh [CKPT_DIR] [HEALTH_URL]
#   CKPT_DIR   mặc định: ai-core/checkpoints
#   HEALTH_URL nếu truyền → curl kiểm models_loaded/stub_mode (vd http://127.0.0.1:8001/health)
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CKPT="${1:-$ROOT/ai-core/checkpoints}"
HEALTH="${2:-}"
MODELS="vit siamese asr_ctc highlight_fusion minigpt two_tower"
fail=0

echo "== Verify checkpoints: $CKPT =="

# 1. Có đủ 6 best.pt không
for m in $MODELS; do
  if [ -f "$CKPT/$m/best.pt" ]; then
    sz=$(du -h "$CKPT/$m/best.pt" 2>/dev/null | cut -f1)
    echo "  [ok]   $m/best.pt ($sz)"
  else
    echo "  [MISS] $m/best.pt — endpoint '$m' sẽ chạy STUB"
    fail=1
  fi
done

# 2. Sidecar bắt buộc cho real path
[ -f "$CKPT/asr_ctc/vocab.json" ]  && echo "  [ok]   asr_ctc/vocab.json"  || { echo "  [MISS] asr_ctc/vocab.json — ASR real path sẽ stub"; fail=1; }
[ -f "$CKPT/vit/classes.json" ]    && echo "  [ok]   vit/classes.json"    || echo "  [warn] vit/classes.json thiếu — category trả 'class_<idx>'"

# 3. Checksum (nếu có CHECKSUMS.txt cạnh checkpoint hoặc ở gốc gói)
CS=""
[ -f "$CKPT/../CHECKSUMS.txt" ] && CS="$CKPT/../CHECKSUMS.txt"
[ -f "$CKPT/CHECKSUMS.txt" ] && CS="$CKPT/CHECKSUMS.txt"
if [ -n "$CS" ]; then
  echo "-- đối chiếu checksum ($CS)"
  ( cd "$(dirname "$CS")" && sha256sum -c "$(basename "$CS")" ) || fail=1
else
  echo "  [warn] không thấy CHECKSUMS.txt — bỏ qua đối chiếu"
fi

# 4. /health (tùy chọn)
if [ -n "$HEALTH" ]; then
  echo "-- GET $HEALTH"
  body="$(curl -s "$HEALTH" || true)"
  echo "  $body"
  echo "$body" | grep -q '"stub_mode":false' && echo "  [ok]   stub_mode=false" || { echo "  [warn] stub_mode != false (đang chạy stub?)"; fail=1; }
  echo "$body" | grep -q '"degraded":\[\]' && echo "  [ok]   degraded rỗng" || echo "  [warn] có model degraded — xem log service"
fi

echo "== $( [ $fail -eq 0 ] && echo 'PASS' || echo 'CÓ VẤN ĐỀ (xem [MISS]/[warn] trên)') =="
exit $fail

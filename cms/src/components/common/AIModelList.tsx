import type { components } from "../../api-types";

// API 0.12.0: checkpoint each AI model is actually running (short SHA; full SHA256 in the tooltip, matches AI_API_CONTRACT §1).
const LABELS: Record<string, string> = {
  vit: "Phân loại hình ảnh (ViT)",
  siamese: "Tìm kiếm hình ảnh (Siamese)",
  asr_ctc: "Nhận dạng giọng nói (ASR)",
  highlight_fusion: "Chấm điểm highlight (Fusion)",
  minigpt: "Tóm tắt nội dung (MiniGPT)",
  two_tower: "Gợi ý video (Two-Tower)",
};

export function AIModelList({ models }: { models?: components["schemas"]["AIModelCheckpoint"][] }) {
  if (!models?.length) return null;
  return <ul className="ai-model-list" aria-label="Phiên bản model AI">{models.map((model) => <li key={model.name}><span>{LABELS[model.name] ?? model.name}</span><code className="mono" title={`${model.file} · SHA256 ${model.sha256}`}>{model.sha256.slice(0, 8)}</code></li>)}</ul>;
}

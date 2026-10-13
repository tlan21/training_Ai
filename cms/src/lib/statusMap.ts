// Single source badge map — 00_master_plan §2.6 + 03_cms §1.3
export const statusMap: Record<string, { color: string; label: string }> = {
  uploaded: { color: "var(--info)", label: "Đã tải lên" },
  processing: { color: "var(--warning)", label: "Đang xử lý" },
  processed: { color: "var(--success)", label: "Đã xử lý" },
  failed: { color: "var(--danger)", label: "Thất bại" },
  deleted: { color: "var(--text-muted)", label: "Đã xóa" },
  draft: { color: "var(--warning)", label: "Nháp" },
  published: { color: "var(--success)", label: "Đã xuất bản" },
  rejected: { color: "var(--danger)", label: "Từ chối" },
  pending: { color: "var(--text-muted)", label: "Chờ" },
  running: { color: "var(--warning)", label: "Đang chạy" },
  completed: { color: "var(--success)", label: "Hoàn tất" },
};
export const stageLabel: Record<string, string> = {
  splitting_frames: "Băm khung hình",
  asr_extracting: "Trích giọng nói",
  highlight_scoring: "Chấm điểm highlight",
  embedding: "Sinh vector",
  summarizing: "Tóm tắt",
  completed: "Hoàn tất",
};

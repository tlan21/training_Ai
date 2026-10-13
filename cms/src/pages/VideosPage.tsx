import { useState } from "react";
import { useCmsVideos, useCmsVideo, useCmsAnalysis, useCategories } from "../hooks/useCms";
import { apiClient } from "../lib/apiClient";
import { useQueryClient } from "@tanstack/react-query";
import { StatusBadge } from "../components/common/StatusBadge";

export default function VideosPage() {
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const list = useCmsVideos({ status: status || undefined, page });
  const cats = useCategories();
  const qc = useQueryClient();
  const items: any[] = list.data?.items ?? [];
  return (
    <div>
      <h2>Danh sách Video</h2>
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <select className="input" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
          <option value="">Tất cả</option>
          {["uploaded", "processing", "processed", "failed", "deleted"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div className="card" style={{ marginTop: 16, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead><tr style={{ background: "var(--bg-surface-2)", textAlign: "left" }}><th style={{ padding: 8 }}>Tên</th><th>Trạng thái</th><th>Category</th><th>Thời lượng</th><th>Ngày</th><th></th></tr></thead>
          <tbody>
            {items.map((v: any) => (
              <tr key={v.id} style={{ borderTop: "1px solid var(--border)" }}>
                <td style={{ padding: 8 }}>{v.title}</td>
                <td><StatusBadge status={v.status} /></td>
                <td><CategoryCell video={v} cats={cats.data} qc={qc} /></td>
                <td>{v.duration_seconds}s</td>
                <td style={{ fontFamily: "JetBrains Mono", fontSize: 11 }}>{v.created_at?.slice(0, 10)}</td>
                <td><button onClick={async () => { if (confirm("Xóa video?")) { await apiClient.delete(`/api/cms/videos/${v.id}`); qc.invalidateQueries({ queryKey: ["videos"] }); } }} style={{ color: "var(--danger)" }}>Xóa</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && <div style={{ padding: 16, color: "var(--text-muted)" }}>{list.isLoading ? "Đang tải…" : "Không có video khớp"}</div>}
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>◄</button>
        <span>Trang {page} / {Math.ceil((list.data?.total ?? items.length) / 20) || 1}</span>
        <button onClick={() => setPage((p) => p + 1)}>►</button>
      </div>
    </div>
  );
}
function CategoryCell({ video, cats, qc }: any) {
  const analysis = useCmsAnalysis(video.id);
  const suggestion: string | null = analysis.data?.category_suggestion ?? null;
  const [sel, setSel] = useState(video.category?.id ?? "");
  const catList: any[] = cats ?? [];
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
      {suggestion && !video.category && <span className="badge" style={{ background: "var(--info)22" }}>AI gợi ý: {suggestion}</span>}
      <select className="input" value={sel} onChange={(e) => setSel(e.target.value)} style={{ padding: "4px 8px" }}>
        <option value="">—</option>
        {catList.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
      <button onClick={async () => { if (!sel) return; await apiClient.put(`/api/cms/videos/${video.id}/category`, { category_id: sel }); qc.invalidateQueries({ queryKey: ["videos"] }); }} style={{ fontSize: 12, color: "var(--primary)" }}>Xác nhận</button>
    </div>
  );
}

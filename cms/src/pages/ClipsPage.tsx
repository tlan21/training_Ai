import { useState } from "react";
import { useClips, usePublishClip, useDeleteClip } from "../hooks/useCms";
import { apiClient } from "../lib/apiClient";
import { StatusBadge } from "../components/common/StatusBadge";

export default function ClipsPage() {
  const [vid, setVid] = useState("");
  const [status, setStatus] = useState("");
  const list = useClips({ video_id: vid || undefined, status: status || undefined });
  const pub = usePublishClip();
  const del = useDeleteClip();
  const [edit, setEdit] = useState<any | null>(null);
  const items: any[] = list.data ?? [];
  return (
    <div>
      <h2>Nội dung đã xuất bản — Clips</h2>
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <input className="input" placeholder="video_id" value={vid} onChange={(e) => setVid(e.target.value)} style={{ width: 220 }} />
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Tất cả</option>
          {["draft", "processing", "published", "rejected"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div className="card" style={{ marginTop: 16, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead><tr style={{ background: "var(--bg-surface-2)", textAlign: "left" }}><th style={{ padding: 8 }}>Tiêu đề</th><th>Video</th><th>Khoảng</th><th>Điểm</th><th>Trạng thái</th><th>Hành động</th></tr></thead>
          <tbody>
            {items.map((c: any) => (
              <tr key={c.id} style={{ borderTop: "1px solid var(--border)" }}>
                <td style={{ padding: 8 }}>{c.title}</td>
                <td style={{ fontFamily: "JetBrains Mono", fontSize: 11 }}>{c.video_id?.slice(0, 10)}</td>
                <td>{c.start_time?.toFixed(1)}–{c.end_time?.toFixed(1)}</td>
                <td>{c.average_score}</td>
                <td><StatusBadge status={c.status} /></td>
                <td style={{ display: "flex", gap: 6 }}>
                  <button onClick={() => setEdit(c)} style={{ color: "var(--primary)" }}>Sửa</button>
                  <button disabled={c.status === "processing"} onClick={() => pub.mutate(c.id)} style={{ color: c.status === "processing" ? "var(--text-muted)" : "var(--success)" }}>Publish</button>
                  <button onClick={() => { if (confirm("Reject?")) del.mutate(c.id); }} style={{ color: "var(--danger)" }}>Reject</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && <div style={{ padding: 16, color: "var(--text-muted)" }}>{list.isLoading ? "Đang tải…" : "Không có clip"}</div>}
      </div>
      {edit && <EditModal clip={edit} onClose={() => setEdit(null)} />}
    </div>
  );
}
function EditModal({ clip, onClose }: any) {
  const [title, setTitle] = useState(clip.title);
  const save = async () => { await apiClient.put(`/api/cms/clips/${clip.id}`, { title }); onClose(); location.reload(); };
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "grid", placeItems: "center" }} onClick={onClose}>
      <div className="card" style={{ padding: 16, width: 400 }} onClick={(e) => e.stopPropagation()}>
        <h3>Sửa clip</h3>
        <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} style={{ width: "100%", marginTop: 8 }} />
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button className="btn-primary" onClick={save}>Lưu</button>
          <button onClick={onClose}>Hủy</button>
        </div>
      </div>
    </div>
  );
}

import { useDropzone } from "../components/common/useDropzone";
import { useUploadVideo, useCmsJobs, useCmsJob } from "../hooks/useCms";
import { useUploadStore } from "../stores/uploadStore";
import { useState } from "react";
import { StatusBadge } from "../components/common/StatusBadge";
import { stageLabel } from "../lib/statusMap";

function ErrorLogModal({ id, onClose }: { id: string; onClose: () => void }) {
  const { data } = useCmsJob(id);
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "grid", placeItems: "center", zIndex: 50 }} onClick={onClose}>
      <div className="card" style={{ padding: 16, width: 640, maxHeight: "80vh", overflow: "auto" }} onClick={(e) => e.stopPropagation()}>
        <h3>Error log — {id}</h3>
        <pre style={{ fontFamily: "JetBrains Mono", fontSize: 12, whiteSpace: "pre-wrap", background: "var(--bg-surface-2)", padding: 12, borderRadius: 8 }}>
          {data?.error_log ?? "—"}
        </pre>
        <button className="btn-primary" onClick={onClose} style={{ marginTop: 12 }}>Đóng</button>
      </div>
    </div>
  );
}

export default function QueuePage() {
  const { getRootProps, getInputProps, isDragActive, file } = useDropzone({ accept: ".mp4,.mkv", maxSize: 2 * 1024 * 1024 * 1024 });
  const up = useUploadVideo();
  const upload = useUploadStore();
  const jobs = useCmsJobs({});
  const [errId, setErrId] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const doUpload = async () => {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("title", file.name);
    try { await up.mutateAsync(fd); upload.done(); } catch (e: any) { upload.fail(e?.apiError?.message ?? e.message); }
  };

  return (
    <div>
      <h2>Tải lên & Hàng đợi</h2>
      <div className="card" {...getRootProps()} style={{ padding: 32, border: "2px dashed var(--border)", textAlign: "center", background: isDragActive ? "var(--bg-surface-2)" : undefined, cursor: "pointer", marginTop: 16 }}>
        <input {...getInputProps()} />
        <div style={{ fontSize: 32 }}>⬆</div>
        <div>{file ? file.name : "Kéo thả video vào đây hoặc Chọn tệp (.mp4/.mkv ≤2GB)"}</div>
        {file && <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{(file.size / 1e9).toFixed(2)} GB</div>}
        {upload.status === "error" && <div style={{ color: "var(--danger)" }}>{upload.error}</div>}
      </div>
      {file && <button className="btn-primary" onClick={doUpload} disabled={up.isPending} style={{ marginTop: 12 }}>{up.isPending ? "Đang tải…" : "Tải lên"}</button>}

      <div style={{ display: "flex", gap: 8, marginTop: 24 }}>
        {(["", "pending", "running", "completed", "failed"] as const).map((s) => (
          <button key={s} onClick={() => setFilter(s)} style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border)", background: filter === s ? "var(--primary)" : "var(--bg-surface)", color: filter === s ? "white" : undefined }}>
            {s || "Tất cả"}
          </button>
        ))}
      </div>

      <div className="card" style={{ marginTop: 16, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "var(--bg-surface-2)", textAlign: "left" }}>
              <th style={{ padding: 8 }}>Video ID</th><th>Tên</th><th>Giai đoạn</th><th>Trạng thái</th><th>Tiến độ</th><th></th>
            </tr>
          </thead>
          <tbody>
            {((jobs.data as any[]) ?? []).filter((j) => !filter || j.status === filter).map((j: any) => (
              <tr key={j.id} style={{ borderTop: "1px solid var(--border)" }}>
                <td style={{ padding: 8, fontFamily: "JetBrains Mono", fontSize: 11 }}>{j.video_id?.slice(0, 12)}</td>
                <td>{j.video_id}</td>
                <td>{j.current_stage ? stageLabel[j.current_stage] ?? j.current_stage : "—"}</td>
                <td><StatusBadge status={j.status} /></td>
                <td>{j.progress ?? 0}%</td>
                <td>
                  {j.status === "failed" && <button onClick={() => setErrId(j.id)} style={{ fontSize: 12, color: "var(--danger)" }}>Xem log</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!jobs.data && <div style={{ padding: 16, color: "var(--text-muted)" }}>Đang tải…</div>}
        {(jobs.data as any[])?.length === 0 && <div style={{ padding: 16, color: "var(--text-muted)" }}>Chưa có job</div>}
      </div>
      {errId && <ErrorLogModal id={errId} onClose={() => setErrId(null)} />}
    </div>
  );
}

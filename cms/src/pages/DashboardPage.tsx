import { useSystemHealth, useJobs, useVideos } from "../hooks/useAuth";

export default function DashboardPage() {
  const health = useSystemHealth();
  const jobs = useJobs({ status: "running" });
  const videos = useVideos({});
  const failed = useJobs({ status: "failed" });
  return (
    <div>
      <h2>Tổng quan hệ thống</h2>
      <p style={{ color: "var(--text-secondary)" }}>Chào mừng quay trở lại.</p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginTop: 24 }}>
        <Stat label="Tổng Video" value={(videos.data as any)?.total ?? (videos.data as any)?.items?.length ?? "—"} />
        <Stat label="Đang xử lý" value={(jobs.data as any)?.length ?? "—"} />
        <Stat label="Jobs lỗi" value={(failed.data as any)?.length ?? "—"} />
        <Stat label="Queue depth" value={health.data?.queue_depth ?? "—"} />
      </div>
      <div className="card" style={{ padding: 16, marginTop: 16 }}>
        <h3>GPU Health (poll 5s) {health.isFetching ? "● live" : "○"}</h3>
        {health.data ? (
          <div style={{ fontFamily: "JetBrains Mono", fontSize: 13 }}>
            VRAM {health.data.gpu_vram_used} — Util {health.data.gpu_util}% — Models: {health.data.models_loaded?.join(", ") || "—"} — Queue {health.data.queue_depth}
          </div>
        ) : (
          <div style={{ color: "var(--text-muted)" }}>{health.isError ? "AI không khả dụng" : "Đang tải…"}</div>
        )}
      </div>
      <div className="card" style={{ padding: 16, marginTop: 16 }}>
        <h3>Jobs đang chạy</h3>
        {(jobs.data as any[])?.length ? (
          (jobs.data as any[]).map((j: any) => (
            <div key={j.id} style={{ display: "flex", gap: 12, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
              <span style={{ fontFamily: "JetBrains Mono", fontSize: 12 }}>{j.video_id?.slice(0, 10)}</span>
              <span>{j.current_stage ?? "—"}</span>
              <span className="badge" style={{ background: "var(--warning)22" }}>{j.status}</span>
            </div>
          ))
        ) : (
          <div style={{ color: "var(--text-muted)" }}>Không có job đang chạy</div>
        )}
      </div>
    </div>
  );
}
function Stat({ label, value }: { label: string; value: any }) {
  return (
    <div className="card" style={{ padding: 16 }}>
      <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

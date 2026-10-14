import { Link } from "react-router-dom";
import { useState } from "react";
import { useSystemHealth } from "../hooks/useAuth";
import { useCmsJobs, useCmsVideos, useClips } from "../hooks/useCms";
import { Icon } from "../components/common/Icon";
import { Thumbnail } from "../components/common/Media";
import { StatusBadge } from "../components/common/StatusBadge";
import { Skeleton, Empty, ErrorState } from "../components/common/Skeleton";
import { apiClient, errorMessage } from "../lib/apiClient";
import type { components } from "../api-types";
import { useToast } from "../components/common/Toast";
import { fmtSec } from "../lib/time";

export default function DashboardPage() {
  const health = useSystemHealth();
  const jobs = useCmsJobs();
  const videos = useCmsVideos({});
  const clips = useClips();
  const toast = useToast();
  const [previousMonth, setPreviousMonth] = useState(false);
  const download = async (id: string) => {
    try { const result = await apiClient.get<components["schemas"]["Clip"]>(`/api/clips/${id}`); if (result.data.playback_url) window.open(result.data.playback_url, "_blank", "noopener"); else toast.err("Chưa có nguồn phát clip"); } catch (error) { toast.err(errorMessage(error)); }
  };
  const failures = jobs.data?.filter((job) => job.status === "failed") ?? [];
  const now = new Date();
  const end = previousMonth ? new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 0)) : new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const days = Array.from({ length: Math.min(30, end.getUTCDate()) }, (_, index) => { const day = new Date(end); day.setUTCDate(end.getUTCDate() - Math.min(30, end.getUTCDate()) + 1 + index); return day; });
  const dayCounts = days.map((day) => (jobs.data ?? []).filter((job) => job.status === "completed" && job.updated_at?.slice(0, 10) === day.toISOString().slice(0, 10)).length);
  const maxCount = Math.max(1, ...dayCounts);
  const points = dayCounts.map((count, index) => `${index / Math.max(1, days.length - 1) * 600},${220 - count / maxCount * 180}`).join(" ");
  const report = () => {
    const blob = new Blob([JSON.stringify({ videos: videos.data, jobs: jobs.data, clips: clips.data, health: health.data }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "bao-cao-cms.json"; link.click(); URL.revokeObjectURL(url);
  };
  return <div className="dashboard-page">
    <div className="page-header"><div><h2>Tổng quan hệ thống</h2><p>Chào mừng quay trở lại, Admin. Đây là hiệu suất xử lý hôm nay.</p></div><div className="page-actions"><button className="btn-secondary" onClick={report} disabled={!videos.data || !jobs.data}>Tải báo cáo</button><Link className="btn-primary" to="/queue">Tải video mới</Link></div></div>
    <div className="stat-grid">
      <Stat label="Tổng video xử lý" icon="video_file" value={videos.data?.total ?? "—"} hint="Video trong hệ thống" />
      <Stat label="Hiệu suất Highlight AI" icon="auto_awesome" value="—" hint="Chưa có dữ liệu đánh giá" />
      <Stat label="Dung lượng lưu trữ" icon="database" value="—" hint="MinIO · Chưa có dữ liệu dung lượng" />
      <Stat label="Người dùng hoạt động" icon="person_play" value="—" hint="Chưa có dữ liệu trực tuyến" />
    </div>
    <div className="dashboard-middle">
      <section className="card panel-body"><div className="chart-heading"><h4>Xu hướng xử lý Video (30 ngày)</h4><select className="input compact-input" aria-label="Khoảng thời gian thống kê" value={previousMonth ? "previous" : "current"} onChange={(event) => setPreviousMonth(event.target.value === "previous")}><option value="current">Tháng này</option><option value="previous">Tháng trước</option></select></div>
        {jobs.isLoading ? <Skeleton h={260} /> : jobs.isError ? <ErrorState msg={errorMessage(jobs.error)} onRetry={() => jobs.refetch()} /> : <><svg className="trend-chart" viewBox="0 0 600 250" preserveAspectRatio="none" role="img" aria-label="Số video xử lý hoàn tất theo ngày"><defs><linearGradient id="chart-area" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#461599" stopOpacity=".12" /><stop offset="1" stopColor="#461599" stopOpacity="0" /></linearGradient></defs><polygon points={`0,220 ${points} 600,220`} fill="url(#chart-area)" /><polyline points={points} fill="none" stroke="#461599" strokeWidth="2.5" /><line x1="0" y1="220" x2="600" y2="220" stroke="#cbc3d5" /></svg><div className="chart-dates">{Array.from({ length: 6 }, (_, index) => <span key={index}>{days[Math.round(index * (days.length - 1) / 5)].toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", timeZone: "UTC" })}</span>)}</div><p className="micro">Thống kê theo thời gian hoàn tất của các job.</p></>}
      </section>
      <section className="card panel-body"><h4>Cảnh báo hệ thống</h4><div className="system-alerts">
        {jobs.isError && <ErrorState msg={errorMessage(jobs.error)} onRetry={() => jobs.refetch()} />}
        {failures.slice(0, 2).map((job) => <Link to="/queue?status=failed" key={job.id} className="system-alert is-error"><Icon name="warning" size={20} /><div><strong>Lỗi xử lý video</strong><p>{job.error_log ?? job.video_id}</p></div></Link>)}
        <div className="system-alert"><Icon name="info" size={20} /><div><strong>Model AI</strong>{health.isLoading ? <Skeleton /> : <p>{health.isError ? "AI không khả dụng" : health.data?.models_loaded?.join(", ") || "Chưa nạp model"}</p>}</div></div>
        <div className="system-alert neutral"><Icon name="storage" size={20} /><div><strong>Trạng thái inference</strong><p>VRAM {health.data?.gpu_vram_used ?? "—"} GB · GPU {health.data?.gpu_util ?? "—"}%</p><p>Hàng đợi: {health.data?.queue_depth ?? "—"}</p></div></div>
      </div><Link className="btn-text" to="/queue">Xem tất cả log <Icon name="arrow_forward" size={16} /></Link></section>
    </div>
    <section className="card table-card"><div className="panel-heading"><h4>Highlight AI mới nhất</h4><Link className="btn-text" to="/published">Quản lý Highlight</Link></div><div className="table-scroll"><table className="data-table"><thead><tr><th>Video</th><th>Thời lượng</th><th>Độ tin cậy AI</th><th>Trạng thái</th><th>Hành động</th></tr></thead><tbody>{clips.data?.slice(0, 5).map((clip) => <tr key={clip.id}><td><div className="media-cell"><Thumbnail src={clip.thumbnail_url} duration={(clip.end_time ?? 0) - (clip.start_time ?? 0)} /><div><strong>{clip.title}</strong><p className="micro mono">{clip.id}</p></div></div></td><td className="mono">{fmtSec((clip.end_time ?? 0) - (clip.start_time ?? 0))}</td><td><div className="score-cell">{clip.average_score?.toFixed(0) ?? "—"}%<div className="progress-track"><span style={{ width: `${clip.average_score ?? 0}%` }} /></div></div></td><td><StatusBadge status={clip.status ?? "draft"} /></td><td><div className="row-actions"><Link className="icon-button" aria-label="Biên tập highlight" to={`/highlight?video_id=${clip.video_id}`}><Icon name="edit" size={20} /></Link><button className="icon-button" aria-label={`Mở tải clip ${clip.title}`} disabled={clip.status !== "published"} onClick={() => clip.id && download(clip.id)}><Icon name="download" size={20} /></button></div></td></tr>)}</tbody></table></div>{clips.isLoading ? <div className="panel-body"><Skeleton h={48} /></div> : clips.isError ? <ErrorState msg={errorMessage(clips.error)} onRetry={() => clips.refetch()} /> : !clips.data?.length && <Empty msg="Chưa có highlight. Tải video mới để bắt đầu." />}<div className="pagination" style={{ justifyContent: "center" }}><Link className="btn-text" to="/published">Tải thêm dữ liệu <Icon name="expand_more" size={18} /></Link></div></section>
    <Link className="dashboard-fab" aria-label="Phân tích video mới" to="/queue"><Icon name="add" /></Link>
  </div>;
}
function Stat({ label, icon, value, hint }: { label: string; icon: string; value: number | string; hint: string }) {
  return <div className="card stat-card"><div className="stat-label"><span>{label}</span><Icon name={icon} /></div><div><div className="stat-value">{value}</div><p className="stat-hint">{hint}</p></div></div>;
}

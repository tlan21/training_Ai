import { Link } from "react-router-dom";
import { useState } from "react";
import { useSystemHealth } from "../hooks/useAuth";
import { useAuthStore } from "../stores/authStore";
import { useCmsJobs, useClips } from "../hooks/useCms";
import { Icon } from "../components/common/Icon";
import { Thumbnail } from "../components/common/Media";
import { StatusBadge } from "../components/common/StatusBadge";
import { Skeleton, Empty, ErrorState } from "../components/common/Skeleton";
import { apiClient, errorMessage } from "../lib/apiClient";
import type { components } from "../api-types";
import { useToast } from "../components/common/Toast";
import { fmtSec, fmtBytes, fmtISO } from "../lib/time";

export default function DashboardPage() {
const [previousMonth, setPreviousMonth] = useState(false);
 const current = new Date(); const month = new Date(Date.UTC(current.getUTCFullYear(),current.getUTCMonth()-(previousMonth?1:0),1)).toISOString().slice(0,7);
 const health = useSystemHealth({include_metrics:true,month});
 const metrics=health.data?.metrics;
  const jobs = useCmsJobs();
  const clips = useClips();
  const username = useAuthStore((state) => state.user?.username) ?? "Admin";
  const toast = useToast();
  const download = async (id: string) => {
    try { const result = await apiClient.get<components["schemas"]["Clip"]>(`/api/clips/${id}`); if (result.data.playback_url) window.open(result.data.playback_url, "_blank", "noopener"); else toast.err("Chưa có nguồn phát clip"); } catch (error) { toast.err(errorMessage(error)); }
  };
  const failures = jobs.data?.filter((job) => job.status === "failed") ?? [];
 const days=(metrics?.daily_processing ?? []).map(day => new Date(day.date+"T00:00:00Z"));
 const dayCounts=(metrics?.daily_processing ?? []).map(day => day.count);
  const maxCount = Math.max(1, ...dayCounts);
  const points = dayCounts.map((count, index) => `${index / Math.max(1, days.length - 1) * 600},${220 - count / maxCount * 180}`).join(" ");
  const report = () => {
    const blob = new Blob([JSON.stringify({ month, metrics, storage: health.data?.storage, jobs: jobs.data, clips: clips.data, health: health.data }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "bao-cao-cms.json"; link.click(); URL.revokeObjectURL(url);
  };
  return <div className="dashboard-page">
    <div className="page-header"><div><h2>Tổng quan hệ thống</h2><p>Chào mừng quay trở lại, {username}. Đây là hiệu suất xử lý hôm nay.</p></div><div className="page-actions"><button className="btn-secondary" onClick={report} disabled={!metrics || !jobs.data}>Tải báo cáo</button><Link className="btn-primary" to="/queue">Tải video mới</Link></div></div>
    <div className="stat-grid">
      <Stat label="Tổng video xử lý" icon="video_file" value={metrics?.total_videos ?? "—"} hint={`${metrics?.processed_videos ?? "—"} video đã xử lý · Không gồm đã xóa`} />
      <Stat label="Tỷ lệ job thành công" hintIcon="check_circle" icon="auto_awesome" value={metrics?.success_rate == null ? "—" : `${metrics.success_rate.toFixed(1)}%`} hint="Hoàn tất / (hoàn tất + lỗi)" />
      <Stat label="Dung lượng lưu trữ" icon="database" split value={fmtBytes(health.data?.storage?.total_bytes)} hint={health.data?.storage_error ?? "MinIO · Video gốc, clip và thumbnail"} />
      <Stat label="Người dùng hoạt động" hintIcon="radio_button_checked" icon="person_play" value={metrics?.active_users ?? "—"} hint="Có tương tác trong 15 phút qua" />
    </div>
    <div className="dashboard-middle">
      <section className="card panel-body"><div className="chart-heading"><h4>Xu hướng xử lý Video (tháng UTC)</h4><select className="input compact-input" aria-label="Khoảng thời gian thống kê" value={previousMonth ? "previous" : "current"} onChange={(event) => setPreviousMonth(event.target.value === "previous")}><option value="current">Tháng này</option><option value="previous">Tháng trước</option></select></div>
        {health.isLoading ? <Skeleton h={260} /> : health.isError || health.data?.metrics_error ? <ErrorState msg={health.data?.metrics_error ?? errorMessage(health.error)} onRetry={() => health.refetch()} /> : !days.length ? <Empty msg="Chưa có thống kê xử lý" /> : <><svg className="trend-chart" viewBox="0 0 600 250" preserveAspectRatio="none" role="img" aria-label="Số video xử lý hoàn tất theo ngày"><defs><linearGradient id="chart-area" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#461599" stopOpacity=".12" /><stop offset="1" stopColor="#461599" stopOpacity="0" /></linearGradient></defs><polygon points={`0,220 ${points} 600,220`} fill="url(#chart-area)" /><polyline points={points} fill="none" stroke="#461599" strokeWidth="3" /><line x1="0" y1="220" x2="600" y2="220" stroke="#cbc3d5" /></svg><div className="chart-dates">{Array.from({ length: 6 }, (_, index) => <span key={index}>{days[Math.round(index * (days.length - 1) / 5)].toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", timeZone: "UTC" })}</span>)}</div></>}
      </section>
      <section className="card panel-body"><h4>Cảnh báo hệ thống</h4><div className="system-alerts">
        {jobs.isError && <ErrorState msg={errorMessage(jobs.error)} onRetry={() => jobs.refetch()} />}
        {failures.slice(0, 2).map((job) => <Link to={`/queue?status=failed&video_id=${job.video_id}`} key={job.id} className="system-alert is-error"><Icon name="warning" size={24} /><div><strong>Lỗi xử lý video</strong><p>{job.error_log ?? job.video_id}</p>{job.updated_at && <p className="alert-time mono">{fmtISO(job.updated_at)}</p>}</div></Link>)}
        <div className="system-alert"><Icon name="info" size={24} /><div><strong>Model AI</strong>{health.isLoading ? <Skeleton /> : <p>{health.isError || health.data?.ai_available === false ? "AI không khả dụng" : health.data?.models_loaded?.join(", ") || "Chưa nạp model"}</p>}</div></div>
        <div className="system-alert neutral"><Icon name="storage" size={24} /><div><strong>Trạng thái inference</strong><p>Thiết bị: {health.data?.device ?? "—"} · CPU {health.data?.cpu_util?.toFixed(1) ?? "—"}%</p><p>Hàng đợi: {health.data?.queue_depth ?? "—"}</p></div></div>
      </div><Link className="btn-text" to="/queue">Xem tất cả log <Icon name="arrow_forward" size={16} /></Link></section>
    </div>
    <section className="card table-card"><div className="panel-heading"><h4>Highlight AI mới nhất</h4><Link className="btn-text" to="/published">Quản lý Highlight</Link></div><div className="table-scroll"><table className="data-table"><thead><tr><th>Video</th><th>Thời lượng</th><th>Độ tin cậy AI</th><th>Trạng thái</th><th>Hành động</th></tr></thead><tbody>{clips.data?.slice(0, 5).map((clip) => <tr key={clip.id}><td><div className="media-cell"><Thumbnail src={clip.thumbnail_url} duration={(clip.end_time ?? 0) - (clip.start_time ?? 0)} showTime={false} /><div><strong>{clip.title}</strong><p className="micro mono">{clip.id}</p></div></div></td><td className="mono">{fmtSec((clip.end_time ?? 0) - (clip.start_time ?? 0))}</td><td><div className={`score-cell ${(clip.average_score ?? 0) < 75 ? "is-low" : ""}`}>{clip.average_score?.toFixed(0) ?? "—"}%<div className="progress-track"><span style={{ width: `${clip.average_score ?? 0}%` }} /></div></div></td><td><StatusBadge status={clip.status ?? "draft"} variant="caps" /></td><td><div className="row-actions"><Link className="icon-button" aria-label="Biên tập highlight" to={`/highlight?video_id=${clip.video_id}`}><Icon name="edit" size={20} /></Link><button className="icon-button" aria-label={`Mở tải clip ${clip.title}`} disabled={clip.status !== "published"} onClick={() => clip.id && download(clip.id)}><Icon name="download" size={20} /></button></div></td></tr>)}</tbody></table></div>{clips.isLoading ? <div className="panel-body"><Skeleton h={48} /></div> : clips.isError ? <ErrorState msg={errorMessage(clips.error)} onRetry={() => clips.refetch()} /> : !clips.data?.length && <Empty msg="Chưa có highlight. Tải video mới để bắt đầu." />}<div className="table-more"><Link className="btn-text" to="/published">Tải thêm dữ liệu <Icon name="expand_more" size={18} /></Link></div></section>
    <Link className="dashboard-fab" aria-label="Phân tích video mới" to="/queue"><Icon name="add" /><span className="fab-tip">Phân tích video mới</span></Link>
  </div>;
}
function Stat({ label, icon, value, hint, hintIcon, split }: { label: string; icon: string; value: number | string; hint: string; hintIcon?: string; split?: boolean }) {
  const parts = split ? String(value).match(/^(\S+)\s+(\S+)$/) : null;   // Stitch storage card: number 32px + unit body-md
  return <div className="card stat-card"><div className="stat-label"><span>{label}</span><Icon name={icon} /></div><div><div className="stat-value">{parts ? <>{parts[1]}<span className="stat-unit"> {parts[2]}</span></> : value}</div><p className="stat-hint">{hintIcon && <Icon name={hintIcon} size={14} />}{hint}</p></div></div>;
}

import { Modal } from "../components/common/Modal";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useDropzone } from "../components/common/useDropzone";
import { useUploadVideo, useCmsJobs, useCmsJob, useCmsVideos } from "../hooks/useCms";
import { useSystemHealth } from "../hooks/useAuth";
import { useUploadStore } from "../stores/uploadStore";
import { StatusBadge } from "../components/common/StatusBadge";
import { Icon } from "../components/common/Icon";
import { Thumbnail, Pagination } from "../components/common/Media";
import { Skeleton, Empty, ErrorState } from "../components/common/Skeleton";
import { useToast } from "../components/common/Toast";
import { apiClient, errorMessage } from "../lib/apiClient";
import { stageLabel } from "../lib/statusMap";
import { fmtSec, fmtISO } from "../lib/time";

function ErrorLogModal({ id, onClose }: { id: string; onClose: () => void }) {
  const job = useCmsJob(id);
  return <Modal  onClose={onClose}><section   aria-label="Chi tiết lỗi xử lý" className="card modal" onClick={(e) => e.stopPropagation()}><h3>Chi tiết lỗi xử lý</h3><p className="micro mono">{id}</p>{job.isLoading ? <Skeleton h={80} /> : job.isError ? <ErrorState msg={errorMessage(job.error)} onRetry={() => job.refetch()} /> : <pre className="error-log">{job.data?.error_log ?? "Không có lỗi"}</pre>}<div className="page-actions"><button className="btn-primary" onClick={onClose}>Đóng</button></div></section></Modal>;
}
export default function QueuePage() {
  const dropzone = useDropzone({ accept: ".mp4,.mkv", maxSize: 2 * 1024 ** 3 });
  const up = useUploadVideo();
  const upload = useUploadStore();
  const jobs = useCmsJobs();
  const videos = useCmsVideos({});
  const health = useSystemHealth();
  const qc = useQueryClient();
  const toast = useToast();
  const [params] = useSearchParams();
  const [filter, setFilter] = useState(params.get("status") ?? "");
  useEffect(() => { setFilter(params.get("status") ?? ""); setPage(1); }, [params]);
  const [sort, setSort] = useState("newest");
  const [page, setPage] = useState(1);
  const [errId, setErrId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const titleFor = (id?: string) => videos.data?.items?.find((video) => video.id === id)?.title ?? id ?? "—";
  const search = params.get("q")?.toLocaleLowerCase("vi") ?? "";
  const items = (jobs.data ?? []).filter((job) => (!filter || job.status === filter) && (!search || titleFor(job.video_id).toLocaleLowerCase("vi").includes(search))).sort((a, b) => sort === "title" ? titleFor(a.video_id).localeCompare(titleFor(b.video_id), "vi") : (b.updated_at ?? "").localeCompare(a.updated_at ?? ""));
  const doUpload = async () => {
    if (!dropzone.file) return;
    const file = dropzone.file;
    upload.start(file);
    const form = new FormData(); form.append("file", file); form.append("title", file.name);
    try { await up.mutateAsync(form); upload.done(); dropzone.resetFile(); toast.ok("Đã tải video — đang xử lý AI"); }
    catch (error) { if (!useUploadStore.getState().controller?.signal.aborted) upload.fail(errorMessage(error)); }
  };
  const jobAction = async (id: string, action: "retry" | "cancel") => {
    if (action === "cancel" && !confirm("Hủy xử lý video này?")) return;
    setBusyId(id);
    try { await apiClient.post(`/api/cms/jobs/${id}/${action}`); await qc.invalidateQueries({ queryKey: ["jobs"] }); await qc.invalidateQueries({ queryKey: ["videos"] }); toast.ok(action === "retry" ? "Đã yêu cầu xử lý lại" : "Đã hủy xử lý"); } catch (error) { toast.err(errorMessage(error)); } finally { setBusyId(null); }
  };
  const progress = upload.total ? Math.min(100, Math.round(upload.loaded / upload.total * 100)) : 0;
  return <div>
    <div className="upload-monitor">
      <div className={`dropzone ${dropzone.isDragActive ? "is-dragging" : ""}`} {...dropzone.getRootProps()}><input {...dropzone.getInputProps()} /><span className="upload-mark"><Icon name="upload_file" size={32} /></span><h3>Tải lên video mới</h3><p>Kéo và thả tệp video vào đây hoặc chọn từ máy tính. Hỗ trợ định dạng MP4, MKV (tối đa 2GB).</p><span className="btn-primary">Chọn video</span>{dropzone.error && <p role="alert" className="error-text">{dropzone.error}</p>}</div>
      <div className="monitor-grid">
        <Monitor label="CPU Usage" icon="memory" value="—" note="Chưa có dữ liệu CPU" />
        <Monitor label="GPU Load" icon="developer_board" value={health.data ? `${health.data.gpu_util ?? 0}%` : "—"} progress={health.data?.gpu_util} />
        <Monitor label="VRAM Status" icon="settings_input_component" value={health.data ? `${health.data.gpu_vram_used ?? 0} GB` : "—"} note={health.isError ? "AI không khả dụng" : "Bộ nhớ GPU đang sử dụng"} />
        <Monitor label="Hàng đợi" icon="list_alt" value={health.data?.queue_depth ?? "—"} note={`${jobs.data?.filter((job) => job.status === "running").length ?? 0} job đang chạy`} />
      </div>
    </div>
    {(dropzone.file || upload.status !== "idle") && <div className="card upload-progress"><div className="media-cell"><Icon name="video_file" /><div><strong>{dropzone.file?.name ?? upload.file?.name}</strong><p className="micro">{((dropzone.file?.size ?? upload.total) / 1024 ** 2).toFixed(1)} MB</p></div></div>{upload.status === "uploading" ? <><div className="min-zero upload-meter"><span>{progress}%</span><div className="progress-track"><span style={{ width: `${progress}%` }} /></div></div><button className="btn-outline" onClick={() => upload.cancel()}>Hủy tải lên</button></> : <>{dropzone.file && <button className="btn-primary" disabled={up.isPending} onClick={doUpload}>Tải lên</button>}{upload.status === "success" && <span className="badge ai-badge"><Icon name="check_circle" size={16} />Đã tải lên</span>}<button className="icon-button" aria-label="Bỏ tệp đã chọn" onClick={() => { dropzone.resetFile(); upload.reset(); }}><Icon name="close" /></button></>}{upload.error && <p role="alert" className="error-text">{upload.error}</p>}</div>}
    <section className="card table-card"><div className="panel-heading"><div className="queue-heading"><h3>Hàng đợi xử lý</h3><div className="segmented">{[["", "Tất cả"], ["running", "Đang xử lý"], ["completed", "Đã xong"], ["failed", "Lỗi"]].map(([status, label]) => <button key={status} aria-pressed={filter === status} onClick={() => { setFilter(status); setPage(1); }}>{label}</button>)}</div></div><div className="page-actions"><select aria-label="Sắp xếp hàng đợi" className="input compact-input" value={sort} onChange={(e) => setSort(e.target.value)}><option value="newest">Sắp xếp: Mới nhất</option><option value="title">Sắp xếp: Tên A-Z</option></select><select className="input compact-input" aria-label="Bộ lọc trạng thái job" value={filter} onChange={(e) => { setFilter(e.target.value); setPage(1); }}><option value="">Bộ lọc: Tất cả</option><option value="pending">Đang chờ</option><option value="running">Đang xử lý</option><option value="completed">Hoàn tất</option><option value="failed">Thất bại</option></select></div></div>
      <div className="table-scroll"><table className="data-table queue-table"><thead><tr><th>Thumbnail & Tiêu đề</th><th>Người đăng</th><th>Thời lượng</th><th>Trạng thái hiện tại</th><th>Tiến độ</th><th>Thời gian</th><th>Thao tác</th></tr></thead><tbody>{items.slice((page - 1) * 10, page * 10).map((job) => { const video = videos.data?.items?.find((item) => item.id === job.video_id); return <tr key={job.id}><td><div className="media-cell"><Thumbnail src={video?.thumbnail_url} duration={video?.duration_seconds} /><div><strong>{titleFor(job.video_id)}</strong><p className="micro mono">{job.video_id}</p></div></div></td><td className="muted">—</td><td className="mono">{video ? fmtSec(video.duration_seconds ?? 0) : "—"}</td><td><StatusBadge status={job.status ?? "pending"} /><p className="micro">{stageLabel[job.current_stage ?? ""] ?? "—"}</p></td><td className="queue-progress"><span className="micro mono">{job.progress ?? 0}%</span><div className="progress-track"><span style={{ width: `${job.progress ?? 0}%`, background: job.status === "failed" ? "var(--error)" : undefined }} /></div></td><td className="micro">{job.updated_at ? fmtISO(job.updated_at) : "—"}</td><td><div className="row-actions">{job.status === "completed" ? <Link className="btn-secondary" to={`/highlight?video_id=${job.video_id}`}>Xem kết quả</Link> : job.status === "failed" ? <><button className="icon-button" aria-label="Thử lại xử lý" disabled={busyId === job.id} onClick={() => job.id && jobAction(job.id, "retry")}><Icon name="replay" /></button><button className="icon-button danger" aria-label="Xem log lỗi" onClick={() => setErrId(job.id ?? null)}><Icon name="error" /></button></> : <button className="icon-button" aria-label="Hủy xử lý" disabled={busyId === job.id} onClick={() => job.id && jobAction(job.id, "cancel")}><Icon name="pause_circle" /></button>}</div></td></tr>; })}</tbody></table></div>
      {jobs.isLoading ? <div className="panel-body"><Skeleton h={64} /><Skeleton h={64} /></div> : jobs.isError ? <ErrorState msg={errorMessage(jobs.error)} onRetry={() => jobs.refetch()} /> : !items.length && <Empty msg="Chưa có job khớp bộ lọc" />}<Pagination page={page} total={items.length} size={10} onPage={setPage} />
    </section>
    <div className="stage-legend">{[["hourglass_empty", "Đang chờ"], ["grid_view", "Tách khung"], ["record_voice_over", "Giọng nói"], ["auto_awesome", "Chấm điểm"], ["account_tree", "Embedding"], ["description", "Tóm tắt"], ["check_circle", "Hoàn tất"], ["cancel", "Thất bại"]].map(([icon, label]) => <div key={label}><Icon name={icon} /><span>{label}</span></div>)}</div>
    {errId && <ErrorLogModal id={errId} onClose={() => setErrId(null)} />}
  </div>;
}
function Monitor({ label, icon, value, note, progress }: { label: string; icon: string; value: string | number; note?: string; progress?: number }) {
  return <div className="card monitor-card"><div className="stat-label"><span>{label}</span><Icon name={icon} /></div><div><div className="monitor-value mono">{value}</div>{progress !== undefined && <div className="progress-track"><span style={{ width: `${progress}%` }} /></div>}{note && <p className="micro">{note}</p>}</div></div>;
}

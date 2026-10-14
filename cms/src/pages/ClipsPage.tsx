import { Modal } from "../components/common/Modal";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import type { components } from "../api-types";
import { useClips, usePublishClip, useDeleteClip, useCmsVideos, useCmsJobs } from "../hooks/useCms";
import { apiClient, errorMessage } from "../lib/apiClient";
import { StatusBadge } from "../components/common/StatusBadge";
import { Icon } from "../components/common/Icon";
import { Thumbnail, Pagination } from "../components/common/Media";
import { Skeleton, Empty, ErrorState } from "../components/common/Skeleton";
import { VideoPlayer } from "../components/player/VideoPlayer";
import { useToast } from "../components/common/Toast";
import { fmtSec, fmtISO } from "../lib/time";

export default function ClipsPage() {
  const [params] = useSearchParams();
  const search = params.get("q")?.toLocaleLowerCase("vi") ?? "";
  const [tab, setTab] = useState("published");
  const [filterOpen, setFilterOpen] = useState(false);
  const [videoId, setVideoId] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string[]>([]);
  const [edit, setEdit] = useState<components["schemas"]["Clip"] | null>(null);
  const [preview, setPreview] = useState<components["schemas"]["Clip"] | null>(null);
  const [busy, setBusy] = useState(false);
  const list = useClips({ video_id: videoId || undefined });
  const videos = useCmsVideos({ page: tab === "original" ? page : 1 });
  const jobs = useCmsJobs();
  const publish = usePublishClip();
  const remove = useDeleteClip();
  const qc = useQueryClient();
  const toast = useToast();
  const allClips = list.data ?? [];
  const clips = allClips.filter((clip) => (tab === "all" || clip.status === tab) && (!search || clip.title?.toLocaleLowerCase("vi").includes(search)));
  const rows = tab === "original" ? (videos.data?.items ?? []).map((video) => ({ id: video.id, title: video.title, thumbnail: video.thumbnail_url, duration: video.duration_seconds ?? 0, status: video.status ?? "uploaded", videoId: video.id, category: video.category?.name, createdAt: video.created_at, clip: undefined as components["schemas"]["Clip"] | undefined })) : clips.slice((page - 1) * 10, page * 10).map((clip) => ({ id: clip.id, title: clip.title, thumbnail: clip.thumbnail_url, duration: (clip.end_time ?? 0) - (clip.start_time ?? 0), status: clip.status ?? "draft", videoId: clip.video_id, category: videos.data?.items?.find((video) => video.id === clip.video_id)?.category?.name, createdAt: clip.created_at, clip }));
  const query = tab === "original" ? videos : list;
  const total = tab === "original" ? videos.data?.total ?? 0 : clips.length;
  const selectTab = (value: string) => { setTab(value); setPage(1); setSelected([]); };
  const bulkDelete = async () => {
    if (!selected.length || !confirm(`Ẩn ${selected.length} nội dung đã chọn?`)) return;
    setBusy(true);
    try { for (const id of selected) { if (tab === "original") await apiClient.delete(`/api/cms/videos/${id}`); else await remove.mutateAsync(id); } setSelected([]); await qc.invalidateQueries({ queryKey: ["videos"] }); toast.ok("Đã ẩn nội dung"); } catch (error) { toast.err(errorMessage(error)); } finally { setBusy(false); }
  };
  const openPreview = async (clip: components["schemas"]["Clip"]) => {
    try { const result = await apiClient.get<components["schemas"]["Clip"]>(`/api/clips/${clip.id}`); setPreview(result.data); } catch (error) { toast.err(errorMessage(error)); }
  };
  return <div>
    <div className="page-header"><div><h2>Thư viện nội dung</h2><p>Quản lý và theo dõi trạng thái các video trong hệ thống.</p></div><div className="page-actions"><button className="btn-outline" aria-expanded={filterOpen} onClick={() => setFilterOpen((open) => !open)}><Icon name="filter_list" size={18} />Bộ lọc nâng cao</button><button className="btn-outline danger" disabled={!selected.length || busy} onClick={bulkDelete}><Icon name="delete_sweep" size={18} />Xóa hàng loạt</button></div></div>
    <div className="tabs" role="tablist" aria-label="Loại nội dung">{[["published", "Đã xuất bản", allClips.filter((clip) => clip.status === "published").length], ["original", "Video gốc", videos.data?.total ?? 0], ["all", "Clip highlight", allClips.length], ["draft", "Bản nháp", allClips.filter((clip) => clip.status === "draft").length], ["rejected", "Đã ẩn", allClips.filter((clip) => clip.status === "rejected").length]].map(([value, label, count]) => <button key={value} role="tab" aria-selected={tab === value} onClick={() => selectTab(String(value))}>{label} ({count})</button>)}</div>
    {filterOpen && <div className="card filters"><label htmlFor="clip-video">VIDEO:<select id="clip-video" className="input" value={videoId} disabled={tab === "original"} onChange={(event) => { setVideoId(event.target.value); setPage(1); }}><option value="">Tất cả video</option>{videos.data?.items?.map((video) => <option key={video.id} value={video.id}>{video.title}</option>)}</select></label></div>}
    <section className="card table-card"><div className="table-scroll"><table className="data-table library-table"><thead><tr><th><input type="checkbox" aria-label="Chọn tất cả nội dung trên trang" checked={!!rows.length && rows.every((item) => selected.includes(item.id ?? ""))} onChange={(event) => setSelected(event.target.checked ? rows.flatMap((item) => item.id ? [item.id] : []) : [])} /></th><th>Thumbnail & Tiêu đề</th><th>Phân loại</th><th>Thời lượng</th><th>Trạng thái</th><th>Lượt xem</th><th>Người sửa</th><th>Cập nhật</th><th>Thao tác</th></tr></thead><tbody>{rows.map((item) => <tr key={item.id}><td><input type="checkbox" aria-label={`Chọn ${item.title}`} checked={selected.includes(item.id ?? "")} onChange={(event) => setSelected((ids) => event.target.checked ? [...ids, item.id ?? ""] : ids.filter((id) => id !== item.id))} /></td><td><div className="media-cell"><Thumbnail src={item.thumbnail} duration={item.duration} /><div><strong>{item.title}</strong><p className="micro mono">ID: {item.id}</p></div></div></td><td><strong>{item.clip ? "Clip highlight" : "Video gốc"}</strong><p className="micro">{item.category ?? "—"}</p></td><td className="mono">{fmtSec(item.duration)}</td><td><StatusBadge status={item.status} />{item.clip && <p className="micro">AI: {item.clip.average_score?.toFixed(0) ?? "—"} điểm</p>}</td><td className="mono">—</td><td className="muted">—</td><td className="micro">{item.createdAt ? fmtISO(item.createdAt) : "—"}</td><td><div className="row-actions">{item.clip ? <><button className="icon-button" aria-label={`Xem clip ${item.title}`} disabled={item.status !== "published"} onClick={() => item.clip && openPreview(item.clip)}><Icon name="visibility" size={20} /></button><button className="icon-button" aria-label={`Sửa clip ${item.title}`} onClick={() => setEdit(item.clip ?? null)}><Icon name="edit" size={20} /></button>{item.status === "draft" && <button className="icon-button" aria-label={`Xuất bản ${item.title}`} disabled={publish.isPending} onClick={() => item.id && publish.mutate(item.id, { onSuccess: () => toast.ok("Đã xuất bản clip"), onError: (error) => toast.err(errorMessage(error)) })}><Icon name="publish" size={20} /></button>}<button className="icon-button danger" aria-label={`Ẩn clip ${item.title}`} disabled={remove.isPending || item.status === "rejected"} onClick={() => item.id && confirm("Ẩn clip này khỏi thư viện công khai?") && remove.mutate(item.id, { onSuccess: () => toast.ok("Đã ẩn clip"), onError: (error) => toast.err(errorMessage(error)) })}><Icon name="delete" size={20} /></button></> : <Link className="icon-button" aria-label="Biên tập video" to={item.status === "processed" ? `/subtitles?video_id=${item.videoId}` : "/queue"}><Icon name="edit" size={20} /></Link>}</div></td></tr>)}</tbody></table></div>
      {query.isLoading ? <div className="panel-body"><Skeleton h={64} /><Skeleton h={64} /></div> : query.isError ? <ErrorState msg={errorMessage(query.error)} onRetry={() => query.refetch()} /> : !rows.length && <Empty msg="Chưa có nội dung trong mục này" />}
      <Pagination page={page} total={total} size={tab === "original" ? 20 : 10} onPage={setPage} />
    </section>
    <div className="stat-grid library-stats">{[["storage", "Dung lượng sử dụng", "—", "Chưa có dữ liệu dung lượng"], ["speed", "Hiệu suất render AI", "—", "Chưa có dữ liệu hiệu suất"], ["visibility", "Tổng lượt xem tháng", "—", "Chưa có dữ liệu lượt xem"], ["pending_actions", "Đang chờ xử lý", jobs.data?.filter((job) => job.status === "pending" || job.status === "running").length ?? "—", "Tác vụ đang chờ hoặc đang chạy"]].map(([icon, label, value, hint]) => <div key={label} className="card stat-card"><div className="stat-label"><Icon name={String(icon)} size={20} /><span>{label}</span></div><div><div className="monitor-value">{value}</div><p className="micro">{hint}</p></div></div>)}</div>
    {edit && <EditModal clip={edit} onClose={() => setEdit(null)} />}
    {preview && <Modal  onClose={() => setPreview(null)}><section className="card modal preview-modal"   aria-label="Xem clip" onClick={(event) => event.stopPropagation()}><h3>{preview.title}</h3><VideoPlayer src={preview.playback_url} poster={preview.thumbnail_url} /><div className="page-actions"><button className="btn-primary" onClick={() => setPreview(null)}>Đóng</button></div></section></Modal>}
  </div>;
}
function EditModal({ clip, onClose }: { clip: components["schemas"]["Clip"]; onClose: () => void }) {
  const [title, setTitle] = useState(clip.title ?? "");
  const [saving, setSaving] = useState(false);
  const qc = useQueryClient();
  const toast = useToast();
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); setSaving(true);
    try { await apiClient.put(`/api/cms/clips/${clip.id}`, { title: title.trim() }); await qc.invalidateQueries({ queryKey: ["clips"] }); toast.ok("Đã lưu clip"); onClose(); } catch (error) { toast.err(errorMessage(error)); } finally { setSaving(false); }
  };
  return <Modal  onClose={onClose}><form className="card modal"   aria-label="Sửa clip" onClick={(event) => event.stopPropagation()} onSubmit={save}><h3>Sửa clip</h3><label className="field"><span className="field-label">Tiêu đề</span><input className="input" value={title} onChange={(event) => setTitle(event.target.value)} required autoFocus /></label><div className="page-actions"><button type="button" className="btn-outline" onClick={onClose}>Hủy</button><button className="btn-primary" disabled={!title.trim() || saving}>{saving ? "Đang lưu…" : "Lưu"}</button></div></form></Modal>;
}

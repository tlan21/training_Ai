import { Modal } from "../components/common/Modal";
import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import type { components } from "../api-types";
import { useCmsVideos, useCmsAnalysis, useCategories } from "../hooks/useCms";
import { apiClient, errorMessage } from "../lib/apiClient";
import { StatusBadge } from "../components/common/StatusBadge";
import { Skeleton, Empty, ErrorState } from "../components/common/Skeleton";
import { Icon } from "../components/common/Icon";
import { Thumbnail, Pagination } from "../components/common/Media";
import { useToast } from "../components/common/Toast";
import { fmtSec, fmtISO } from "../lib/time";

export default function VideosPage() {
  const [params] = useSearchParams();
  const [status, setStatus] = useState<NonNullable<components["schemas"]["Video"]["status"]> | "">("");
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [edit, setEdit] = useState<components["schemas"]["Video"] | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
const search = params.get("q")?.trim() ?? "";
  const list = useCmsVideos({ status: status || undefined, page, q: search || undefined, category_id: category || undefined, date_from: from || undefined, date_to: to || undefined });
  useEffect(() => {setPage(1);setSelected([]);},[search,status,category,from,to]);
  const cats = useCategories();
  const qc = useQueryClient();
  const toast = useToast();
  const items = list.data?.items ?? [];
  const remove = async (ids: string[]) => {
    if (!confirm(`Xóa ${ids.length} video đã chọn? Các clip tương ứng cũng sẽ bị ẩn.`)) return;
    try { for (const id of ids) await apiClient.delete(`/api/cms/videos/${id}`); setSelected([]); toast.ok("Đã xóa video"); } catch (error) { toast.err(errorMessage(error)); } finally { await qc.invalidateQueries({ queryKey: ["videos"] }); await qc.invalidateQueries({ queryKey: ["clips"] }); }
  };
  // Stitch per-status actions: stop a running job / retry a failed one (same job endpoints as the Queue; latest job first)
  const jobAction = async (videoId: string, action: "retry" | "cancel") => {
    if (action === "cancel" && !confirm("Dừng xử lý video này?")) return;
    try {
      const job = (await apiClient.get<components["schemas"]["Job"][]>("/api/cms/jobs", { params: { video_id: videoId } })).data.find(item => item.video_id === videoId);
      if (!job?.id) throw new Error("Không tìm thấy job xử lý của video");
      await apiClient.post(`/api/cms/jobs/${job.id}/${action}`);
      toast.ok(action === "cancel" ? "Đã gửi yêu cầu dừng xử lý" : "Đã xếp lại video vào hàng đợi");
    } catch (error) { toast.err(errorMessage(error)); } finally { await qc.invalidateQueries({ queryKey: ["videos"] }); await qc.invalidateQueries({ queryKey: ["jobs"] }); }
  };
  const toggle = (id: string, checked: boolean) => setSelected((ids) => checked ? [...ids, id] : ids.filter((value) => value !== id));
  return <div className="videos-page">
    <div className="page-header"><div><h2>Danh sách Video</h2><p>Quản lý và theo dõi quy trình xử lý AI cho tất cả tài nguyên video.</p></div><Link className="btn-primary" to="/queue"><Icon name="cloud_upload" />Tải lên video</Link></div>
    <div className="card filters">
      <label>DANH MỤC:<select className="input" value={category} onChange={(e) => setCategory(e.target.value)}><option value="">Tất cả video</option>{cats.data?.map((cat) => <option key={cat.id} value={cat.id}>{cat.name}</option>)}</select></label>
      <div className="status-chips"><span className="field-label">Trạng thái:</span>{([["", "Tất cả"], ["processed", "Đã xử lý"], ["processing", "Đang xử lý"], ["failed", "Lỗi AI"], ["deleted", "Đã xóa"]] as const).map(([value, label]) => <button key={value} className={status === value ? "is-active" : ""} aria-pressed={status === value} onClick={() => { setStatus(value); setPage(1); setSelected([]); }}>{label}</button>)}</div>
      <label className="date-range-label">KHOẢNG NGÀY:<span className="date-range"><input type="date" aria-label="Từ ngày" value={from} onChange={(e) => setFrom(e.target.value)} /><span className="date-sep">→</span><input type="date" aria-label="Đến ngày" value={to} min={from} onChange={(e) => setTo(e.target.value)} /></span></label>
      <button className="icon-button" aria-label="Xóa bộ lọc" onClick={() => { setCategory(""); setFrom(""); setTo(""); setStatus(""); setPage(1); }}><Icon name="filter_list" /></button>
      
      {!!selected.length && <button className="btn-outline danger" onClick={() => remove(selected)}><Icon name="delete_sweep" size={18} />Xóa {selected.length} video</button>}
    </div>
    <section className="card table-card"><div className="table-scroll"><table className="data-table videos-table"><thead><tr><th><input type="checkbox" aria-label="Chọn tất cả video trên trang" checked={!!items.length && items.every((video) => selected.includes(video.id ?? ""))} onChange={(e) => setSelected(e.target.checked ? items.flatMap((video) => video.id ? [video.id] : []) : [])} /></th><th>Thumbnail / Tiêu đề</th><th>Ngày tải lên</th><th>Thời lượng</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>{items.map((video) => <tr key={video.id}><td><input type="checkbox" aria-label={`Chọn ${video.title}`} checked={selected.includes(video.id ?? "")} onChange={(e) => video.id && toggle(video.id, e.target.checked)} /></td><td><div className="media-cell"><Thumbnail src={video.thumbnail_url} duration={video.duration_seconds} /><div><strong>{video.title}</strong><p className="cell-sub">{video.id}</p>{video.category && <span className="badge ai-badge">{video.category.name}</span>}</div></div></td><td className="cell-date">{video.created_at ? fmtISO(video.created_at) : "—"}</td><td className="cell-mono">{fmtSec(video.duration_seconds ?? 0)}</td><td><StatusBadge status={video.status ?? "uploaded"} variant="pill" /></td><td><div className="row-actions">{video.status === "failed" ? <button className="icon-button" aria-label={`Thử lại ${video.title}`} onClick={() => video.id && jobAction(video.id, "retry")}><Icon name="refresh" size={20} /></button> : <>{video.status === "processed" ? <Link className="icon-button" aria-label={`Xem highlight ${video.title}`} to={`/highlight?video_id=${video.id}`}><Icon name="visibility" size={20} /></Link> : <Link className="icon-button" aria-label="Xem tiến trình xử lý" to="/queue"><Icon name="analytics" size={20} /></Link>}<button className="icon-button" aria-label={`Biên tập ${video.title}`} onClick={() => setEdit(video)}><Icon name="edit" size={20} /></button></>}{video.status === "uploaded" || video.status === "processing" ? <button className="icon-button row-stop" aria-label={`Dừng xử lý ${video.title}`} onClick={() => video.id && jobAction(video.id, "cancel")}><Icon name="stop_circle" size={20} /></button> : <button className="icon-button row-delete" aria-label={`Xóa ${video.title}`} onClick={() => video.id && remove([video.id])}><Icon name="delete" size={20} /></button>}</div></td></tr>)}</tbody></table></div>
      {list.isLoading ? <div className="panel-body"><Skeleton h={48} /><Skeleton h={48} /><Skeleton h={48} /></div> : list.isError ? <ErrorState msg={errorMessage(list.error)} onRetry={() => list.refetch()} /> : !items.length && <Empty msg="Không có video khớp" />}
      <Pagination page={page} total={list.data?.total ?? 0} label="video" onPage={(next) => { setPage(next); setSelected([]); }} />
    </section>
    {edit && <CategoryModal video={edit} onClose={() => setEdit(null)} />}
  </div>;
}
function CategoryModal({ video, onClose }: { video: components["schemas"]["Video"]; onClose: () => void }) {
  const cats = useCategories();
  const analysis = useCmsAnalysis(video.status === "processed" ? video.id ?? "" : "");
  const qc = useQueryClient();
  const toast = useToast();
  const [category, setCategory] = useState(video.category?.id ?? "");
  const [saving, setSaving] = useState(false);
  const save = async () => {
    setSaving(true);
    try { await apiClient.put(`/api/cms/videos/${video.id}/category`, { category_id: category }); await qc.invalidateQueries({ queryKey: ["videos"] }); await qc.invalidateQueries({ queryKey: ["video", video.id] }); toast.ok("Đã xác nhận danh mục"); onClose(); } catch (error) { toast.err(errorMessage(error)); } finally { setSaving(false); }
  };
  return <Modal  onClose={onClose}><section className="card modal"   aria-label="Biên tập video" onClick={(e) => e.stopPropagation()}><h3>Biên tập video</h3><p>{video.title}</p><div className="field"><label htmlFor="video-category">Danh mục</label><select className="input" id="video-category" value={category} onChange={(e) => setCategory(e.target.value)}><option value="">Chọn danh mục</option>{cats.data?.map((cat) => <option key={cat.id} value={cat.id}>{cat.name}</option>)}</select></div>{analysis.data?.category_suggestion && <p className="category-suggestion"><Icon name="auto_awesome" size={18} />AI gợi ý: {analysis.data.category_suggestion}</p>}{cats.isError && <ErrorState msg={errorMessage(cats.error)} onRetry={() => cats.refetch()} />}<div className="page-actions"><button className="btn-outline" onClick={onClose}>Hủy</button><button className="btn-primary" disabled={!category || saving} onClick={save}>{saving ? "Đang lưu…" : "Xác nhận danh mục"}</button></div>{video.status === "processed" && <Link className="btn-text" to={`/subtitles?video_id=${video.id}`}>Phụ đề & Tóm tắt <Icon name="arrow_forward" size={16} /></Link>}</section></Modal>;
}

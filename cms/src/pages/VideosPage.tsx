import { Modal } from "../components/common/Modal";
import { useState } from "react";
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
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [edit, setEdit] = useState<components["schemas"]["Video"] | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const list = useCmsVideos({ status: status || undefined, page });
  const cats = useCategories();
  const qc = useQueryClient();
  const toast = useToast();
  const search = params.get("q")?.toLocaleLowerCase("vi") ?? "";
  const items = (list.data?.items ?? []).filter((video) => (!category || video.category?.id === category) && (!search || video.title?.toLocaleLowerCase("vi").includes(search)) && (!from || (video.created_at ?? "").slice(0, 10) >= from) && (!to || (video.created_at ?? "").slice(0, 10) <= to));
  const remove = async (ids: string[]) => {
    if (!confirm(`Xóa ${ids.length} video đã chọn? Các clip tương ứng cũng sẽ bị ẩn.`)) return;
    try { for (const id of ids) await apiClient.delete(`/api/cms/videos/${id}`); setSelected([]); toast.ok("Đã xóa video"); } catch (error) { toast.err(errorMessage(error)); } finally { await qc.invalidateQueries({ queryKey: ["videos"] }); await qc.invalidateQueries({ queryKey: ["clips"] }); }
  };
  const toggle = (id: string, checked: boolean) => setSelected((ids) => checked ? [...ids, id] : ids.filter((value) => value !== id));
  return <div>
    <div className="page-header"><div><h2>Danh sách Video</h2><p>Quản lý và theo dõi quy trình xử lý AI cho tất cả tài nguyên video.</p></div><Link className="btn-primary" to="/queue"><Icon name="cloud_upload" size={20} />Tải lên video</Link></div>
    <div className="card filters">
      <label>DANH MỤC:<select className="input" value={category} onChange={(e) => setCategory(e.target.value)}><option value="">Tất cả video</option>{cats.data?.map((cat) => <option key={cat.id} value={cat.id}>{cat.name}</option>)}</select></label>
      <div className="status-chips"><span className="field-label">Trạng thái:</span>{[["", "Tất cả"], ["processed", "Đã duyệt"], ["processing", "Đang xử lý"], ["failed", "Lỗi AI"]].map(([value, label]) => <button key={value} className={status === value ? "is-active" : ""} aria-pressed={status === value} onClick={() => { setStatus(value); setPage(1); setSelected([]); }}>{label}</button>)}</div>
      <label>KHOẢNG NGÀY:<input className="input" type="date" aria-label="Từ ngày" value={from} onChange={(e) => setFrom(e.target.value)} /><Icon name="arrow_forward" size={16} /><input className="input" type="date" aria-label="Đến ngày" value={to} min={from} onChange={(e) => setTo(e.target.value)} /></label>
      <button className="icon-button" aria-label="Xóa bộ lọc" onClick={() => { setCategory(""); setFrom(""); setTo(""); setStatus(""); setPage(1); }}><Icon name="filter_list" /></button>
      {(category || from || to || search) && <span className="micro">Bộ lọc tên, danh mục và ngày áp dụng trên trang hiện tại.</span>}
      {!!selected.length && <button className="btn-outline danger" onClick={() => remove(selected)}><Icon name="delete_sweep" size={18} />Xóa {selected.length} video</button>}
    </div>
    <section className="card table-card"><div className="table-scroll"><table className="data-table videos-table"><thead><tr><th><input type="checkbox" aria-label="Chọn tất cả video trên trang" checked={!!items.length && items.every((video) => selected.includes(video.id ?? ""))} onChange={(e) => setSelected(e.target.checked ? items.flatMap((video) => video.id ? [video.id] : []) : [])} /></th><th>Thumbnail / Tiêu đề</th><th>Ngày tải lên</th><th>Thời lượng</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>{items.map((video) => <tr key={video.id}><td><input type="checkbox" aria-label={`Chọn ${video.title}`} checked={selected.includes(video.id ?? "")} onChange={(e) => video.id && toggle(video.id, e.target.checked)} /></td><td><div className="media-cell"><Thumbnail src={video.thumbnail_url} duration={video.duration_seconds} /><div><strong>{video.title}</strong><p className="micro mono">{video.id}</p>{video.category && <span className="badge ai-badge">{video.category.name}</span>}</div></div></td><td className="micro">{video.created_at ? fmtISO(video.created_at) : "—"}</td><td className="mono">{fmtSec(video.duration_seconds ?? 0)}</td><td><StatusBadge status={video.status ?? "uploaded"} /></td><td><div className="row-actions">{video.status === "processed" ? <Link className="icon-button" aria-label={`Xem highlight ${video.title}`} to={`/highlight?video_id=${video.id}`}><Icon name="visibility" size={20} /></Link> : <Link className="icon-button" aria-label="Xem tiến trình xử lý" to="/queue"><Icon name="analytics" size={20} /></Link>}<button className="icon-button" aria-label={`Biên tập ${video.title}`} onClick={() => setEdit(video)}><Icon name="edit" size={20} /></button><button className="icon-button danger" aria-label={`Xóa ${video.title}`} onClick={() => video.id && remove([video.id])}><Icon name="delete" size={20} /></button></div></td></tr>)}</tbody></table></div>
      {list.isLoading ? <div className="panel-body"><Skeleton h={48} /><Skeleton h={48} /><Skeleton h={48} /></div> : list.isError ? <ErrorState msg={errorMessage(list.error)} onRetry={() => list.refetch()} /> : !items.length && <Empty msg="Không có video khớp" />}
      <Pagination page={page} total={list.data?.total ?? 0} onPage={(next) => { setPage(next); setSelected([]); }} />
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

import { Modal } from "../components/common/Modal";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { components } from "../api-types";
import { useCategories, useCreateCategory, useUpdateCategory, useDeleteCategory, useCmsVideos } from "../hooks/useCms";
import { useToast } from "../components/common/Toast";
import { Skeleton, Empty, ErrorState } from "../components/common/Skeleton";
import { Icon } from "../components/common/Icon";
import { Thumbnail } from "../components/common/Media";
import { errorMessage } from "../lib/apiClient";

const icons: Record<string, string> = { "Bóng đá": "sports_soccer", "Thể thao": "sports_soccer", "Game": "sports_esports", "Ca nhạc": "music_note", "Tin tức": "newspaper", "Giải trí": "movie", "Highlight": "auto_awesome", "Giáo dục": "school", "Du lịch": "flight", "Ẩm thực": "restaurant", "Công nghệ": "memory" };
export default function CategoriesPage() {
  const [params] = useSearchParams();
  const search = params.get("q")?.toLocaleLowerCase("vi") ?? "";
  const categoryMatches = (category: components["schemas"]["Category"]) => !search || category.name?.toLocaleLowerCase("vi").includes(search);
  const list = useCategories();
  const videos = useCmsVideos({});
  const create = useCreateCategory();
  const update = useUpdateCategory();
  const remove = useDeleteCategory();
  const toast = useToast();
  const [editing, setEditing] = useState<components["schemas"]["Category"] | null>(null);
  const [name, setName] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    try { if (editing?.id) await update.mutateAsync({ id: editing.id, name: name.trim() }); else await create.mutateAsync({ name: name.trim() }); setEditing(null); setCreateOpen(false); setName(""); toast.ok("Đã lưu danh mục"); } catch (error) { toast.err(errorMessage(error)); }
  };
  return <div>
    <nav className="breadcrumb"><span>CMS</span><Icon name="chevron_right" size={14} /><strong>Quản lý Danh mục</strong></nav><div className="page-header"><div><h2>Quản lý Danh mục</h2><p>Phân loại và cấu hình quy tắc gán tự động cho kho nội dung video.</p></div><button className="btn-primary" onClick={() => { setName(""); setCreateOpen(true); }}><Icon name="add" size={20} />Thêm danh mục mới</button></div>
    <div className="categories-grid"><section className="card table-card category-table-card"><div className="table-scroll"><table className="data-table category-table"><thead><tr><th>Icon</th><th>Tên danh mục</th><th>Mô tả</th><th>Video</th><th>Quy tắc</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>{list.data?.filter(categoryMatches).map((category) => { const system = category.name === "Highlight"; const count = videos.data?.items?.filter((video) => video.category?.id === category.id).length; return <tr key={category.id}><td><span className={`category-icon ${system ? "system" : ""}`}><Icon name={icons[category.name ?? ""] ?? "category"} /></span></td><td><strong className={system ? "primary-text" : ""}>{category.name}</strong>{system && <p><span className="badge ai-badge">HỆ THỐNG</span></p>}</td><td className="micro">{system ? "Danh mục mặc định cho clip Highlight AI." : "—"}</td><td className="mono" title="Số video gán danh mục trên trang dữ liệu hiện tại">{count ?? "—"}</td><td className="micro">{system ? <span className="primary-text"><Icon name="bolt" size={14} />Tự động (Khóa)</span> : "Thủ công"}</td><td><span className="badge category-status">Đã duyệt</span></td><td><div className="row-actions">{system ? <><Link className="icon-button" to="/published" aria-label="Xem Highlight"><Icon name="visibility" size={20} /></Link><Link className="icon-button" to="/settings" aria-label="Cài đặt Highlight"><Icon name="settings" size={20} /></Link></> : <><button className="icon-button" aria-label={`Sửa danh mục ${category.name}`} onClick={() => { setEditing(category); setName(category.name ?? ""); }}><Icon name="edit" size={20} /></button><button className="icon-button" aria-label={`Xóa danh mục ${category.name}`} disabled={remove.isPending} onClick={() => category.id && confirm(`Xóa danh mục "${category.name}"?`) && remove.mutate(category.id, { onSuccess: () => toast.ok("Đã xóa danh mục"), onError: (error) => toast.err(errorMessage(error)) })}><Icon name="delete" size={20} /></button></>}</div></td></tr>; })}</tbody></table></div>{list.isLoading ? <div className="panel-body"><Skeleton h={48} /><Skeleton h={48} /><Skeleton h={48} /></div> : list.isError ? <ErrorState msg={errorMessage(list.error)} onRetry={() => list.refetch()} /> : !list.data?.filter(categoryMatches).length && <Empty msg="Chưa có danh mục khớp" />}</section>
    <div className="category-aside"><section className="card panel-body"><div className="category-rule-heading"><h4><Icon name="circle" size={20} />Cấu hình Tự động gán AI</h4><button className="btn-text" disabled title="Chưa hỗ trợ cấu hình quy tắc">Chỉnh sửa</button></div><div className="category-rule"><span className="avatar"><Icon name="lock" /></span><div><strong>Danh mục Highlight AI</strong><p>AI đề xuất phân loại. Biên tập viên xác nhận danh mục trước khi xuất bản.</p></div></div><div className="category-keyword"><span><Icon name="tag" size={20} />Gán theo từ khóa AI</span><label className="switch"><span /><input type="checkbox" aria-label="Gán theo từ khóa AI" disabled checked={false} readOnly /></label></div></section>
      <section className="card category-recent"><div className="panel-heading"><h4>Gán video gần đây</h4><button className="icon-button" aria-label="Tải lại video gần đây" onClick={() => videos.refetch()}><Icon name="refresh" size={20} /></button></div><div className="recent-videos">{videos.isLoading ? <Skeleton h={64} /> : videos.isError ? <ErrorState msg={errorMessage(videos.error)} onRetry={() => videos.refetch()} /> : !(videos.data?.items?.some((video) => video.category)) && <Empty msg="Chưa có video được gán danh mục" />}{videos.data?.items?.filter((video) => video.category).slice(0, 4).map((video) => <Link key={video.id} className="recent-video" to={`/subtitles?video_id=${video.id}`}><Thumbnail src={video.thumbnail_url} duration={video.duration_seconds} /><div className="min-zero"><strong>{video.title}</strong><span className="badge ai-badge">{video.category?.name}</span></div></Link>)}</div><div className="category-recent-footer"><Link className="btn-text" to="/videos">Xem tất cả video</Link></div></section>
    </div></div>
    {(editing || createOpen) && <Modal  onClose={() => { setEditing(null); setCreateOpen(false); }}><form className="card modal"   aria-label={editing ? "Sửa danh mục" : "Thêm danh mục mới"} onClick={(event) => event.stopPropagation()} onSubmit={save}><h3>{editing ? "Sửa danh mục" : "Thêm danh mục mới"}</h3><label className="field"><span className="field-label">Tên danh mục</span><input className="input" value={name} onChange={(event) => setName(event.target.value)} placeholder="Tên danh mục" required autoFocus /></label><div className="page-actions"><button type="button" className="btn-outline" onClick={() => { setEditing(null); setCreateOpen(false); }}>Hủy</button><button className="btn-primary" disabled={!name.trim() || create.isPending || update.isPending}>{create.isPending || update.isPending ? "Đang lưu…" : "Lưu"}</button></div></form></Modal>}
  </div>;
}

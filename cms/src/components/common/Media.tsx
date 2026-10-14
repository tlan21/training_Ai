import { useCmsVideos } from "../../hooks/useCms";
import { useSearchParams } from "react-router-dom";
import { Icon } from "./Icon";
import { fmtSec } from "../../lib/time";

export function Thumbnail({ src, duration = 0 }: { src?: string | null; duration?: number }) {
  return <div className="thumbnail">{src ? <img src={src} alt="" loading="lazy" onError={(e) => { e.currentTarget.style.display = "none"; }} /> : <Icon name="video_file" />}<span className="thumbnail-time mono">{fmtSec(duration)}</span></div>;
}
export function Pagination({ page, total, size = 20, onPage }: { page: number; total: number; size?: number; onPage: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / size));
  return <div className="pagination"><span>Hiển thị {total ? (page - 1) * size + 1 : 0}–{Math.min(page * size, total)} trên {total} mục</span><div className="pagination-controls"><button className="icon-button" aria-label="Trang trước" disabled={page <= 1} onClick={() => onPage(page - 1)}><Icon name="chevron_left" /></button><button className="page-number" aria-label={`Trang ${page}`}>{page}</button><span className="muted">/ {pages}</span><button className="icon-button" aria-label="Trang sau" disabled={page >= pages} onClick={() => onPage(page + 1)}><Icon name="chevron_right" /></button></div></div>;
}
export function VideoPicker({ beforeChange }: { beforeChange?: () => boolean } = {}) {
  const [params, setParams] = useSearchParams();
  const list = useCmsVideos({ status: "processed" });
  const id = params.get("video_id") ?? "";
  const items = list.data?.items ?? [];
  return <div className="video-picker"><label htmlFor="review-video" className="field-label">Video đang biên tập</label><select id="review-video" className="input" value={id} onChange={(e) => { if (!beforeChange || beforeChange()) setParams({ video_id: e.target.value }); }}><option value="">{list.isLoading ? "Đang tải video…" : "Chọn video đã xử lý"}</option>{id && !items.some((video) => video.id === id) && <option value={id}>{id}</option>}{items.map((video) => <option key={video.id} value={video.id}>{video.title}</option>)}</select></div>;
}

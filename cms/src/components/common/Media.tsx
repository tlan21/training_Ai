import { Fragment, useState } from "react";
import { ErrorState } from "./Skeleton";
import { errorMessage } from "../../lib/apiClient";
import { useCmsVideos } from "../../hooks/useCms";
import { useSearchParams } from "react-router-dom";
import { Icon } from "./Icon";
import { fmtSec } from "../../lib/time";

export function Thumbnail({ src, duration = 0, showTime = true }: { src?: string | null; duration?: number; showTime?: boolean }) {
  return <div className="thumbnail">{src ? <img src={src} alt="" loading="lazy" onError={(e) => { e.currentTarget.style.display = "none"; }} /> : <Icon name="video_file" />}{showTime && <span className="thumbnail-time mono">{fmtSec(duration)}</span>}</div>;
}
export function Pagination({ page, total, size = 20, onPage, label = "mục" }: { page: number; total: number; size?: number; onPage: (page: number) => void; label?: string }) {
  const pages = Math.max(1, Math.ceil(total / size));
  const from = total ? (page - 1) * size + 1 : 0, to = Math.min(page * size, total);
  // Stitch: numbered 32px page buttons with an ellipsis gap; first/last/current±1 kept.
  const nums = [...new Set([1, page - 1, page, page + 1, pages])].filter(n => n >= 1 && n <= pages).sort((a, b) => a - b);
  return <div className="pagination"><span>Hiển thị <strong>{from}-{to}</strong> của <strong>{total}</strong> {label}</span><div className="pagination-controls"><button className="icon-button" aria-label="Trang trước" disabled={page <= 1} onClick={() => onPage(page - 1)}><Icon name="chevron_left" /></button>{nums.map((n, i) => <Fragment key={n}>{i > 0 && n - nums[i - 1] > 1 && <span className="page-gap">…</span>}<button className={`page-number ${n === page ? "is-active" : ""}`} aria-label={`Trang ${n}`} aria-current={n === page ? "page" : undefined} onClick={() => onPage(n)}>{n}</button></Fragment>)}<button className="icon-button" aria-label="Trang sau" disabled={page >= pages} onClick={() => onPage(page + 1)}><Icon name="chevron_right" /></button></div></div>;
}
export function VideoPicker({ beforeChange }: { beforeChange?: () => boolean } = {}) {
  const [params, setParams] = useSearchParams();
 const [search,setSearch]=useState("");const [page,setPage]=useState(1);
 const list = useCmsVideos({ status: "processed", q:search || undefined,page });
  const id = params.get("video_id") ?? "";
  const items = list.data?.items ?? [];
  return <div className="video-picker"><input className="input" aria-label="Tìm video đã xử lý" placeholder="Tìm video đã xử lý…" maxLength={200} value={search} onChange={event=>{setSearch(event.target.value);setPage(1);}}/><label htmlFor="review-video" className="field-label">Video đang biên tập</label><select id="review-video" className="input" value={id} onChange={(e) => { if (!beforeChange || beforeChange()) setParams({ video_id: e.target.value }); }}><option value="">{list.isLoading ? "Đang tải video…" : "Chọn video đã xử lý"}</option>{id && !items.some((video) => video.id === id) && <option value={id}>{id}</option>}{items.map((video) => <option key={video.id} value={video.id}>{video.title}</option>)}</select>{list.isError && <ErrorState msg={errorMessage(list.error)} onRetry={()=>list.refetch()}/ >}{(list.data?.total ?? 0)>20 && <Pagination page={page} total={list.data?.total ?? 0} onPage={setPage}/>}</div>;
}

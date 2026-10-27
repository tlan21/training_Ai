"use client";
/* eslint-disable @next/next/no-img-element -- Browser blob previews are local and bypass the image optimizer. */
import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQueries, useQuery } from "@tanstack/react-query";
import type { components } from "@/api-types";
import { AppNav, MobileHeader } from "@/components/AppNav";
import { BottomNav } from "@/components/BottomNav";
import { Icon } from "@/components/Icon";
import { Thumbnail, PageState } from "@/components/Media";
import { apiClient } from "@/lib/apiClient";
import { useAuthStore } from "@/stores/authStore";
import { formatTime, type VisualResults, type TextResults } from "@/lib/content";
function Search() {
    const sp = useSearchParams();
    const [tab, setTab] = useState<"text" | "visual">(sp.get("tab") === "visual" ? "visual" : "text");
    const [q, setQ] = useState(sp.get("q") || "");
    const [debounced, setDebounced] = useState(q);
    const ready = useAuthStore(s => s.ready);
    const [file, setFile] = useState<File | null>(null);
    const [revision, setRevision] = useState(0);
    const [preview, setPreview] = useState("");
    const [uploadError, setUploadError] = useState("");
    const [similarity, setSimilarity] = useState(85);
    const [threshold, setThreshold] = useState(85);
    const [duration, setDuration] = useState<number | null>(null);
    const [sort, setSort] = useState("match");
    const [view, setView] = useState("grid");
    const [count, setCount] = useState(12);
    const [recent, setRecent] = useState<string[]>([]);
    const imageInput = useRef<HTMLInputElement>(null);
    const cameraInput = useRef<HTMLInputElement>(null);
    useEffect(() => { const timer = setTimeout(() => setDebounced(q.trim()), 300); return () => clearTimeout(timer); }, [q]);
    useEffect(() => { const timer = setTimeout(() => setThreshold(similarity), 300); return () => clearTimeout(timer); }, [similarity]);
    useEffect(() => { if (!file) {
        setPreview("");
        return;
    } const url = URL.createObjectURL(file); setPreview(url); return () => URL.revokeObjectURL(url); }, [file]);
    useEffect(() => { const value = sessionStorage.getItem("client-searches"); if (value) {
        try {
            const stored: unknown = JSON.parse(value);
            if (Array.isArray(stored))
                setRecent(stored.filter((v): v is string => typeof v === "string").slice(0, 3));
        }
        catch { }
    } }, []);
    useEffect(() => { if (!debounced)
        return; setRecent(old => { const next = [debounced, ...old.filter(v => v !== debounced)].slice(0, 3); sessionStorage.setItem("client-searches", JSON.stringify(next)); return next; }); }, [debounced]);
    useEffect(() => { if (sp.get("tab") === "visual")
        setTab("visual"); }, [sp]);
    const text = useQuery({ queryKey: ["search", debounced], enabled: ready && tab === "text" && !!debounced, queryFn: async ({ signal }) => (await apiClient.get<TextResults>("/api/search", { params: { q: debounced }, signal })).data });
    const visual = useQuery({ queryKey: ["visual-search", revision, threshold], enabled: ready && tab === "visual" && !!file, retry: false, queryFn: async ({ signal }) => { const form = new FormData(); form.append("image", file!); form.append("min_similarity", String(threshold / 100)); return (await apiClient.post<VisualResults>("/api/search/visual", form, { signal })).data; } });
    const choose = (f?: File) => {
        setUploadError("");
        if (!f)
            return;
        if (!["image/jpeg", "image/png", "image/webp"].includes(f.type) || f.size > 5 * 1024 * 1024) {
            setUploadError("Chọn ảnh JPG, PNG hoặc WebP, tối đa 5 MB.");
            setFile(null);
            return;
        }
        setFile(f);
        setRevision(v => v + 1);
        setCount(12);
    };
    const visualItems = visual.data?.results || [];
    const textItems = text.data?.items || [];
    const ids = Array.from(new Set((tab === "visual" ? visualItems : textItems).map(r => r.video_id).filter((id): id is string => !!id)));
    const meta = useQueries({ queries: ids.map(id => ({ queryKey: ["video", id], enabled: ready, queryFn: async () => (await apiClient.get<components["schemas"]["VideoDetail"]>(`/api/videos/${id}`)).data })) });
    const videoById = new Map(meta.map((m, i) => [ids[i], m.data]));
    const rows = tab === "visual" ? visualItems.map(r => ({ id: r.video_id, time: r.timestamp || 0, score: r.similarity_score, title: videoById.get(r.video_id || "")?.title, description: videoById.get(r.video_id || "")?.description, thumb: r.thumbnail_url })) : textItems.map(r => ({ id: r.video_id, time: r.timestamp || 0, score: undefined, title: r.title, description: r.matched_text, thumb: videoById.get(r.video_id || "")?.thumbnail_url }));
    const filtered = rows.filter(r => { if (duration === null)
        return true; const n = videoById.get(r.id || "")?.duration_seconds; if (n == null)
        return false; return duration === 0 ? n < 60 : duration === 1 ? n >= 60 && n <= 300 : duration === 2 ? n > 300 && n <= 1200 : n > 1200; }).sort((a, b) => sort === "newest" ? (videoById.get(b.id || "")?.created_at || "").localeCompare(videoById.get(a.id || "")?.created_at || "") : (b.score || 0) - (a.score || 0));
    const requested = tab === "text" ? !!debounced : !!file;
    const resultQuery = tab === "text" ? text : visual;
    const loading = requested && resultQuery.isPending;
    const changeTab = (value: "text" | "visual") => { setTab(value); setDuration(null); setCount(12); };
    const uploadArea = <div className="upload-grid">
  <button className="image-uploader" onClick={() => imageInput.current?.click()} onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); choose(e.dataTransfer.files[0]); }}>
   <span><Icon name="photo_library" size={28}/></span><span className="mobile-only">Chọn từ thư viện</span><span className="desktop-only">Kéo và thả ảnh vào đây</span><small className="desktop-only">Hoặc</small><span className="btn-primary desktop-only">Chọn ảnh</span>
  </button>
  <button className="image-uploader camera" onClick={() => cameraInput.current?.click()}><span><Icon name="photo_camera" size={28}/></span><span>Mở máy ảnh</span></button>
  <div className="search-preview">{preview ? <><img src={preview} alt="Ảnh tìm kiếm"/><small>{file?.name}</small></> : <><Icon name="visibility" size={36}/><span>Xem trước ảnh</span></>}</div>
 </div>;
    return <div className="content-page"><AppNav active="search" search={false}/><MobileHeader title="Tìm kiếm" back><Link className="icon-button" href="/profile?view=library&tab=history" aria-label="Lịch sử xem"><Icon name="history"/></Link></MobileHeader>
 <main className="search-main"><h1 className="search-title">Tìm kiếm đa phương thức</h1><div className="search-layout"><section className="search-input-panel">
 <div className="search-tabs" role="tablist" aria-label="Phương thức tìm kiếm"><button role="tab" aria-selected={tab === "text"} className={tab === "text" ? "active" : ""} onClick={() => changeTab("text")}><span className="mobile-only">Văn bản</span><span className="desktop-only">Tìm bằng văn bản</span></button><button role="tab" aria-selected={tab === "visual"} className={tab === "visual" ? "active" : ""} onClick={() => changeTab("visual")}><span className="mobile-only">Hình ảnh</span><span className="desktop-only">Tìm bằng hình ảnh</span></button></div>
 {tab === "text" ? <><form className="input-wrap search-input" onSubmit={e => { e.preventDefault(); setDebounced(q.trim()); }}><span className="input-icon input-icon--left"><Icon name="search" size={24}/></span><input aria-label="Mô tả video hoặc khoảnh khắc" className="input input--with-left-icon input--with-right-icon" placeholder="Nhập mô tả video hoặc khoảnh khắc..." value={q} onChange={e => { setQ(e.target.value); setCount(12); }}/><button type="button" className="input-icon input-icon--right input-icon--action mobile-only" disabled title="Tìm bằng giọng nói chưa khả dụng" aria-label="Tìm bằng giọng nói"><Icon name="mic" size={24}/></button></form>
 <div className="search-tags"><span className="desktop-only">Tìm kiếm gần đây:</span>{["#cinematic", "#thien-nhien", "#nấu-ăn", "#vlog"].map(tag => <button className="mobile-only" key={tag} onClick={() => setQ(tag.slice(1))}>{tag}</button>)}{recent.map(item => <button className="desktop-only" key={item} onClick={() => setQ(item)}>{item}</button>)}{!recent.length && <small className="desktop-only">Chưa có tìm kiếm gần đây.</small>}</div></> : <>{uploadArea}<div className="search-info"><Icon name="info"/><p>AI sẽ tìm kiếm video có khung hình tương đồng với ảnh bạn cung cấp.</p></div>{uploadError && <p className="error-banner upload-error" role="alert">{uploadError}</p>}</>}
 <input ref={imageInput} type="file" accept="image/jpeg,image/png,image/webp" hidden aria-label="Ảnh từ thư viện" onChange={e => { choose(e.target.files?.[0]); e.target.value = ""; }}/><input ref={cameraInput} type="file" accept="image/*" capture="environment" hidden aria-label="Ảnh từ máy ảnh" onChange={e => { choose(e.target.files?.[0]); e.target.value = ""; }}/>
 </section>
 <aside className={`search-filters ${tab === "text" ? "text-filters" : ""}`}><h2 className="filter-title"><Icon name="tune"/>Bộ lọc</h2><div className="filter-controls">
 <div><label htmlFor="similarity">Mức độ tương đồng: <span style={{ color: "var(--primary)" }}>{similarity}%</span></label><input id="similarity" type="range" min={50} max={100} value={similarity} disabled={tab === "text"} onChange={e => setSimilarity(Number(e.target.value))}/><div className="filter-scale"><span>Rộng</span><span>Chính xác</span></div></div>
 <div className="filter-duration"><label>Thời lượng video</label><div className="duration-buttons">{[["Ngắn", "< 1p"], ["Vừa", "1–5p"], ["Dài", "5–20p"], ["Rất dài", "> 20p"]].map(([label, range], i) => <button key={label} className={duration === i ? "active" : ""} aria-pressed={duration === i} onClick={() => setDuration(duration === i ? null : i)}>{label}<span>{range}</span></button>)}</div></div>
 <div className="filter-sort"><label htmlFor="sort">Sắp xếp theo</label><select id="sort" value={sort} onChange={e => setSort(e.target.value)}><option value="match">Độ khớp cao nhất</option><option value="newest">Mới nhất</option><option disabled>Phổ biến nhất (chưa có dữ liệu)</option></select></div>
 </div></aside></div>
 <section className="search-results-section"><div className="section-heading"><h2>Kết quả tìm kiếm <span className="result-count">({filtered.length} kết quả)</span></h2><div className="result-view-controls"><button className={`icon-button ${view === "grid" ? "active" : ""}`} onClick={() => setView("grid")} aria-label="Hiển thị lưới"><Icon name="grid_view"/></button><button className={`icon-button ${view === "list" ? "active" : ""}`} onClick={() => setView("list")} aria-label="Hiển thị danh sách"><Icon name="view_list"/></button></div></div>
 {loading || resultQuery.error || !filtered.length ? <PageState loading={loading} error={requested ? resultQuery.error : null} empty={!requested ? "Nhập mô tả hoặc chọn ảnh để tìm kiếm." : "Không có kết quả phù hợp."} retry={() => resultQuery.refetch()}/> : <div className={`search-results ${view === "list" ? "list" : ""}`}>{filtered.slice(0, count).map((result, i) => <article className="search-result" key={`${result.id}-${result.time}-${i}`}>
 <Link className="media-frame" href={`/videos/${result.id}?t=${result.time}`} aria-label={result.title || result.id}><Thumbnail src={result.thumb}/><time className="time-badge">{formatTime(videoById.get(result.id || "")?.duration_seconds)}</time></Link>
 <div className="result-body"><h3 className="line-clamp-2">{result.title || result.id}</h3>{result.score != null && <span className={`match-badge ${result.score >= .95 ? "high" : ""}`}>{Math.round(result.score * 100)}% TƯƠNG ĐỒNG</span>}<span className="jump-scene"><Icon name="schedule" size={14}/>Xuất hiện tại {formatTime(result.time)}</span><p className="result-description">{result.description || "Khung hình tương đồng trong video."}</p><div className="result-footer"><span>VidsAI</span><Link href={`/videos/${result.id}?t=${result.time}`}>Chi tiết</Link></div></div><Link href={`/videos/${result.id}?t=${result.time}`} className="result-play" aria-label={`Đến cảnh ${formatTime(result.time)}`}><Icon name="play_arrow" size={20}/></Link>
 </article>)}</div>}
 {filtered.length > count && <div className="load-more"><button className="pill" onClick={() => setCount(n => n + 12)}><Icon name="refresh" size={20}/>Tải thêm kết quả</button></div>}
 </section></main><BottomNav active="search"/></div>;
}
export default function SearchPage() { return <Suspense fallback={<PageState loading/>}><Search /></Suspense>; }

"use client";
import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import type { components } from "@/api-types";
import { AppNav, MobileHeader } from "@/components/AppNav";
import { BottomNav } from "@/components/BottomNav";
import { Icon } from "@/components/Icon";
import { Thumbnail, PageState } from "@/components/Media";
import { recommendationLabel, useCategories, useVideos, useClipPage, useHistory, formatTime, formatDate, type Video, type Clip } from "@/lib/content";
import { apiClient } from "@/lib/apiClient";
function VideoCard({ video, published }: {
    video: Video;
    published: boolean;
}) {
    return <Link className="video-card" href={`/videos/${video.id}`}><div className="media-frame"><Thumbnail src={video.thumbnail_url}/>{published && <span className="card-badge ai-badge"><Icon name="auto_awesome" size={12}/>AI Highlight</span>}<time className="time-badge">{formatTime(video.duration_seconds)}</time></div><h3 className="line-clamp-2">{video.title}</h3><small>VidsAI · {video.category?.name || "Video"}<br />{formatDate(video.created_at)}</small></Link>;
}
function ClipCard({ clip }: {
    clip: Clip;
}) {
    return <Link className="video-card" href={`/videos/${clip.video_id}?clip=${clip.id}`}><div className="media-frame"><Thumbnail src={clip.thumbnail_url}/><span className="card-badge ai-badge"><Icon name="auto_awesome" size={12}/>AI Highlight</span><time className="time-badge">{formatTime((clip.end_time || 0) - (clip.start_time || 0))}</time></div><h3 className="line-clamp-2">{clip.title}</h3><small>VidsAI · {formatDate(clip.created_at)}</small></Link>;
}
export default function DiscoverPage() {
    const [category, setCategory] = useState("");
    const [q, setQ] = useState("");
    const categories = useCategories();
    const newest = useVideos(category, "newest");
    const trending = useVideos(category, "trending");
    const feed = useClipPage("/api/feed");
    const history = useHistory();
    const mode = feed.data?.pages[0]?.recommendation_mode;
    const router = useRouter();
    const trendRef = useRef<HTMLDivElement>(null);
    const newItems = newest.data?.pages.flatMap(p => p.items || []) || [];
    const trendItems = trending.data?.pages.flatMap(p => p.items || []) || [];
    const clips = feed.data?.pages.flatMap(p => p.items || []) || [];
    const viewed = history.data?.pages.flatMap(p => p.items || []) || [];
    const published = new Set(clips.map(c => c.video_id));
    const hero = newItems[0];
    const analysis = useQuery({ queryKey: ["analysis", hero?.id], enabled: !!hero?.id, queryFn: async () => (await apiClient.get<components["schemas"]["PublicAnalysis"]>(`/api/videos/${hero?.id}/analysis`)).data });
    const filteredClips = category ? clips.filter(c => newItems.some(v => v.id === c.video_id) || trendItems.some(v => v.id === c.video_id)) : clips;
    const newestState = newest.isPending || newest.error || !newItems.length;
    const recommendation = feed.isPending || feed.error || !filteredClips.length;
    return <div className="content-page"><AppNav active="discover"/><MobileHeader />
 <form className="discovery-mobile-search mobile-only" onSubmit={e => { e.preventDefault(); router.push(`/search?q=${encodeURIComponent(q)}`); }}><div className="input-wrap"><span className="input-icon input-icon--left"><Icon name="search"/></span><input aria-label="Tìm kiếm video" placeholder="Tìm kiếm video, hình ảnh..." value={q} onChange={e => setQ(e.target.value)}/><Link href="/search?tab=visual" className="input-icon input-icon--right" aria-label="Tìm bằng hình ảnh"><Icon name="image_search"/></Link></div></form>
 <section className="category-chips hide-scrollbar" aria-label="Danh mục"><button className={`pill ${!category ? "active" : ""}`} onClick={() => setCategory("")}>Tất cả</button>{categories.data?.map(c => <button key={c.id} className={`pill ${category === c.id ? "active" : ""}`} onClick={() => setCategory(c.id || "")}>{c.name}</button>)}</section>
 {categories.error && <div className="content-main"><PageState error={categories.error} retry={() => categories.refetch()}/></div>}
 <main className="content-main">
 <div className="mobile-discovery">
  <section className="discovery-section"><div className="section-heading"><h2>Tiếp tục xem</h2><Link href="/profile?view=library&tab=history" className="link">Xem tất cả</Link></div>
   {history.isPending || history.error || !viewed.length ? <PageState loading={history.isPending} error={history.error} empty="Chưa có lịch sử xem." retry={() => history.refetch()}/> : <div className="continue-row hide-scrollbar">{viewed.map((item, i) => item.clip && <Link className="continue-card" href={`/videos/${item.clip.video_id}?clip=${item.clip.id}`} key={item.clip.id || i}><div className="media-frame"><Thumbnail src={item.clip.thumbnail_url}/><time className="time-badge">{formatTime((item.clip.end_time || 0) - (item.clip.start_time || 0))}</time></div><h3 className="line-clamp-2">{item.clip.title}</h3><small>VidsAI · {formatDate(item.watched_at)}</small></Link>)}</div>}
  </section>
  <section className="discovery-section"><div className="section-heading"><h2 data-recommendation-mode={mode ?? "unknown"}>{mode === "personalized" ? "Gợi ý cho bạn" : recommendationLabel(mode)}</h2></div>
   {recommendation ? <PageState loading={feed.isPending} error={feed.error} empty="Chưa có clip phù hợp." retry={() => feed.refetch()}/> : <div className="bento-grid">{filteredClips.slice(0, 3).map((clip, i) => <Link key={clip.id} className="bento-card" href={`/videos/${clip.video_id}?clip=${clip.id}`}><div className="media-frame"><Thumbnail src={clip.thumbnail_url}/>{i === 0 ? <div className="bento-overlay"><span className="ai-badge" style={{ alignSelf: "flex-start" }}>NỔI BẬT</span><h3 className="line-clamp-2">{clip.title}</h3><small>VidsAI</small></div> : <span className="card-badge ai-badge"><Icon name={i === 1 ? "play_circle" : "bolt"} size={16}/></span>}</div>{i > 0 && <h3 className="line-clamp-2">{clip.title}</h3>}</Link>)}</div>}
   {hero && <Link className="newest-callout" href={`/videos/${hero.id}`}><div className="media-frame"><Thumbnail src={hero.thumbnail_url}/></div><div><small>MỚI NHẤT</small><h3 className="line-clamp-2">{hero.title}</h3><p className="line-clamp-2">{hero.description || hero.category?.name}</p><span className="link">Xem ngay →</span></div></Link>}
  </section>
  <section className="discovery-section"><div className="section-heading"><h2><Icon name="trending_up"/>Đang thịnh hành</h2></div>{trending.isPending || trending.error || !trendItems.length ? <PageState loading={trending.isPending} error={trending.error} empty="Chưa có video." retry={() => trending.refetch()}/> : <div className="trending-row">{trendItems.slice(0, 4).map(video => <Link className="trending-card" href={`/videos/${video.id}`} key={video.id}><div className="media-frame"><Thumbnail src={video.thumbnail_url}/></div><div><h3 className="line-clamp-2">{video.title}</h3><small>VidsAI · {video.category?.name || formatDate(video.created_at)}</small></div></Link>)}</div>}</section>
 </div>
 <div className="desktop-discovery">
  <section className="discovery-section"><div className="section-heading"><h2>Highlight mới</h2><button className="link" onClick={() => newest.fetchNextPage()} disabled={!newest.hasNextPage || newest.isFetchingNextPage}>Xem tất cả <Icon name="arrow_forward" size={16}/></button></div>
   {newestState ? <PageState loading={newest.isPending} error={newest.error} empty="Chưa có video." retry={() => newest.refetch()}/> : <div className="discovery-hero">
    <Link className="discovery-hero-main" href={`/videos/${hero.id}`}><div className="media-frame"><Thumbnail src={hero.thumbnail_url}/><div className="bento-overlay">
     {published.has(hero.id) && <span className="ai-badge" style={{ alignSelf: "flex-start" }}><Icon name="auto_awesome" size={12}/>AI Highlight</span>}
     {!!analysis.data?.timeline_scores?.length && <div className="mini-heatmap">{analysis.data.timeline_scores.map((s, i) => <div key={i} style={{ flex: 1, background: (s.score || 0) > 75 ? "#ba1a1a" : (s.score || 0) >= 40 ? "#fea619" : "#630ed4" }}/>)}</div>}
     <h3 className="line-clamp-2">{hero.title}</h3><small>VidsAI · {hero.category?.name} · {formatDate(hero.created_at)}</small></div></div></Link>
    <div className="discovery-hero-side">{newItems.slice(1, 3).map((v, i) => <Link href={`/videos/${v.id}`} key={v.id}><div className="media-frame"><Thumbnail src={v.thumbnail_url}/><div className="bento-overlay"><span className="ai-badge" style={{ alignSelf: "flex-start", background: i === 0 ? "var(--secondary-container)" : "var(--primary)" }}>{i === 0 ? "MỚI" : published.has(v.id) ? "AI MOMENT" : "VIDEO"}</span><h3 className="line-clamp-2">{v.title}</h3><small>VidsAI · {v.category?.name}</small></div></div></Link>)}</div>
   </div>}
  </section>
  <section className="discovery-section"><div className="section-heading"><h2>Đang thịnh hành</h2><div><button className="icon-button" aria-label="Video trước" onClick={() => trendRef.current?.scrollBy({ left: -350, behavior: "smooth" })}><Icon name="chevron_left"/></button><button className="icon-button" aria-label="Video tiếp theo" onClick={() => trendRef.current?.scrollBy({ left: 350, behavior: "smooth" })}><Icon name="chevron_right"/></button></div></div>
   {trending.isPending || trending.error || !trendItems.length ? <PageState loading={trending.isPending} error={trending.error} empty="Chưa có video." retry={() => trending.refetch()}/> : <div className="trending-desktop-row hide-scrollbar" ref={trendRef}>{trendItems.map(v => <VideoCard key={v.id} video={v} published={published.has(v.id)}/>)}</div>}
  </section>
  <section className="discovery-section"><div className="section-heading"><h2 data-recommendation-mode={mode ?? "unknown"}>{recommendationLabel(mode)}</h2></div>{recommendation ? <PageState loading={feed.isPending} error={feed.error} empty="Chưa có clip phù hợp." retry={() => feed.refetch()}/> : <div className="video-grid">{filteredClips.map(c => <ClipCard key={c.id} clip={c}/>)}</div>}{feed.hasNextPage && <div className="load-more"><button className="btn-outline" disabled={feed.isFetchingNextPage} onClick={() => feed.fetchNextPage()}>Tải thêm</button></div>}</section>
 </div>
 </main><BottomNav active="discover"/></div>;
}

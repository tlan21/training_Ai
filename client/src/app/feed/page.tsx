"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import type { components } from "@/api-types";
import { AppNav } from "@/components/AppNav";
import { BottomNav } from "@/components/BottomNav";
import { Icon } from "@/components/Icon";
import { PageState, Thumbnail } from "@/components/Media";
import { useClipPage, formatTime, track, shareVideo, recommendationLabel, type RecommendationMode, type Clip } from "@/lib/content";
import { apiClient, errorMessage } from "@/lib/apiClient";
import { useWatchTime } from "@/lib/useWatchTime";
function FeedClip({ clip, active, mode, onMessage }: {
    clip: Clip;
    mode?: RecommendationMode;
    active: boolean;
    onMessage: (s: string) => void;
}) {
    const ref = useRef<HTMLVideoElement>(null);
    const [playing, setPlaying] = useState(false);
    const [muted, setMuted] = useState(true);
    const [time, setTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [liked, setLiked] = useState(false);
    const [saved, setSaved] = useState(false);
    const [mediaError, setMediaError] = useState(false);
    const subs = useQuery({ queryKey: ["subtitles", clip.video_id], enabled: active && !!clip.video_id, queryFn: async () => (await apiClient.get<components["schemas"]["Subtitles"]>(`/api/videos/${clip.video_id}/subtitles`)).data });
    const analysis = useQuery({ queryKey: ["analysis", clip.video_id], enabled: active && !!clip.video_id, queryFn: async () => (await apiClient.get<components["schemas"]["PublicAnalysis"]>(`/api/videos/${clip.video_id}/analysis`)).data });
    const segment = subs.data?.segments?.find(s => time + (clip.start_time || 0) >= (s.start_time || 0) && time + (clip.start_time || 0) < (s.end_time || 0));
    const scores = analysis.data?.timeline_scores?.filter(s => (s.second || 0) >= (clip.start_time || 0) && (s.second || 0) < (clip.end_time || 0)) || [];
    useEffect(() => {
        const el = ref.current;
        if (!el)
            return;
        const update = () => { if (active && !document.hidden)
            void el.play().catch(() => setPlaying(false));
        else
            el.pause(); };
        update();
        document.addEventListener("visibilitychange", update);
        return () => { el.pause(); document.removeEventListener("visibilitychange", update); };
    }, [active, clip.playback_url]);
    useEffect(() => { if (active && clip.video_id)
        track({ video_id: clip.video_id, clip_id: clip.id, interaction_type: "click" }); }, [active, clip.video_id, clip.id]);
    useWatchTime(ref, clip.video_id, clip.id, active, clip.playback_url);
    const action = (type: "like" | "save") => { if (type === "like")
        setLiked(v => !v);
    else
        setSaved(v => !v); if (clip.video_id)
        track({ video_id: clip.video_id, clip_id: clip.id, interaction_type: type }); };
    const share = async () => { if (!clip.video_id)
        return; try {
        await shareVideo(clip.video_id, clip.id);
        if (!navigator.share)
            onMessage("Đã sao chép liên kết.");
    }
    catch (e) {
        if (!(e instanceof DOMException && e.name === "AbortError"))
            onMessage(errorMessage(e));
    } };
    return <article className="feed-clip" data-clip-id={clip.id}>
  <video ref={ref} src={clip.playback_url || undefined} poster={clip.thumbnail_url || undefined} preload={active ? "metadata" : "none"} playsInline muted={muted} loop onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onTimeUpdate={e => setTime(e.currentTarget.currentTime)} onLoadedMetadata={e => setDuration(e.currentTarget.duration)} onError={() => setMediaError(true)}/>
  <div className="feed-mobile-top"><Link href="/discover" className="icon-button" aria-label="Quay lại Khám phá"><Icon name="arrow_back" size={28}/></Link><span data-recommendation-mode={mode ?? "unknown"}>{recommendationLabel(mode)}</span><Link href="/search" className="icon-button" aria-label="Tìm kiếm"><Icon name="search" size={28}/></Link></div>
  {(!clip.playback_url || mediaError) && <div className="player-unavailable" role="alert">Không thể phát clip này.<button className="btn-outline" onClick={() => { setMediaError(false); ref.current?.load(); }}>Thử lại</button></div>}
  <button className="feed-player-button" aria-label={playing ? "Tạm dừng" : "Phát video"} onClick={() => { const el = ref.current; if (el) {
        if (el.paused)
            void el.play().catch(() => onMessage("Không thể phát video."));
        else
            el.pause();
    } }} style={{ opacity: playing ? 0 : 1 }}><Icon name={playing ? "pause" : "play_arrow"} size={36}/></button>
  <button className="feed-mute" aria-label={muted ? "Bật âm thanh" : "Tắt âm thanh"} onClick={() => setMuted(!muted)}><Icon name={muted ? "volume_off" : "volume_up"} size={20}/></button>
  <aside className="feed-actions">
   <button className="feed-action" aria-label="Thích" aria-pressed={liked} onClick={() => action("like")}><span><Icon name="favorite" size={32} filled={liked}/></span><span>{liked ? "Đã thích" : "Thích"}</span></button>
   <button className="feed-action" aria-label="Lưu clip" aria-pressed={saved} onClick={() => action("save")}><span><Icon name="bookmark" size={32} filled={saved}/></span><span>{saved ? "Đã lưu" : "Lưu"}</span></button>
   <button className="feed-action" aria-label="Chia sẻ" onClick={share}><span><Icon name="share" size={32}/></span><span>Chia sẻ</span></button>
   <Link className="feed-insights" href={`/videos/${clip.video_id}`} aria-label="Phân tích AI"><Icon name="insights" size={24}/></Link>
  </aside>
  <footer className="feed-bottom"><div className="feed-copy"><strong>@VidsAI</strong><h1 className="line-clamp-2">{clip.title}</h1><Link href={`/videos/${clip.video_id}`} className="feed-original"><Icon name="smart_display" size={18}/>Xem video gốc</Link>{segment?.text?.trim() && <div className="feed-caption"><Icon name="closed_caption" size={20}/><p>{segment.text}</p></div>}</div>
   {!!scores.length && <div className="feed-heatmap desktop-only">{scores.map((s, i) => <span key={i} title={`${Math.round(s.score || 0)}/100`} style={{ height: `${Math.max(8, s.score || 0)}%`, background: (s.score || 0) > 75 ? "#c6252b" : (s.score || 0) >= 40 ? "#fea619" : "#630ed4" }}/>)}</div>}
   <input type="range" min={0} max={duration || 1} step={.1} value={Math.min(time, duration || 1)} aria-label="Vị trí phát clip" onChange={e => { if (ref.current)
        ref.current.currentTime = Number(e.target.value); }}/>
   <div className="feed-times"><time>{formatTime(time)}</time><time>{formatTime(duration || (clip.end_time || 0) - (clip.start_time || 0))}</time></div>
  </footer>
 </article>;
}
export default function FeedPage() {
    const feed = useClipPage("/api/feed");
    const clips = feed.data?.pages.flatMap(p => p.items || []) || [];
    const [active, setActive] = useState(0);
    const [message, setMessage] = useState("");
    const root = useRef<HTMLDivElement>(null);
    const { fetchNextPage, hasNextPage, isFetchingNextPage } = feed;
    useEffect(() => { if (!message)
        return; const timer = setTimeout(() => setMessage(""), 4000); return () => clearTimeout(timer); }, [message]);
    useEffect(() => {
        const el = root.current;
        if (!el)
            return;
        const observer = new IntersectionObserver(entries => { for (const entry of entries)
            if (entry.isIntersecting)
                setActive(Number((entry.target as HTMLElement).dataset.index)); }, { root: el, threshold: .7 });
        el.querySelectorAll("[data-index]").forEach(item => observer.observe(item));
        return () => observer.disconnect();
    }, [clips.length]);
    useEffect(() => { if (active >= clips.length - 2 && hasNextPage && !isFetchingNextPage)
        void fetchNextPage(); }, [active, clips.length, hasNextPage, isFetchingNextPage, fetchNextPage]);
    const next = clips.filter((_, i) => i !== active);
    return <div className="feed-page"><AppNav active="home"/><main className="feed-layout">
  <aside className="feed-trending-nav"><Link href="/discover"><span className="icon-button"><Icon name="trending_up"/></span>Xu hướng</Link></aside>
  {feed.isPending || feed.error || !clips.length ? <div className="feed-empty"><PageState loading={feed.isPending} error={feed.error} empty="Chưa có clip được xuất bản." retry={() => feed.refetch()}/>{!feed.isPending && !feed.error && <Link href="/onboarding" className="btn-primary">Chọn chủ đề yêu thích</Link>}</div> : <div className="feed-scroll" ref={root} aria-label="Video feed">
   {clips.map((clip, i) => <div key={clip.id} data-index={i} style={{ height: "100%" }}><FeedClip clip={clip} active={active === i} mode={feed.data?.pages[0]?.recommendation_mode} onMessage={setMessage}/></div>)}
   {feed.hasNextPage && <div className="page-state"><button className="btn-primary" disabled={feed.isFetchingNextPage} onClick={() => feed.fetchNextPage()}>Tải thêm</button></div>}
  </div>}
  <section className="feed-upnext"><div className="section-heading"><h2>Sắp phát tiếp</h2><Link href="/discover" className="link">Tất cả</Link></div><div className="feed-upnext-list">{next.map(clip => <Link className="upnext-card" href={`/videos/${clip.video_id}?clip=${clip.id}`} key={clip.id}><div className="media-frame"><Thumbnail src={clip.thumbnail_url}/><time className="time-badge">{formatTime((clip.end_time || 0) - (clip.start_time || 0))}</time></div><div><h3 className="line-clamp-2">{clip.title}</h3><small>VidsAI · {formatTime((clip.end_time || 0) - (clip.start_time || 0))}</small><span className="ai-badge"><Icon name="bolt" size={16}/>AI Highlight</span></div></Link>)}{!next.length && <PageState empty="Chưa có clip tiếp theo"/>}</div><div className="feed-promo"><small>GỢI Ý</small><h3>Tạo Highlight Video của riêng bạn chỉ trong vài giây.</h3><button className="btn-primary" disabled title="Tạo highlight được thực hiện trong CMS">Thử ngay miễn phí</button></div></section>
 </main><BottomNav active="home" camera/>{message && <div className="feed-toast" role="status">{message}</div>}</div>;
}

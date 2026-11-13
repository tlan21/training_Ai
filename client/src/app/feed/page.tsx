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
import { clipSourceTime, compilationScores } from "@/lib/clipTimeline";
import { useWatchTime } from "@/lib/useWatchTime";
import { ListPicker, useClipActions } from "@/components/Library";
// INT-64: one sound preference for the whole feed (default ON, kept for the tab). Browsers refuse unmuted autoplay without a
// user gesture: the reel then plays muted, `blocked` is set and a "Bật âm thanh" pill asks for the one click that unlocks sound.
const SOUND_KEY = "feed-sound";
function FeedClip({ clip, active, mode, audible, blocked, onSound, onBlocked, onEnded, onMessage, onList }: {
    clip: Clip;
    mode?: RecommendationMode;
    active: boolean;
    audible: boolean;
    blocked: boolean;
    onSound: (on: boolean) => void;
    onBlocked: () => void;
    onEnded: () => void;
    onMessage: (s: string) => void;
    onList: (clipId: string) => void;
}) {
    const ref = useRef<HTMLVideoElement>(null);
    const audibleRef = useRef(audible);
    // Declared before the playback effect so a reel that becomes active in the same render reads the current preference.
    useEffect(() => { audibleRef.current = audible; if (ref.current)
        ref.current.muted = !audible; }, [audible]);
    const [playing, setPlaying] = useState(false);
    const [time, setTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const marks = useClipActions(clip.id, onMessage);
    const [mediaError, setMediaError] = useState(false);
    const subs = useQuery({ queryKey: ["subtitles", clip.video_id], enabled: active && !!clip.video_id, queryFn: async () => (await apiClient.get<components["schemas"]["Subtitles"]>(`/api/videos/${clip.video_id}/subtitles`)).data });
    const analysis = useQuery({ queryKey: ["analysis", clip.video_id], enabled: active && !!clip.video_id, queryFn: async () => (await apiClient.get<components["schemas"]["PublicAnalysis"]>(`/api/videos/${clip.video_id}/analysis`)).data });
    const sourceTime = clipSourceTime(clip, time);
    const segment = subs.data?.segments?.find(s => sourceTime >= (s.start_time || 0) && sourceTime < (s.end_time || 0));
    const scores = compilationScores(analysis.data?.timeline_scores || [], clip.source_segments || []).filter(s => (s.second || 0) >= (clip.start_time || 0) && (s.second || 0) < (clip.end_time || 0)) || [];
    useEffect(() => {
        const el = ref.current;
        if (!el)
            return;
        const update = () => {
            if (!active || document.hidden) {
                el.pause();
                return;
            }
            el.muted = !audibleRef.current;
            el.play().catch((e: unknown) => {
                if (!el.muted && e instanceof DOMException && e.name === "NotAllowedError") {
                    el.muted = true; // autoplay policy: keep playing silently, ask for the click that enables sound
                    onBlocked();
                    void el.play().catch(() => setPlaying(false));
                }
                else
                    setPlaying(false);
            });
        };
        update();
        document.addEventListener("visibilitychange", update);
        return () => { el.pause(); document.removeEventListener("visibilitychange", update); };
        // eslint-disable-next-line react-hooks/exhaustive-deps -- restart playback only when the reel or its source changes
    }, [active, clip.playback_url]);
    const unmute = () => { const el = ref.current; if (el) {
        el.muted = false; // inside the click: the gesture is what lets the browser play with sound
        if (el.paused)
            void el.play().catch(() => setPlaying(false));
    } onSound(true); };
    const toggle = () => { const el = ref.current; if (!el)
        return; if (el.paused)
        void el.play().catch(() => onMessage("Không thể phát video."));
    else
        el.pause(); };
    useEffect(() => { if (active && clip.video_id)
        track({ video_id: clip.video_id, clip_id: clip.id, interaction_type: "click" }); }, [active, clip.video_id, clip.id]);
    useWatchTime(ref, clip.video_id, clip.id, active, clip.playback_url, true);
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
  <video ref={ref} src={clip.playback_url || undefined} poster={clip.thumbnail_url || undefined} preload={active ? "metadata" : "none"} playsInline onClick={() => blocked ? unmute() : toggle()} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onEnded={() => { if (active)
        onEnded(); }} onTimeUpdate={e => setTime(e.currentTarget.currentTime)} onLoadedMetadata={e => setDuration(e.currentTarget.duration)} onError={() => setMediaError(true)}/>
  <div className="feed-mobile-top"><Link href="/discover" className="icon-button" aria-label="Quay lại Khám phá"><Icon name="arrow_back" size={28}/></Link><span data-recommendation-mode={mode ?? "unknown"}>{recommendationLabel(mode)}</span><Link href="/search" className="icon-button" aria-label="Tìm kiếm"><Icon name="search" size={28}/></Link></div>
  {(!clip.playback_url || mediaError) && <div className="player-unavailable" role="alert">Không thể phát clip này.<button className="btn-outline" onClick={() => { setMediaError(false); ref.current?.load(); }}>Thử lại</button></div>}
  {!playing && <button className="feed-player-button" aria-hidden="true" tabIndex={-1} onClick={toggle}><Icon name="play_arrow" size={36}/></button>}
  {active && blocked && <button className="feed-sound-hint" onClick={unmute}><Icon name="volume_off" size={18}/>Bật âm thanh</button>}
  <button className="feed-mute" aria-label={audible ? "Tắt âm thanh" : "Bật âm thanh"} onClick={() => { if (audible) {
        if (ref.current)
            ref.current.muted = true;
        onSound(false);
    }
    else
        unmute(); }}><Icon name={audible ? "volume_up" : "volume_off"} size={20}/></button>
  <aside className="feed-actions">
   <button className="feed-action" aria-label="Thích" aria-pressed={marks.liked} disabled={!marks.ready} onClick={marks.toggleLike}><span><Icon name="favorite" size={32} filled={marks.liked}/></span><span>{marks.liked ? "Đã thích" : "Thích"}</span></button>
   <button className="feed-action" aria-label="Xem sau" aria-pressed={marks.saved} disabled={!marks.ready} onClick={marks.toggleSave}><span><Icon name="schedule" size={32} filled={marks.saved}/></span><span>{marks.saved ? "Đã lưu" : "Xem sau"}</span></button>
   <button className="feed-action" aria-label="Thêm vào danh sách" aria-pressed={marks.inList} disabled={!marks.ready} onClick={() => clip.id && onList(clip.id)}><span><Icon name="playlist_add" size={32}/></span><span>Danh sách</span></button>
   <button className="feed-action" aria-label="Chia sẻ" onClick={share}><span><Icon name="share" size={32}/></span><span>Chia sẻ</span></button>
   <Link className="feed-insights" href={`/videos/${clip.video_id}`} aria-label="Phân tích AI"><Icon name="insights" size={24}/></Link>
  </aside>
  <footer className="feed-bottom"><div className="feed-copy"><strong>@VidsAI</strong><h1 className="line-clamp-2">{clip.title}</h1><Link href={`/videos/${clip.video_id}`} className="feed-original"><Icon name="smart_display" size={18}/>Xem video gốc</Link>{segment?.text?.trim() && <div className="feed-caption"><Icon name="closed_caption" size={20}/><p><span className="subtitle-draft-label">Bản nháp phụ đề AI</span>{segment.text}</p></div>}</div>
   {!!scores.length && <div className="feed-heatmap desktop-only">{scores.map((s, i) => <span key={i} title={`${Math.round(s.score || 0)}/100`} style={{ height: `${Math.max(8, s.score || 0)}%`, background: (s.score || 0) > 75 ? "#c6252b" : (s.score || 0) >= 40 ? "#fea619" : "#630ed4" }}/>)}</div>}
   <div className="feed-progress"><button className="feed-play" aria-label={playing ? "Tạm dừng" : "Phát video"} onClick={toggle}><Icon name={playing ? "pause" : "play_arrow"} size={22}/></button>
   <input type="range" min={0} max={duration || 1} step={.1} value={Math.min(time, duration || 1)} aria-label="Vị trí phát clip" onChange={e => { if (ref.current)
        ref.current.currentTime = Number(e.target.value); }}/></div>
   <div className="feed-times"><time>{formatTime(time)}</time><time>{formatTime(duration || (clip.end_time || 0) - (clip.start_time || 0))}</time></div>
  </footer>
 </article>;
}
export default function FeedPage() {
    const feed = useClipPage("/api/feed");
    const clips = feed.data?.pages.flatMap(p => p.items || []) || [];
    const [active, setActive] = useState(0);
    const [message, setMessage] = useState("");
    const [listClip, setListClip] = useState<string | null>(null);
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
    const [soundOn, setSoundOn] = useState(true);
    const [blocked, setBlocked] = useState(false);
    useEffect(() => { setSoundOn(sessionStorage.getItem(SOUND_KEY) !== "off"); }, []);
    const setSound = (on: boolean) => { setSoundOn(on); setBlocked(false); sessionStorage.setItem(SOUND_KEY, on ? "on" : "off"); };
    // Scrolling the snap container is the only way a reel becomes active (the IntersectionObserver above), so the queue and
    // auto-advance both scroll instead of setting `active` directly.
    const goTo = (i: number) => root.current?.querySelector(`[data-index="${i}"]`)?.scrollIntoView({ behavior: "smooth", block: "start" });
    const pendingAdvance = useRef<number | null>(null);
    const advance = (from: number) => {
        if (from + 1 < clips.length)
            goTo(from + 1);
        else if (hasNextPage) {
            pendingAdvance.current = from + 1;
            if (!isFetchingNextPage)
                void fetchNextPage();
        } // last reel and no more pages: stay on it (paused at the end), no wrap
    };
    useEffect(() => { const i = pendingAdvance.current; if (i != null && i < clips.length) {
        pendingAdvance.current = null;
        goTo(i);
    } }, [clips.length]);
    const current = clips[active];
    const queue = clips.slice(active + 1);
    return <div className="feed-page"><AppNav active="home"/><main className="feed-layout">
  <aside className="feed-trending-nav"><Link href="/discover"><span className="icon-button"><Icon name="trending_up"/></span>Xu hướng</Link></aside>
  {feed.isPending || feed.error || !clips.length ? <div className="feed-empty"><PageState loading={feed.isPending} error={feed.error} empty="Chưa có clip được xuất bản." retry={() => feed.refetch()}/>{!feed.isPending && !feed.error && <Link href="/onboarding" className="btn-primary">Chọn chủ đề yêu thích</Link>}</div> : <div className="feed-scroll" ref={root} aria-label="Video feed">
   {clips.map((clip, i) => <div key={clip.id} data-index={i} style={{ height: "100%" }}><FeedClip clip={clip} active={active === i} mode={feed.data?.pages[0]?.recommendation_mode} audible={soundOn && !blocked} blocked={blocked} onSound={setSound} onBlocked={() => setBlocked(true)} onEnded={() => advance(i)} onMessage={setMessage} onList={setListClip}/></div>)}
   {feed.hasNextPage && <div className="page-state"><button className="btn-primary" disabled={feed.isFetchingNextPage} onClick={() => feed.fetchNextPage()}>Tải thêm</button></div>}
  </div>}
  <section className="feed-upnext" aria-label="Sắp phát tiếp"><div className="section-heading"><h2>Sắp phát tiếp</h2><Link href="/discover" className="link">Tất cả</Link></div>
   <ol className="feed-upnext-list upnext-queue">{current && [current, ...queue].map((clip, k) => <li key={clip.id} className={`upnext-row ${k === 0 ? "is-current" : ""}`}><button onClick={() => goTo(active + k)} aria-current={k === 0 ? "true" : undefined} aria-label={`${k === 0 ? "Đang phát" : `Phát tiếp ${k}`}: ${clip.title}`}>
    <span className="upnext-pos">{k === 0 ? <Icon name="play_arrow" size={18}/> : k}</span>
    <span className="media-frame"><Thumbnail src={clip.thumbnail_url}/><time className="time-badge">{formatTime((clip.end_time || 0) - (clip.start_time || 0))}</time></span>
    <span className="upnext-text">{k === 0 && <span className="upnext-now">Đang phát</span>}<span className="upnext-title line-clamp-2">{clip.title}</span><small>VidsAI{clip.view_count != null ? ` · ${clip.view_count} lượt xem` : ""}</small></span>
   </button></li>)}</ol>
   {current && !queue.length && <p className="upnext-end">{hasNextPage ? "Đang tải thêm…" : "Đã hết danh sách phát."}</p>}</section>
 </main><BottomNav active="home" camera/>{message && <div className="feed-toast" role="status">{message}</div>}<ListPicker clipId={listClip} onClose={() => setListClip(null)}/></div>;
}

"use client";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import type { components } from "@/api-types";
import { useAuthStore } from "@/stores/authStore";
import { apiClient, errorMessage } from "@/lib/apiClient";
import { usePlayerStore, buildHighlightRanges, nextHighlightStart } from "@/stores/playerStore";
import { useWatchTime } from "@/lib/useWatchTime";
import { formatTime, formatDate, track, shareVideo } from "@/lib/content";
import { AppNav, MobileHeader } from "@/components/AppNav";
import { BottomNav } from "@/components/BottomNav";
import { Icon } from "@/components/Icon";
import { PageState, Thumbnail } from "@/components/Media";
import { Transcript } from "@/components/Transcript";
function VideoDetail() {
    const { id } = useParams<{
        id: string;
    }>();
    const search = useSearchParams();
    const ready = useAuthStore(s => s.ready);
    const video = useQuery({ queryKey: ["video", id], enabled: ready, queryFn: async () => (await apiClient.get<components["schemas"]["VideoDetail"]>(`/api/videos/${id}`)).data });
    const analysis = useQuery({ queryKey: ["analysis", id], enabled: ready, queryFn: async () => (await apiClient.get<components["schemas"]["PublicAnalysis"]>(`/api/videos/${id}/analysis`)).data });
    const subs = useQuery({ queryKey: ["subtitles", id], enabled: ready, queryFn: async () => (await apiClient.get<components["schemas"]["Subtitles"]>(`/api/videos/${id}/subtitles`)).data });
    const clips = video.data?.clips?.filter(c => c.status === "published") || [];
    const requested = Number(search.get("t") || 0);
    const validTime = Number.isFinite(requested) && requested >= 0 ? requested : 0;
    const initialClip = clips.find(c => c.id === search.get("clip")) || clips.find(c => validTime >= (c.start_time || 0) && validTime < (c.end_time || 0)) || clips[0];
    const [selected, setSelected] = useState<string | null>(null);
    const original = selected === null && !search.get("clip") ? video.data?.playback_url : null;
    const selectedClip = original ? undefined : clips.find(c => c.id === selected) || initialClip;
    const clip = useQuery({ queryKey: ["clip", selectedClip?.id], enabled: !!selectedClip?.id, queryFn: async () => (await apiClient.get<components["schemas"]["Clip"]>(`/api/clips/${selectedClip?.id}`)).data });
    const ref = useRef<HTMLVideoElement | null>(null);
    const dialog = useRef<HTMLDialogElement>(null);
    const pendingSeek = useRef<number | null>(null);
    const store = usePlayerStore();
    const [sheet, setSheet] = useState(false);
    const [message, setMessage] = useState("");
    const [mediaError, setMediaError] = useState(false);
    const [liked, setLiked] = useState(false);
    const [saved, setSaved] = useState(false);
    const [summaryOpen, setSummaryOpen] = useState(true);
    const [rate,setRate]=useState(1);
    const offset = selectedClip?.start_time || 0;
    const end = original ? video.data?.duration_seconds || 0 : selectedClip?.end_time || 0;
    const source = original || clip.data?.playback_url;
    const register = useCallback((el: HTMLVideoElement | null) => { ref.current = el; usePlayerStore.getState().register(el, offset); }, [offset]);
    useEffect(() => { setSelected(null); pendingSeek.current = validTime; setMediaError(false); }, [id, validTime]);
    useEffect(() => { if (ready)
        track({ video_id: id, interaction_type: "click" }); }, [id, ready]);
    useEffect(() => { setMediaError(false); }, [source]);
    useEffect(() => { if (!message)
        return; const timer = setTimeout(() => setMessage(""), 4500); return () => clearTimeout(timer); }, [message]);
    useEffect(() => { if (sheet && !dialog.current?.open)
        dialog.current?.showModal();
    else if (!sheet && dialog.current?.open)
        dialog.current.close(); }, [sheet]);
    useWatchTime(ref, id, selectedClip?.id, true, source);
    const seek = (time: number) => {
        if (original) { store.seekTo(time); return; }
        const target = clips.find(c => time >= (c.start_time || 0) && time < (c.end_time || 0));
        if (!target) {
            setMessage("Khoảnh khắc này chưa có clip được xuất bản. Nguồn phát video gốc chưa khả dụng.");
            return;
        }
        if (target.id !== selectedClip?.id) {
            pendingSeek.current = time;
            setSelected(target.id || null);
        }
        else
            store.seekTo(time);
    };
    const scores = useMemo(() => analysis.data?.timeline_scores || [], [analysis.data]);
    const ranges = useMemo(() => buildHighlightRanges(scores.filter(s => (s.second || 0) >= offset && (s.second || 0) < end)), [scores, offset, end]);
    const onTime = (el: HTMLVideoElement) => {
        const time = el.currentTime + offset;
        store.onTimeUpdate(time);
        if (store.autoHighlight && !ranges.some(r => time >= r.start && time < r.end)) {
            const next = nextHighlightStart(time, ranges);
            if (next !== null)
                store.seekTo(next);
            else
                store.setAuto(false);
        }
    };
    const auto = () => { const on = !store.autoHighlight; store.setAuto(on); if (on && !ranges.some(r => store.currentTime >= r.start && store.currentTime < r.end)) {
        const next = nextHighlightStart(store.currentTime, ranges);
        if (next !== null)
            store.seekTo(next);
        else
            store.setAuto(false);
    } };
    const share = async () => { try {
        await shareVideo(id, selectedClip?.id);
        if (!navigator.share)
            setMessage("Đã sao chép liên kết.");
    }
    catch (e) {
        if (!(e instanceof DOMException && e.name === "AbortError"))
            setMessage(errorMessage(e));
    } };
    const action = (type: "like" | "save") => { if (type === "like")
        setLiked(v => !v);
    else
        setSaved(v => !v); track({ video_id: id, clip_id: selectedClip?.id, interaction_type: type }); };
    const segments = subs.data?.segments || [];
    const currentSegment = segments.find(s => store.currentTime >= (s.start_time || 0) && store.currentTime < (s.end_time || 0));
    const transcriptProps = { segments, loading: subs.isPending, error: subs.error, currentTime: store.currentTime, seek, retry: () => { void subs.refetch(); }, videoId: id };
    if (video.isPending || video.error)
        return <div className="content-page"><AppNav active="discover" variant="detail"/><MobileHeader center back/><PageState loading={video.isPending} error={video.error} retry={() => video.refetch()}/><BottomNav active="library"/></div>;
    const data = video.data;
    return <div className="content-page"><AppNav active="discover" variant="detail"/><MobileHeader center back><button className="icon-button" onClick={share} aria-label="Chia sẻ video"><Icon name="share" size={22}/></button></MobileHeader>
 <main className="detail-main"><div className="detail-left">
 <section className="detail-player">
  <video key={selectedClip?.id || id} ref={register} src={source || undefined} poster={selectedClip?.thumbnail_url || data?.thumbnail_url || undefined} playsInline preload="metadata" onTimeUpdate={e => onTime(e.currentTarget)} onPlay={() => store.setPlaying(true)} onPause={() => store.setPlaying(false)} onError={() => setMediaError(true)} onLoadedMetadata={e => { e.currentTarget.playbackRate=rate;store.setDuration(data?.duration_seconds || end); const time = pendingSeek.current ?? validTime; if (time >= offset && time < end)
        e.currentTarget.currentTime = time - offset; pendingSeek.current = null; }}/>
  <span className="player-tag mobile-only">AI Augmented</span>
  {(clip.isPending && selectedClip || clip.error || !source || mediaError) && <div className="player-unavailable" role={clip.error || mediaError ? "alert" : "status"}><Icon name="smart_display" size={36}/>{clip.isPending && selectedClip ? "Đang tải clip…" : clip.error ? errorMessage(clip.error) : !selectedClip ? "Nguồn phát video chưa khả dụng." : "Không thể phát clip."}{clip.error && <button className="btn-outline" onClick={() => clip.refetch()}>Thử lại</button>}</div>}
  {source && !mediaError && <><div className="detail-center-controls"><button aria-label="Lùi 10 giây" onClick={() => store.seekTo(Math.max(offset, store.currentTime - 10))}><Icon name="replay_10" size={32}/></button><button aria-label={store.isPlaying ? "Tạm dừng" : "Phát video"} onClick={store.togglePlay}><Icon name={store.isPlaying ? "pause" : "play_arrow"} size={36}/></button><button aria-label="Toàn màn hình" onClick={() => void ref.current?.requestFullscreen()}><Icon name="fullscreen" size={28}/></button></div>
   {currentSegment?.text && <div className="subtitle-overlay">{currentSegment.text}</div>}
  </>}
  <div className="player-bottom">
   <div className="heatmap" aria-label="Heatmap điểm highlight">{scores.map((s, i) => <button key={i} aria-label={`Đến ${formatTime(s.second)}, điểm ${Math.round(s.score || 0)}`} title={`${formatTime(s.second)} · Cường độ: ${Math.round(s.score || 0)}/100`} onClick={() => seek(s.second || 0)} style={{ height: `${Math.max(8, s.score || 0)}%`, background: (s.score || 0) > 75 ? "#c6252b" : (s.score || 0) >= 40 ? "#fea619" : "#630ed4" }}/>)}{!!scores.length && <i className="heatmap-cursor" style={{ left: `${Math.min(100, store.currentTime / (data?.duration_seconds || 1) * 100)}%` }}/>}</div>
   <input aria-label="Vị trí phát video" className="detail-seek" type="range" min={offset} max={end || 1} step={.1} value={Math.min(end || 1, Math.max(offset, store.currentTime))} disabled={!source} onChange={e => store.seekTo(Number(e.target.value))}/>
   <div className="player-toolbar"><div className="desktop-player-controls"><button className="icon-button" aria-label="Lùi 10 giây" onClick={() => store.seekTo(Math.max(offset, store.currentTime - 10))}><Icon name="skip_previous" size={20}/></button><button className="icon-button" aria-label={store.isPlaying ? "Tạm dừng" : "Phát video"} onClick={store.togglePlay}><Icon name={store.isPlaying ? "pause" : "play_arrow"} size={20}/></button><button className="icon-button" aria-label="Tiến 10 giây" onClick={() => store.seekTo(Math.min(end, store.currentTime + 10))}><Icon name="skip_next" size={20}/></button></div><time>{formatTime(store.currentTime)}<span className="desktop-only"> / {formatTime(data?.duration_seconds)}</span></time><time className="player-end-time">{formatTime(data?.duration_seconds)}</time><button className="auto-highlight desktop-only" aria-pressed={store.autoHighlight} onClick={auto} disabled={!source || !ranges.length}><Icon name="auto_awesome" size={16}/>Tự động phát Highlight</button><details className="player-settings desktop-only"><summary className="icon-button" aria-label="Cài đặt trình phát"><Icon name="settings"/></summary><div><label htmlFor="playback-rate">Tốc độ phát</label><select id="playback-rate" value={rate} onChange={e=>{const value=Number(e.target.value);setRate(value);if(ref.current)ref.current.playbackRate=value;}}>{[.5,.75,1,1.25,1.5,2].map(value=><option key={value} value={value}>{value}×</option>)}</select></div></details><button className="icon-button desktop-only" onClick={() => void ref.current?.requestFullscreen()} aria-label="Toàn màn hình"><Icon name="fullscreen"/></button></div>
  </div>
 </section>
 {!original && <div className="notice detail-error">Đang xem clip đã xuất bản{selectedClip ? ` (${formatTime(offset)}–${formatTime(end)})` : ""}. Video gốc chưa có nguồn phát.</div>}
 <section className="detail-metadata"><h1>{data?.title}</h1><div className="video-metadata-line"><span>{formatDate(data?.created_at)}</span><span>{formatTime(data?.duration_seconds)}</span>{data?.category?.name && <span className="category">#{data.category.name}</span>}</div>
 <div className="detail-channel"><span className="avatar"><Icon name="movie_filter" size={22}/></span><div><p>VidsAI</p><small>Video đã xử lý</small></div></div>
 <div className="detail-quick-actions hide-scrollbar"><button aria-pressed={liked} className={liked ? "active" : ""} onClick={() => action("like")}><Icon name="thumb_up" size={20}/>{liked ? "Đã thích" : "Thích"}</button><button className={`mobile-action ${saved ? "active" : ""}`} aria-pressed={saved} onClick={() => action("save")}><Icon name="bookmark" size={20} filled={saved}/>Lưu lại</button><button className="mobile-action" onClick={() => { setSummaryOpen(true); document.getElementById("ai-summary")?.scrollIntoView({ behavior: "smooth" }); }} disabled={!analysis.data?.summary}><Icon name="auto_awesome" size={20}/>Tóm tắt AI</button><button className="mobile-action" onClick={() => setSheet(true)}><Icon name="description" size={20}/>Bản ghi</button><button className="desktop-only" onClick={share}><Icon name="share" size={20}/>Chia sẻ</button></div></section>
 {analysis.isPending ? <PageState loading/> : analysis.error ? <div className="detail-error"><PageState error={analysis.error} retry={() => analysis.refetch()}/></div> : analysis.data?.summary && <section className="summary-section" id="ai-summary"><button className="summary-heading" onClick={() => setSummaryOpen(!summaryOpen)} aria-expanded={summaryOpen}><span className="mobile-only"><Icon name="auto_awesome" filled/></span><span className="desktop-only"><Icon name="bolt"/></span><h2><span className="mobile-only">Tóm tắt Thông minh bởi AI</span><span className="desktop-only">Tóm tắt nội dung bằng AI</span></h2><Icon name="expand_more" size={18}/></button>{summaryOpen && <><p className="summary-content">{analysis.data.summary}</p>{!!analysis.data.key_moments?.length && <div className="moment-grid">{analysis.data.key_moments.map((moment, i) => <button key={i} onClick={() => seek(moment.timestamp || 0)}><small><span className="mobile-only">{i === 0 ? "Điểm Nhấn" : i === 1 ? "Kết Luận" : "Điểm Nhấn"}</span><time className="desktop-only">{formatTime(moment.timestamp)}</time></small><span>{moment.text} <time className="mobile-only">({formatTime(moment.timestamp)})</time></span></button>)}</div>}{!!analysis.data.hashtags?.length && <div className="summary-hashtags">{analysis.data.hashtags.map(h => <span key={h}>{h.startsWith("#") ? h : `#${h}`}</span>)}</div>}</>}</section>}
 <section className="related-section"><h2><span className="mobile-only">Đề xuất cho bạn</span><span className="desktop-only">Video liên quan</span></h2><div className="related-list">{clips.map(c => <button className="related-card" key={c.id} onClick={() => { pendingSeek.current = c.start_time || 0; setSelected(c.id || null); store.seekTo(c.start_time || 0); }}><div className="media-frame"><Thumbnail src={c.thumbnail_url}/><time className="time-badge">{formatTime((c.end_time || 0) - (c.start_time || 0))}</time></div><div><h3 className="line-clamp-2">{c.title}</h3><small>VidsAI · AI Highlight</small></div></button>)}</div>{!clips.length && <PageState empty="Chưa có clip highlight cho video này."/>}</section>
 </div><aside className="transcript-desktop"><Transcript {...transcriptProps}/></aside></main>
 <dialog ref={dialog} className="transcript-dialog" onCancel={() => setSheet(false)} onClose={() => setSheet(false)} onClick={e => { if (e.target === e.currentTarget)
        setSheet(false); }}>{sheet && <Transcript {...transcriptProps} close={() => setSheet(false)}/>}</dialog>
 <BottomNav active="library"/>{message && <div className="feed-toast" role="status">{message}</div>}</div>;
}
export default function VideoDetailPage() { return <Suspense fallback={<PageState loading/>}><VideoDetail /></Suspense>; }

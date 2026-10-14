import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useCmsVideo, useCmsAnalysis, useCreateClip, usePublishClip, useSettings, useClips } from "../hooks/useCms";
import { VideoPlayer, PlayerHandle } from "../components/player/VideoPlayer";
import { HeatmapTimeline } from "../components/heatmap/HeatmapTimeline";
import { VideoPicker } from "../components/common/Media";
import { Icon } from "../components/common/Icon";
import { Empty, ErrorState, Skeleton } from "../components/common/Skeleton";
import { StatusBadge } from "../components/common/StatusBadge";
import { useReviewStore } from "../stores/reviewStore";
import { useAuthStore } from "../stores/authStore";
import { useToast } from "../components/common/Toast";
import { errorMessage } from "../lib/apiClient";
import { fmtSec } from "../lib/time";

export default function HighlightPage() {
  const [params] = useSearchParams();
  const videoId = params.get("video_id") ?? "";
  const video = useCmsVideo(videoId);
  const analysis = useCmsAnalysis(videoId);
  const create = useCreateClip();
  const publish = usePublishClip();
  const clips = useClips({ video_id: videoId || undefined });
  const settings = useSettings(useAuthStore((state) => state.user?.role) === "admin");
  const review = useReviewStore();
  const toast = useToast();
  const player = useRef<PlayerHandle>(null);
  const [clipId, setClipId] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState<number[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [sortByScore, setSortByScore] = useState(true);
  const [zoom, setZoom] = useState(1);
  const duration = video.data?.duration_seconds ?? 0;
  const threshold = settings.data?.highlight_threshold ?? 75;
  const currentClip = clips.data?.find((clip) => clip.id === clipId);
  const scores = (analysis.data?.timeline_scores ?? []).map((score) => ({ second: score.second ?? 0, score: score.score ?? 0 }));
  useEffect(() => { review.loadClip({ start: 0, end: Math.min(duration, 10) }); review.setCurrentTime(0); setClipId(null); setDismissed([]); setSelected(null); }, [videoId, duration]);
  const proposals = (analysis.data?.ai_generated_clips ?? []).map((clip, index) => ({ clip, index })).filter(({ index }) => !dismissed.includes(index)).sort((a, b) => sortByScore ? (b.clip.average_score ?? 0) - (a.clip.average_score ?? 0) : (a.clip.start_time ?? 0) - (b.clip.start_time ?? 0));
  const valid = !!videoId && video.data?.status === "processed" && review.editing.start >= 0 && review.editing.end > review.editing.start && review.editing.end <= duration;
  const save = async () => {
    try { const clip = await create.mutateAsync({ video_id: videoId, title: review.editing.title.trim() || `Highlight — ${video.data?.title ?? "Video"}`, start_time: review.editing.start, end_time: review.editing.end }); setClipId(clip.id ?? null); toast.ok("Đã tạo bản nháp — đang cắt clip"); } catch (error) { toast.err(errorMessage(error)); }
  };
  const seek = (time: number) => { review.setCurrentTime(time); player.current?.seekTo(time); };
  return <div className="highlight-page">
    <div className="page-header"><div><nav className="breadcrumb"><Link to="/videos">Dự án</Link><Icon name="chevron_right" size={16} /><span>{video.data?.category?.name ?? "Video"}</span><Icon name="chevron_right" size={16} /><span>Cắt Highlight AI</span></nav><h2>{video.data?.title ?? "Phê duyệt & Cắt Highlight AI"}</h2></div><div className="page-actions"><button className="btn-secondary" disabled={!valid || create.isPending} onClick={save}><Icon name="save" size={20} />{create.isPending ? "Đang tạo clip…" : "Lưu bản nháp"}</button><button className="btn-primary" disabled={!currentClip || currentClip.status !== "draft" || publish.isPending} onClick={() => clipId && publish.mutate(clipId, { onSuccess: () => toast.ok("Đã xuất bản clip"), onError: (error) => toast.err(errorMessage(error)) })}><Icon name="rocket_launch" size={20} />Xuất bản clip</button></div></div>
    {!videoId && <VideoPicker />}
    {videoId && (video.isError || analysis.isError) && <ErrorState msg={errorMessage(video.error ?? analysis.error)} onRetry={() => { video.refetch(); analysis.refetch(); }} />}
    <div className="highlight-grid"><div className="highlight-left">
      <div className="card highlight-player">{video.isLoading && videoId ? <Skeleton h={320} /> : <VideoPlayer ref={player} poster={video.data?.thumbnail_url} onTimeUpdate={review.setCurrentTime} />}<div className="player-time mono"><span>{fmtSec(review.currentTime)}</span><div className="progress-track"><span style={{ width: `${duration ? review.currentTime / duration * 100 : 0}%` }} /></div><span>{fmtSec(duration)}</span></div></div>
      <div className="card heatmap-panel"><div className="heatmap-heading"><h4><Icon name="analytics" size={20} />Cường độ trận đấu (AI Insights)</h4><span className="badge ai-badge"><span className="peak-dot" />Peaks &gt; {threshold}% Score</span><div className="row-actions"><button className="icon-button" aria-label="Thu nhỏ timeline" disabled={zoom <= 1} onClick={() => setZoom((value) => Math.max(1, value - 1))}><Icon name="zoom_out" size={20} /></button><span className="badge ai-badge">Zoom: {zoom * 100}%</span><button className="icon-button" aria-label="Phóng to timeline" disabled={zoom >= 4 || !duration} onClick={() => setZoom((value) => value + 1)}><Icon name="zoom_in" size={20} /></button></div></div>
        <HeatmapTimeline scores={scores} duration={duration} currentTime={review.currentTime} onSeek={seek} threshold={threshold} selection={review.editing} onSelectionChange={({ start, end }) => { setClipId(null); review.loadClip({ start, end, title: review.editing.title }); }} zoom={zoom} />
      </div>
      <div className="card clip-edit-form"><label>Bắt đầu (giây)<input className="input" aria-label="Bắt đầu clip" type="number" min={0} max={duration} step={.1} value={review.editing.start} onChange={(e) => { setClipId(null); review.setStart(Number(e.target.value)); }} /></label><label>Kết thúc (giây)<input className="input" aria-label="Kết thúc clip" type="number" min={0} max={duration} step={.1} value={review.editing.end} onChange={(e) => { setClipId(null); review.setEnd(Number(e.target.value)); }} /></label><label className="clip-title">Tiêu đề clip<input className="input" placeholder="Tiêu đề" value={review.editing.title} onChange={(e) => { setClipId(null); review.setTitle(e.target.value); }} /></label>{duration > 0 && !valid && <p role="alert" className="error-text">Khoảng cắt phải nằm trong video và thời điểm kết thúc lớn hơn bắt đầu.</p>}{currentClip && <div className="clip-status"><StatusBadge status={currentClip.status ?? "processing"} />{currentClip.status === "processing" && <span className="micro">Đang cắt, tự cập nhật mỗi 3 giây</span>}<Link className="btn-text" to="/published">Mở thư viện</Link></div>}</div>
    </div><section className="card proposal-panel"><div className="panel-heading"><h4><Icon name="magic_button" size={20} />Đề xuất Highlights AI ({proposals.length})</h4><button className="btn-text micro" onClick={() => setSortByScore((value) => !value)}>Sắp xếp theo: {sortByScore ? "Score" : "Thời gian"}</button></div><div className="proposals">
      {videoId && analysis.isLoading ? <Skeleton h={180} /> : !videoId ? <Empty msg="Chọn video đã xử lý để xem gợi ý AI." /> : !proposals.length && <Empty msg="Chưa có gợi ý vượt ngưỡng. Bạn có thể chọn khoảng cắt thủ công." />}
      {proposals.map(({ clip, index }) => <article key={index} className={`proposal-card ${selected === index ? "is-selected" : ""}`}><div className="proposal-meta"><span className="badge ai-badge">#{String(index + 1).padStart(2, "0")}</span><span className={`badge ${(clip.average_score ?? 0) > 90 ? "match-badge" : (clip.average_score ?? 0) >= 80 ? "match-medium" : "match-low"}`}><Icon name={(clip.average_score ?? 0) > 90 ? "star" : "analytics"} size={14} />{clip.average_score?.toFixed(0) ?? 0}% Match</span><span className="mono">{fmtSec(clip.start_time ?? 0)}–{fmtSec(clip.end_time ?? 0)}</span></div><h4>{clip.reason ?? `Highlight #${index + 1}`}</h4><p>{analysis.data?.key_moments?.find((moment) => (moment.timestamp ?? -1) >= (clip.start_time ?? 0) && (moment.timestamp ?? -1) <= (clip.end_time ?? 0))?.text ?? "—"}</p><div className="proposal-actions"><button className={selected === index ? "btn-primary" : "btn-secondary"} onClick={() => { review.loadClip({ start: clip.start_time ?? 0, end: clip.end_time ?? 0, title: clip.reason ?? `Highlight #${index + 1}` }); setSelected(index); setClipId(null); seek(clip.start_time ?? 0); }}>Chấp nhận</button><button className="btn-secondary" disabled title="Nguồn phát video gốc chưa có">Xem trước</button><button className="icon-button danger" aria-label={`Bỏ gợi ý ${index + 1}`} onClick={() => setDismissed((values) => [...values, index])}><Icon name="close" size={20} /></button></div></article>)}
    </div></section></div>
  </div>;
}

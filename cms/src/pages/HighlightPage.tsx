import { useQueryClient } from "@tanstack/react-query";
import type { components } from "../api-types";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useCmsVideo, useCmsAnalysis, useCreateClip, usePublishClip, useClips } from "../hooks/useCms";
import { VideoPlayer, PlayerHandle } from "../components/player/VideoPlayer";
import { HeatmapTimeline } from "../components/heatmap/HeatmapTimeline";
import { VideoPicker } from "../components/common/Media";
import { Icon } from "../components/common/Icon";
import { Empty, ErrorState, Skeleton } from "../components/common/Skeleton";
import { StatusBadge } from "../components/common/StatusBadge";
import { useReviewStore } from "../stores/reviewStore";
import { useToast } from "../components/common/Toast";
import { apiClient, errorMessage } from "../lib/apiClient";
import { fmtSec } from "../lib/time";

export default function HighlightPage() {
  const [params] = useSearchParams();
  const videoId = params.get("video_id") ?? "";
  const video = useCmsVideo(videoId);
  const analysis = useCmsAnalysis(videoId);
  const create = useCreateClip();
  const publish = usePublishClip();
  const clips = useClips({ video_id: videoId || undefined }, !!videoId);
  const review = useReviewStore();
  const toast = useToast();
  const player = useRef<PlayerHandle>(null);
  const [clipId, setClipId] = useState<string | null>(null);
const qc = useQueryClient();
 const [reviewing, setReviewing] = useState(false);
 const decisions=analysis.data?.proposal_decisions ?? [];
 const dismissed=decisions.filter(d=>d.status === "dismissed").map(d=>d.proposal_index);
 const decide=async (index: number, status: "accepted" | "dismissed") => {
  setReviewing(true);
  try {const {data}=await apiClient.put<components["schemas"]["CmsAnalysis"]>(`/api/cms/videos/${videoId}/analysis`,{proposal_decisions:[...decisions.filter(d=>d.proposal_index!==index),{proposal_index:index,status}]});qc.setQueryData(["analysis",videoId],data);return true;}catch(error){toast.err(errorMessage(error));return false;}finally{setReviewing(false);}
 };
 const restore=async()=>{setReviewing(true);try {const {data}=await apiClient.put<components["schemas"]["CmsAnalysis"]>(`/api/cms/videos/${videoId}/analysis`,{proposal_decisions:decisions.filter(d=>d.status!=="dismissed")});qc.setQueryData(["analysis",videoId],data);}catch(error){toast.err(errorMessage(error));}finally{setReviewing(false);}};
  const [selected, setSelected] = useState<number | null>(null);
  const [sortByScore, setSortByScore] = useState(true);
  const [zoom, setZoom] = useState(1);
  const duration = video.data?.duration_seconds ?? 0;
  const reportedThreshold = analysis.data?.clip_threshold;
  const threshold = reportedThreshold ?? 75;
  const isFootball = analysis.data?.category_suggestion === "bong_da";
  const referenceOnly = !isFootball || duration < 120;
  const currentClip = clips.data?.find((clip) => clip.id === clipId);
  const compilations = (clips.data ?? []).filter((clip) => !!clip.source_segments?.length);
  const compilation = currentClip?.source_segments?.length ? currentClip : undefined;
  const scores = (analysis.data?.timeline_scores ?? []).map((score) => ({ second: score.second ?? 0, score: score.score ?? 0 }));
  useEffect(() => { review.loadClip({ start: 0, end: Math.min(duration, 10) }); review.setCurrentTime(0); setClipId(null); setSelected(null); }, [videoId, duration]);
  const proposals = (analysis.data?.ai_generated_clips ?? []).map((clip, index) => ({ clip, index })).filter(({ index }) => !dismissed.includes(index)).sort((a, b) => sortByScore ? (b.clip.average_score ?? 0) - (a.clip.average_score ?? 0) : (a.clip.start_time ?? 0) - (b.clip.start_time ?? 0));
  const valid = !!videoId && video.data?.status === "processed" && review.editing.start >= 0 && review.editing.end > review.editing.start && review.editing.end <= duration;
  const save = async () => {
    try { const clip = await create.mutateAsync({ video_id: videoId, title: review.editing.title.trim() || `Highlight — ${video.data?.title ?? "Video"}`, start_time: review.editing.start, end_time: review.editing.end }); setClipId(clip.id ?? null); toast.ok("Đã tạo bản nháp — đang cắt clip"); } catch (error) { toast.err(errorMessage(error)); }
  };
  const compile = async () => {
    try { const clip = await create.mutateAsync({ video_id: videoId, title: `Tổng hợp — ${video.data?.title ?? "Video"}`, auto_highlights: true }); setClipId(clip.id ?? null); toast.ok("Đang ghép các tình huống nổi bật thành một video nháp"); } catch (error) { toast.err(errorMessage(error)); }
  };
  const seek = (time: number) => { review.setCurrentTime(time); player.current?.seekTo(time); };
  return <div className="highlight-page">
    <div className="page-header"><div><nav className="breadcrumb"><Link to="/videos">Dự án</Link><Icon name="chevron_right" size={12} /><span>{video.data?.category?.name ?? "Video"}</span><Icon name="chevron_right" size={12} /><span>Cắt Highlight AI</span></nav><h2>{video.data?.title ?? "Phê duyệt & Cắt Highlight AI"}</h2></div><div className="page-actions"><button className="btn-secondary" disabled={!videoId || video.data?.status !== "processed" || !proposals.length || create.isPending || reviewing} onClick={compile}><Icon name="auto_awesome" size={24} />Tạo video tổng hợp AI</button><button className="btn-secondary" disabled={!valid || create.isPending} onClick={save}><Icon name="save" size={24} />{create.isPending ? "Đang tạo clip…" : "Lưu bản nháp"}</button><button className="btn-primary" disabled={!currentClip || currentClip.status !== "draft" || publish.isPending} onClick={() => clipId && publish.mutate(clipId, { onSuccess: () => toast.ok("Đã xuất bản clip"), onError: (error) => toast.err(errorMessage(error)) })}><Icon name="rocket_launch" size={24} />Xuất bản clip</button></div></div>
    {!videoId && <VideoPicker />}
    {videoId && (video.isError || analysis.isError) && <ErrorState msg={errorMessage(video.error ?? analysis.error)} onRetry={() => { video.refetch(); analysis.refetch(); }} />}
    <div className="highlight-grid"><div className="highlight-left">
      <div className="card highlight-player">{video.isLoading && videoId ? <Skeleton h={320} /> : <VideoPlayer variant="highlight" ref={player} src={video.data?.playback_url} poster={video.data?.thumbnail_url} onTimeUpdate={review.setCurrentTime} />}<div className="player-time mono"><span>{fmtSec(review.currentTime, true)}</span><div className="progress-track"><span style={{ width: `${duration ? review.currentTime / duration * 100 : 0}%` }} /></div><span>{fmtSec(duration, true)}</span></div></div>
      <div className="card heatmap-panel"><div className="heatmap-heading"><h4><Icon name="analytics" size={24} />{isFootball ? "Cường độ trận đấu (AI Insights)" : "Điểm highlight AI"}</h4><span className="plain-badge"><span className="peak-dot" />{reportedThreshold == null ? "Ngưỡng hiển thị" : "Ngưỡng AI"} &gt; {threshold}%</span><div className="row-actions"><button className="icon-button" aria-label="Thu nhỏ timeline" disabled={zoom <= 1} onClick={() => setZoom((value) => Math.max(1, value - 1))}><Icon name="zoom_out" size={24} /></button><span className="plain-badge zoom-badge">Zoom: {zoom * 100}%</span><button className="icon-button" aria-label="Phóng to timeline" disabled={zoom >= 4 || !duration} onClick={() => setZoom((value) => value + 1)}><Icon name="zoom_in" size={24} /></button></div></div>
        {videoId && analysis.data && reportedThreshold == null && <p className="micro" role="note">Kết quả cũ chưa ghi ngưỡng AI; ngưỡng hiển thị 75% không xác nhận cách AI đã chọn clip.</p>}
        {videoId && analysis.data && referenceOnly && <p className="micro" role="note">Điểm AI chỉ để tham khảo — model highlight huấn luyện trên bóng đá.{duration < 120 ? " Video dưới 2 phút nằm ngoài phạm vi đánh giá của model." : ""}</p>}
        <HeatmapTimeline scores={scores} duration={duration} currentTime={review.currentTime} onSeek={seek} threshold={threshold} selection={review.editing} onSelectionChange={({ start, end }) => { setClipId(null); review.loadClip({ start, end, title: review.editing.title }); }} zoom={zoom} />
      </div>
      <div className="card clip-edit-form"><label>Bắt đầu (giây)<input className="input" aria-label="Bắt đầu clip" type="number" min={0} max={duration} step={.1} value={review.editing.start} onChange={(e) => { setClipId(null); review.setStart(Number(e.target.value)); }} /></label><label>Kết thúc (giây)<input className="input" aria-label="Kết thúc clip" type="number" min={0} max={duration} step={.1} value={review.editing.end} onChange={(e) => { setClipId(null); review.setEnd(Number(e.target.value)); }} /></label><label className="clip-title">Tiêu đề clip<input className="input" placeholder="Tiêu đề" value={review.editing.title} onChange={(e) => { setClipId(null); review.setTitle(e.target.value); }} /></label>{duration > 0 && !valid && <p role="alert" className="error-text">Khoảng cắt phải nằm trong video và thời điểm kết thúc lớn hơn bắt đầu.</p>}{currentClip && <div className="clip-status"><StatusBadge status={currentClip.status ?? "processing"} />{currentClip.status === "processing" && <span className="micro">Đang cắt, tự cập nhật mỗi 3 giây</span>}<Link className="btn-text" to="/published">Mở thư viện</Link></div>}</div>
      {!!compilations.length && <section className="card compilation-preview" aria-label="Video highlight tổng hợp">
        <h4>Video tổng hợp AI</h4><select className="input" aria-label="Chọn video tổng hợp" value={compilation?.id ?? ""} onChange={(e) => setClipId(e.target.value)}><option value="" disabled>Chọn bản tổng hợp đã tạo</option>{compilations.map((clip) => <option key={clip.id} value={clip.id}>{clip.title} · {clip.status}</option>)}</select>
        {compilation && <><p>{compilation.source_segments?.length} đoạn · {fmtSec(compilation.end_time ?? 0)} · Giữ thứ tự diễn biến và âm thanh gốc</p><StatusBadge status={compilation.status ?? "processing"} />{compilation.status === "draft" && <p>Bản nháp AI cần xem và kiểm tra trước khi xuất bản.</p>}{compilation.playback_url ? <video controls playsInline preload="metadata" src={compilation.playback_url} poster={compilation.thumbnail_url ?? undefined} aria-label="Xem trước video tổng hợp" /> : <p role="status">{compilation.status === "rejected" ? "Ghép video thất bại. Hãy thử tạo lại." : "Đang ghép video…"}</p>}<p className="micro">Các đoạn nguồn: {compilation.source_segments?.map((segment) => `${fmtSec(segment.start_time)}–${fmtSec(segment.end_time)}`).join(", ")}</p></>}
      </section>}
    </div><section className="card proposal-panel"><div className="panel-heading"><h4><Icon name="magic_button" size={24} />Đề xuất Highlights AI ({proposals.length})</h4><button className="btn-text micro" onClick={() => setSortByScore((value) => !value)}>Sắp xếp theo: {sortByScore ? "Score" : "Thời gian"}</button></div><div className="proposals">{dismissed.length > 0 && <button className="btn-text" disabled={reviewing} onClick={restore}>Khôi phục gợi ý đã bỏ ({dismissed.length})</button>}
      {videoId && analysis.isLoading ? <Skeleton h={180} /> : !videoId ? <Empty msg="Chọn video đã xử lý để xem gợi ý AI." /> : !proposals.length && !analysis.isError && <Empty msg={analysis.data?.ai_generated_clips?.length ? "Bạn đã ẩn tất cả gợi ý. Vẫn có thể chọn khoảng cắt thủ công." : "AI không đề xuất clip cho video này — bạn có thể chọn khoảng cắt thủ công."} />}
      {proposals.map(({ clip, index }) => <article key={index} className={`proposal-card ${selected === index ? "is-selected" : ""}`}><div className="proposal-meta"><span className="proposal-index">#{String(index + 1).padStart(2, "0")}</span><span className={`badge ${(clip.average_score ?? 0) > 90 ? "match-badge" : (clip.average_score ?? 0) >= 80 ? "match-medium" : "match-low"}`}><Icon name={(clip.average_score ?? 0) > 90 ? "star" : "analytics"} size={12} filled={(clip.average_score ?? 0) > 90} />{clip.average_score?.toFixed(0) ?? 0}% Match</span><span className="proposal-time">{fmtSec(clip.start_time ?? 0, true)} - {fmtSec(clip.end_time ?? 0, true)}</span></div><h4>{clip.reason ?? `Highlight #${index + 1}`}</h4><p>{analysis.data?.key_moments?.find((moment) => (moment.timestamp ?? -1) >= (clip.start_time ?? 0) && (moment.timestamp ?? -1) <= (clip.end_time ?? 0))?.text ?? "—"}</p><div className="proposal-actions"><button className={selected === index || decisions.some(d=>d.proposal_index===index && d.status==="accepted") ? "btn-primary" : "btn-secondary"} disabled={reviewing || video.data?.status !== "processed"} onClick={async () => { if (!await decide(index,"accepted")) return; review.loadClip({ start: clip.start_time ?? 0, end: clip.end_time ?? 0, title: clip.reason ?? `Highlight #${index + 1}` }); setSelected(index); setClipId(null); seek(clip.start_time ?? 0); }}>{decisions.some(d=>d.proposal_index===index && d.status==="accepted") ? "Đã chấp nhận" : "Chấp nhận"}</button><button className="btn-secondary" disabled={!video.data?.playback_url} title={video.data?.playback_url ? undefined : "Nguồn phát video gốc chưa có"} onClick={() => player.current?.preview(clip.start_time ?? 0, clip.end_time ?? 0)}>Xem trước</button><button className={`icon-button ${selected === index ? "danger" : "proposal-dismiss"}`} aria-label={`Bỏ gợi ý ${index + 1}`} disabled={reviewing || video.data?.status !== "processed"} onClick={() => decide(index,"dismissed")}><Icon name="close" size={20} /></button></div></article>)}
    </div></section></div>
  </div>;
}

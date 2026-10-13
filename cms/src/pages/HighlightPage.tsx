import { useRef, useState } from "react";
import { useCmsVideo, useCmsAnalysis, useCreateClip, usePublishClip, useSettings } from "../hooks/useCms";
import { VideoPlayer, PlayerHandle } from "../components/player/VideoPlayer";
import { HeatmapTimeline } from "../components/heatmap/HeatmapTimeline";
import { useReviewStore } from "../stores/reviewStore";
import { useToast } from "../components/common/Toast";

export default function HighlightPage() {
  const [videoId, setVideoId] = useState("vid_stub01");
  const video = useCmsVideo(videoId);
  const analysis = useCmsAnalysis(videoId);
  const createClip = useCreateClip();
  const publishClip = usePublishClip();
  const review = useReviewStore();
  const toast = useToast();
  const settings = useSettings();
  const threshold = settings.data?.highlight_threshold ?? 75;
  const playerRef = useRef<PlayerHandle>(null);
  const scores: { second: number; score: number }[] = analysis.data?.timeline_scores ?? [];
  const aiClips: any[] = analysis.data?.ai_generated_clips ?? [];
  const duration: number = video.data?.duration_seconds ?? 600;
  const [clipId, setClipId] = useState<string | null>(null);

  return (
    <div>
      <h2>Highlight AI</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <input className="input" value={videoId} onChange={(e) => setVideoId(e.target.value)} placeholder="video_id" style={{ width: 280 }} />
        <button className="btn-primary" onClick={() => { video.refetch(); analysis.refetch(); }}>Tải</button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 16 }}>
        <div>
          <VideoPlayer ref={playerRef} src={video.data?.raw_file_path ?? ""} onTimeUpdate={(t) => review.setCurrentTime(t)} />
          <div style={{ marginTop: 12 }}>
            <HeatmapTimeline scores={scores} duration={duration} currentTime={review.currentTime} onSeek={(s) => playerRef.current?.seekTo(s)} threshold={threshold} />
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>Ngưỡng highlight: {threshold} — vùng đỏ = &gt;{threshold}</div>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 12, alignItems: "center" }}>
            <label>Start <input className="input" type="number" value={review.editing.start} onChange={(e) => review.setStart(Number(e.target.value))} style={{ width: 90 }} /></label>
            <label>End <input className="input" type="number" value={review.editing.end} onChange={(e) => review.setEnd(Number(e.target.value))} style={{ width: 90 }} /></label>
            <input className="input" placeholder="Tiêu đề" value={review.editing.title} onChange={(e) => review.setTitle(e.target.value)} style={{ flex: 1 }} />
            <button className="btn-primary" onClick={async () => {
              try { const r: any = await createClip.mutateAsync({ video_id: videoId, title: review.editing.title || "Highlight", start_time: review.editing.start, end_time: review.editing.end }); setClipId(r.id ?? r.clip?.id ?? null); toast.ok("Đã tạo clip — đang cắt"); }
              catch (e: any) { toast.err(e?.apiError?.message ?? e.message); }
            }}>Export Clip</button>
            {clipId && <button className="btn-primary" onClick={() => publishClip.mutate(clipId, { onSuccess: () => toast.ok("Đã xuất bản"), onError: (e: any) => toast.err(e?.apiError?.message ?? e.message) })}>Publish</button>}
          </div>
        </div>
        <div className="card" style={{ padding: 12, height: "fit-content" }}>
          <h4>AI Clips</h4>
          {aiClips.length === 0 && <div style={{ color: "var(--text-muted)", fontSize: 13 }}>Chưa có gợi ý</div>}
          {aiClips.map((c: any, i: number) => (
            <div key={i} style={{ padding: "8px 0", borderBottom: "1px solid var(--border)", fontSize: 13 }}>
              <div>#{i + 1} {c.start_time?.toFixed(1)}–{c.end_time?.toFixed(1)} — avg {c.average_score?.toFixed?.(0) ?? c.average_score}%</div>
              <div style={{ color: "var(--text-secondary)", fontSize: 12 }}>{c.reason ?? ""}</div>
              <button onClick={() => { review.loadClip({ start: c.start_time, end: c.end_time }); playerRef.current?.seekTo(c.start_time); }} style={{ fontSize: 12, color: "var(--primary)" }}>▶ Preview</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

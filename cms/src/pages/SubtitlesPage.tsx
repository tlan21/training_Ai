import { useEffect, useRef, useState } from "react";
import { useSubtitles, useCmsAnalysis } from "../hooks/useCms";
import { apiClient } from "../lib/apiClient";
import { VideoPlayer, PlayerHandle } from "../components/player/VideoPlayer";
import { useCmsVideo } from "../hooks/useCms";

export default function SubtitlesPage() {
  const [videoId, setVideoId] = useState("vid_stub01");
  const video = useCmsVideo(videoId);
  const subs = useSubtitles(videoId);
  const analysis = useCmsAnalysis(videoId);
  const [segments, setSegments] = useState<any[]>([]);
  const [dirty, setDirty] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const playerRef = useRef<PlayerHandle>(null);
  const rowRefs = useRef<Record<number, HTMLDivElement | null>>({});

  useEffect(() => { if (subs.data?.segments) setSegments(subs.data.segments); }, [subs.data]);
  const activeIdx = segments.findIndex((s) => currentTime >= s.start_time && currentTime <= s.end_time);
  useEffect(() => { if (activeIdx >= 0) rowRefs.current[activeIdx]?.scrollIntoView({ block: "center", behavior: "smooth" }); }, [activeIdx]);

  const save = async () => {
    await apiClient.put(`/api/cms/videos/${videoId}/subtitles`, { segments });
    setDirty(false);
  };
  const regenerate = async () => {
    const r = await apiClient.post(`/api/cms/videos/${videoId}/summary/regenerate`);
    alert(`Tiêu đề mới: ${r.data.suggested_title}\nTóm tắt: ${r.data.summary?.slice(0, 200)}`);
  };

  return (
    <div>
      <h2>Phụ đề & Tóm tắt AI</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <input className="input" value={videoId} onChange={(e) => setVideoId(e.target.value)} style={{ width: 280 }} />
        <button className="btn-primary" onClick={() => { video.refetch(); subs.refetch(); analysis.refetch(); }}>Tải</button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr 340px", gap: 16 }}>
        <div>
          <VideoPlayer ref={playerRef} src={video.data?.raw_file_path ?? ""} onTimeUpdate={setCurrentTime} />
          <div style={{ marginTop: 8, fontSize: 12, color: "var(--text-secondary)" }}>Duration: {video.data?.duration_seconds ?? "—"}s</div>
        </div>
        <div className="card" style={{ padding: 12, maxHeight: 520, overflow: "auto" }}>
          <h4>Transcript — {segments.length} segments {dirty && "(dirty)"}</h4>
          {segments.map((s, i) => (
            <div key={i} ref={(el) => { rowRefs.current[i] = el; }} onClick={() => playerRef.current?.seekTo(s.start_time)} style={{ padding: 8, borderRadius: 6, background: i === activeIdx ? "var(--bg-surface-2)" : undefined, border: i === activeIdx ? "1px solid var(--primary)" : "1px solid transparent", marginBottom: 6, cursor: "pointer" }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "JetBrains Mono" }}>
                [{s.start_time?.toFixed?.(1) ?? s.start_time}–{s.end_time?.toFixed?.(1) ?? s.end_time}] — {(s.confidence * 100).toFixed(0)}% {s.warning && <span style={{ color: "var(--danger)" }}>⚠ {s.warning}</span>}
              </div>
              <input className="input" value={s.text} onChange={(e) => { const v = [...segments]; v[i] = { ...v[i], text: e.target.value }; setSegments(v); setDirty(true); }} style={{ width: "100%", marginTop: 4 }} />
            </div>
          ))}
          <button className="btn-primary" onClick={save} style={{ marginTop: 12 }}>Lưu tất cả thay đổi {dirty ? "(3+)" : ""}</button>
        </div>
        <div className="card" style={{ padding: 12 }}>
          <h4>Tóm tắt AI <span className="badge" style={{ background: analysis.data?.summary_status === "approved" ? "var(--success)22" : "var(--warning)22" }}>{analysis.data?.summary_status ?? "draft"}</span></h4>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Tiêu đề đề xuất: {analysis.data?.suggested_title ?? "—"}</div>
          <button onClick={regenerate} style={{ fontSize: 12, color: "var(--primary)", marginTop: 4 }}>Thử tiêu đề khác</button>
          <SummaryEditor videoId={videoId} initial={analysis.data?.summary ?? ""} />
          <div style={{ fontSize: 12, marginTop: 8 }}>Hashtags: {(analysis.data?.hashtags ?? []).join(" ")}</div>
        </div>
      </div>
    </div>
  );
}

function SummaryEditor({ videoId, initial }: { videoId: string; initial: string }) {
  const [text, setText] = useState(initial);
  useEffect(() => setText(initial), [initial]);
  const saveDraft = async () => { await apiClient.put(`/api/cms/videos/${videoId}/summary`, { summary: text }); alert("Đã lưu nháp"); };
  const approve = async () => { await apiClient.post(`/api/cms/videos/${videoId}/summary/approve`); alert("Đã phê duyệt"); };
  return (
    <div style={{ marginTop: 12 }}>
      <textarea className="input" value={text} onChange={(e) => setText(e.target.value)} rows={8} style={{ width: "100%" }} />
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button className="btn-primary" onClick={saveDraft}>Lưu nháp</button>
        <button className="btn-primary" onClick={approve} style={{ background: "var(--success)" }}>✓ Phê duyệt</button>
      </div>
    </div>
  );
}

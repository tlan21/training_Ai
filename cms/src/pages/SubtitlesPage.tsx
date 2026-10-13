import { useEffect, useRef, useState } from "react";
import { useSubtitles, useCmsAnalysis, useSettings } from "../hooks/useCms";
import { apiClient } from "../lib/apiClient";
import { VideoPlayer, PlayerHandle } from "../components/player/VideoPlayer";
import { useCmsVideo } from "../hooks/useCms";
import { useToast } from "../components/common/Toast";

export default function SubtitlesPage() {
  const [videoId, setVideoId] = useState("vid_stub01");
  const video = useCmsVideo(videoId);
  const subs = useSubtitles(videoId);
  const analysis = useCmsAnalysis(videoId);
  const settings = useSettings();
  const toast = useToast();
  const [segments, setSegments] = useState<any[]>([]);
  const [dirty, setDirty] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const playerRef = useRef<PlayerHandle>(null);
  const rowRefs = useRef<Record<number, HTMLDivElement | null>>({});

  useEffect(() => { if (subs.data?.segments) setSegments(subs.data.segments); }, [subs.data]);
  const activeIdx = segments.findIndex((s) => currentTime >= s.start_time && currentTime <= s.end_time);
  useEffect(() => { if (activeIdx >= 0) rowRefs.current[activeIdx]?.scrollIntoView({ block: "center", behavior: "smooth" }); }, [activeIdx]);
  useEffect(() => {
    const h = (e: BeforeUnloadEvent) => { if (dirty) { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", h);
    return () => window.removeEventListener("beforeunload", h);
  }, [dirty]);

  const save = async () => {
    try { await apiClient.put(`/api/cms/videos/${videoId}/subtitles`, { segments }); setDirty(false); toast.ok("Đã lưu phụ đề"); }
    catch (e: any) { toast.err(e?.apiError?.message ?? e.message); }
  };
  const regenerate = async () => {
    try {
      const r = await apiClient.post(`/api/cms/videos/${videoId}/summary/regenerate`);
      toast.ok(`Tiêu đề mới: ${r.data.suggested_title ?? "—"}`);
    } catch (e: any) { toast.err(e?.apiError?.message ?? e.message); }
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
          <h4>Transcript — {segments.length} segments {dirty && "(dirty — chưa lưu)"}</h4>
          {segments.length === 0 && <div style={{ color: "var(--text-muted)", fontSize: 13 }}>{subs.isLoading ? "Đang tải…" : subs.isError ? (subs.error as any)?.apiError?.message ?? "Lỗi tải phụ đề" : "Chưa có phụ đề"}</div>}
          {segments.map((s, i) => {
            const warn = s.warning === "low_confidence" || s.warning === "blacklist";
            const thr = settings.data?.asr_warning_threshold ?? 65;
            const lowByThr = (s.confidence * 100) < thr;
            return (
              <div key={i} ref={(el) => { rowRefs.current[i] = el; }} onClick={() => playerRef.current?.seekTo(s.start_time)} style={{ padding: 8, borderRadius: 6, background: warn || lowByThr ? "var(--danger)12" : i === activeIdx ? "var(--bg-surface-2)" : undefined, border: warn ? "1px solid var(--danger)" : i === activeIdx ? "1px solid var(--primary)" : "1px solid transparent", marginBottom: 6, cursor: "pointer" }}>
                <div style={{ fontSize: 11, fontFamily: "JetBrains Mono", color: warn || lowByThr ? "var(--danger)" : "var(--text-muted)" }}>
                  [{s.start_time?.toFixed?.(1) ?? s.start_time}–{s.end_time?.toFixed?.(1) ?? s.end_time}] — {(s.confidence * 100).toFixed(0)}% {(warn || lowByThr) && <span>⚠ {s.warning ?? `dưới ngưỡng ${thr}%`}</span>}
                  {warn && <span style={{ marginLeft: 6 }}>●</span>}
                </div>
                <input className="input" value={s.text} onChange={(e) => { const v = [...segments]; v[i] = { ...v[i], text: e.target.value }; setSegments(v); setDirty(true); }} style={{ width: "100%", marginTop: 4, borderColor: warn ? "var(--danger)" : undefined }} />
              </div>
            );
          })}
          <button className="btn-primary" onClick={save} style={{ marginTop: 12 }} disabled={!dirty}>Lưu tất cả thay đổi {dirty ? `(${segments.length})` : ""}</button>
        </div>
        <div className="card" style={{ padding: 12 }}>
          <h4>Tóm tắt AI <span className="badge" style={{ background: analysis.data?.summary_status === "approved" ? "var(--success)22" : "var(--warning)22", color: analysis.data?.summary_status === "approved" ? "var(--success)" : "var(--warning)", border: `1px solid ${analysis.data?.summary_status === "approved" ? "var(--success)" : "var(--warning)"}44` }}>{analysis.data?.summary_status === "approved" ? "Đã duyệt" : "Bản nháp AI"}</span></h4>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Tiêu đề đề xuất: {analysis.data?.suggested_title ?? "—"}</div>
          <button onClick={regenerate} style={{ fontSize: 12, color: "var(--primary)", marginTop: 4 }}>Thử tiêu đề khác</button>
          <SummaryEditor videoId={videoId} initial={analysis.data?.summary ?? ""} status={analysis.data?.summary_status} hashtags={analysis.data?.hashtags ?? []} />
        </div>
      </div>
    </div>
  );
}

function SummaryEditor({ videoId, initial, status, hashtags }: { videoId: string; initial: string; status?: string; hashtags: string[] }) {
  const [text, setText] = useState(initial);
  const toast = useToast();
  useEffect(() => setText(initial), [initial]);
  const isApproved = status === "approved";
  const saveDraft = async () => { try { await apiClient.put(`/api/cms/videos/${videoId}/summary`, { summary: text }); toast.ok("Đã lưu nháp"); } catch (e: any) { toast.err(e?.apiError?.message ?? e.message); } };
  const approve = async () => {
    try {
      if (text !== initial) await apiClient.put(`/api/cms/videos/${videoId}/summary`, { summary: text });
      await apiClient.post(`/api/cms/videos/${videoId}/summary/approve`);
      toast.ok("Đã phê duyệt — Client đã thấy");
    } catch (e: any) { toast.err(e?.apiError?.message ?? e.message); }
  };
  return (
    <div style={{ marginTop: 12 }}>
      <textarea className="input" value={text} onChange={(e) => setText(e.target.value)} rows={8} style={{ width: "100%" }} />
      {isApproved && <div style={{ fontSize: 11, color: "var(--warning)", marginTop: 4 }}>Đang ở trạng thái đã duyệt — sửa sẽ tạo bản nháp mới trước khi duyệt lại.</div>}
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button className="btn-primary" onClick={saveDraft}>Lưu nháp</button>
        <button className="btn-primary" onClick={approve} style={{ background: isApproved ? "var(--text-muted)" : "var(--success)", opacity: isApproved && text === initial ? 0.6 : 1 }} disabled={isApproved && text === initial} title={isApproved ? "Đã duyệt — sửa rồi duyệt lại" : "Phê duyệt"}>✓ Phê duyệt</button>
      </div>
      <div style={{ fontSize: 12, marginTop: 8, color: "var(--text-secondary)" }}>Hashtags: {hashtags.length ? hashtags.map((h) => <span key={h} style={{ marginRight: 6, background: "var(--bg-surface-2)", padding: "2px 6px", borderRadius: 4 }}>{h}</span>) : "—"}</div>
    </div>
  );
}

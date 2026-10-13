"use client";
import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { apiClient } from "@/lib/apiClient";
import { usePlayerStore, buildHighlightRanges, nextHighlightStart } from "@/stores/playerStore";
export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>();
  const sp = useSearchParams();
  const t = sp.get("t");
  const [video, setVideo] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [subs, setSubs] = useState<any>(null);
  const [err, setErr] = useState("");
  const vRef = useRef<HTMLVideoElement>(null);
  const store = usePlayerStore();
  useEffect(() => {
    apiClient.get(`/api/videos/${id}`).then((r) => setVideo(r.data)).catch((e) => setErr(e?.response?.data?.error?.message ?? e.message));
    apiClient.get(`/api/videos/${id}/analysis`).then((r) => setAnalysis(r.data)).catch(() => {});
    apiClient.get(`/api/videos/${id}/subtitles`).then((r) => setSubs(r.data)).catch(() => {});
    apiClient.post("/api/interactions", { video_id: id, interaction_type: "click" }).catch(() => {});
    return () => { apiClient.post("/api/interactions", { video_id: id, interaction_type: "watch_time", duration_watched: Math.floor(store.currentTime) }).catch(() => {}); };
  }, [id]);
  useEffect(() => {
    if (vRef.current) store.register(vRef.current);
  }, []);
  useEffect(() => {
    if (t && vRef.current) { const tt = Number(t); if (!isNaN(tt)) vRef.current.currentTime = tt; }
  }, [t, video]);
  const scores: { second: number; score: number }[] = analysis?.timeline_scores ?? [];
  const ranges = buildHighlightRanges(scores, 75);
  const onAuto = () => {
    const on = !store.autoHighlight; store.setAuto(on);
    if (on) { const nxt = nextHighlightStart(store.currentTime, ranges); if (nxt !== null) store.seekTo(nxt); }
  };
  const segments: any[] = subs?.segments ?? [];
  const activeIdx = segments.findIndex((s: any) => store.currentTime >= s.start_time && store.currentTime < s.end_time);
  if (err) return <div style={{ padding: 24, color: "var(--danger)" }}>{err} — <Link href="/feed" style={{ color: "var(--info)" }}>Về feed</Link></div>;
  if (!video) return <div style={{ padding: 24, color: "var(--text-secondary)" }}>Đang tải…</div>;
  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: 12, background: "var(--bg-base)", minHeight: "100vh" }}>
      <Link href="/feed" style={{ color: "var(--info)", fontSize: 13 }}>← Feed</Link>
      <h2 style={{ margin: "8px 0" }}>{video.title}</h2>
      <video ref={vRef} src={video.raw_file_path ?? video.playback_url ?? ""} controls style={{ width: "100%", borderRadius: 12, background: "black" }} onTimeUpdate={(e) => store.onTimeUpdate((e.target as HTMLVideoElement).currentTime)} onLoadedMetadata={(e) => store.setDuration((e.target as HTMLVideoElement).duration)} />
      <div style={{ display: "flex", gap: 8, marginTop: 8, overflowX: "auto" }}>
        {scores.slice(0, 60).map((s, i) => (
          <div key={i} onClick={() => store.seekTo(s.second)} style={{ minWidth: 6, height: 24, background: s.score > 75 ? "var(--success)" : s.score > 40 ? "var(--warning)" : "#3f3f46", borderRadius: 2, cursor: "pointer" }} title={`${s.second}s: ${s.score}`} />
        ))}
      </div>
      <button onClick={onAuto} style={{ marginTop: 8, padding: "8px 12px", borderRadius: 8, border: "none", background: store.autoHighlight ? "var(--accent)" : "var(--bg-surface-2)", color: "white" }}>⚡ {store.autoHighlight ? "Tắt" : "Bật"} Auto Play Highlights</button>
      {analysis?.summary && <div style={{ marginTop: 12, background: "var(--bg-surface)", padding: 12, borderRadius: 12 }}><strong>AI Summary</strong><div style={{ fontSize: 14, color: "var(--text-secondary)", marginTop: 6 }}>{analysis.summary}</div>{analysis.hashtags?.length ? <div style={{ marginTop: 6, fontSize: 12, color: "var(--info)" }}>{analysis.hashtags.join(" ")}</div> : null}</div>}
      {analysis?.key_moments?.length ? <div style={{ marginTop: 12 }}><strong>Điểm nhấn</strong>{analysis.key_moments.map((k: any, i: number) => <div key={i} onClick={() => store.seekTo(k.timestamp)} style={{ padding: 8, borderBottom: "1px solid var(--border)", cursor: "pointer", fontSize: 13 }}>{k.timestamp.toFixed(1)}s — {k.text}</div>)}</div> : null}
      <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
        <input placeholder="Tìm trong bản ghi" onChange={(e) => {
          const q = e.target.value.toLowerCase();
          // client filter via data attr
          document.querySelectorAll("[data-seg]").forEach((el) => {
            const t = (el as HTMLElement).dataset.text ?? "";
            (el as HTMLElement).style.display = t.includes(q) ? "" : "none";
          });
        }} style={{ flex: 1, background: "var(--bg-surface-2)", border: "1px solid var(--border)", borderRadius: 8, padding: 8, color: "white" }} />
        <button onClick={() => {
          const blob = new Blob([segments.map((s: any) => `[${s.start_time.toFixed(1)}-${s.end_time.toFixed(1)}] ${s.text}`).join("\n")], { type: "text/plain" });
          const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = `${id}.txt`; a.click(); URL.revokeObjectURL(url);
        }} style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "white" }}>Tải .txt</button>
      </div>
      <div style={{ marginTop: 8, maxHeight: 300, overflow: "auto", background: "var(--bg-surface)", borderRadius: 12, padding: 8 }}>
        {segments.map((s: any, i: number) => (
          <div key={i} data-seg data-text={s.text.toLowerCase()} onClick={() => store.seekTo(s.start_time)} style={{ padding: 6, borderRadius: 6, background: i === activeIdx ? "var(--bg-surface-2)" : "transparent", border: i === activeIdx ? "1px solid var(--info)" : "1px solid transparent", cursor: "pointer", fontSize: 13 }}>
            <span style={{ fontFamily: "monospace", color: "var(--text-secondary)", fontSize: 11 }}>[{s.start_time.toFixed(1)}]</span> {s.text}
          </div>
        ))}
        {segments.length === 0 && <div style={{ color: "var(--text-secondary)", fontSize: 13, padding: 8 }}>Chưa có phụ đề</div>}
      </div>
      <div style={{ marginTop: 12 }}><strong>Clip từ video này</strong><div style={{ display: "grid", gap: 8, marginTop: 8 }}>{(video.clips ?? []).map((c: any) => <Link key={c.id} href={`/videos/${id}?t=${c.start_time}`} style={{ padding: 10, background: "var(--bg-surface)", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}>{c.title} — {c.start_time.toFixed(1)}–{c.end_time.toFixed(1)}s</Link>)}</div></div>
    </div>
  );
}

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
  const [sheetOpen, setSheetOpen] = useState(false);
  if (err) return <div style={{ padding: 24, color: "var(--danger)" }}>{err} — <Link href="/feed" style={{ color: "var(--primary)" }}>Về feed</Link></div>;
  if (!video) return <div style={{ padding: 24, color: "var(--on-surface-variant)" }}>Đang tải…</div>;
  return (
    <div style={{ maxWidth: 640, margin: "0 auto", background: "var(--background)", minHeight: "100dvh", paddingBottom: 80 }}>
      <header style={{ position: "sticky", top: 0, zIndex: 20, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", background: "rgba(255,248,245,0.85)", backdropFilter: "blur(12px)", borderBottom: "1px solid var(--outline-variant)" }}>
        <button onClick={() => history.back()} style={{ background: "none", border: "none", cursor: "pointer" }}><span className="material-symbols-outlined">arrow_back_ios</span></button>
        <span style={{ fontWeight: 700, color: "var(--primary)" }}>VidsAI</span>
        <span className="material-symbols-outlined">share</span>
      </header>
      <div style={{ position: "relative", background: "black", aspectRatio: "16/9", overflow: "hidden" }}>
        <video ref={vRef} src={video.raw_file_path ?? video.playback_url ?? ""} controls style={{ width: "100%", height: "100%", objectFit: "contain" }} onTimeUpdate={(e) => store.onTimeUpdate((e.target as HTMLVideoElement).currentTime)} onLoadedMetadata={(e) => store.setDuration((e.target as HTMLVideoElement).duration)} poster={video.thumbnail_url ?? undefined} />
        <span style={{ position: "absolute", top: 12, right: 12, background: "rgba(0,0,0,0.5)", color: "white", fontSize: 10, padding: "4px 8px", borderRadius: 9999, backdropFilter: "blur(4px)" }}>AI Augmented</span>
      </div>
      <div style={{ padding: "8px 16px", display: "flex", flexDirection: "column", gap: 8, background: "black", color: "white" }}>
        <div style={{ display: "flex", gap: 2, height: 24, alignItems: "end" }}>
          {scores.slice(0, 24).map((s, i) => (
            <div key={i} onClick={() => store.seekTo(s.second)} style={{ flex: 1, height: `${Math.max(20, s.score)}%`, background: s.score > 75 ? "var(--secondary-container)" : s.score > 40 ? "var(--secondary)" : "rgba(124,58,237,0.35)", borderRadius: "2px 2px 0 0", cursor: "pointer" }} title={`${s.second}s: ${s.score}`} />
          ))}
        </div>
        <div style={{ height: 3, background: "rgba(255,255,255,0.25)", borderRadius: 9999, position: "relative" }}>
          <div style={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${Math.min(100, (store.currentTime / (store.duration || 1)) * 100)}%`, background: "var(--primary)", borderRadius: 9999 }} />
          <div style={{ position: "absolute", left: `calc(${Math.min(100, (store.currentTime / (store.duration || 1)) * 100)}% - 6px)`, top: "50%", transform: "translateY(-50%)", width: 12, height: 12, borderRadius: 9999, background: "var(--primary)", border: "2px solid white", boxShadow: "0 2px 8px rgba(0,0,0,0.3)" }} />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "rgba(255,255,255,0.7)" }}><span>{Math.floor(store.currentTime / 60).toString().padStart(2, "0")}:{(Math.floor(store.currentTime % 60)).toString().padStart(2, "0")}</span><span>{Math.floor((store.duration || 0) / 60).toString().padStart(2, "0")}:{(Math.floor((store.duration || 0) % 60)).toString().padStart(2, "0")}</span></div>
      </div>
      <button onClick={onAuto} style={{ margin: "12px 16px", padding: "8px 12px", borderRadius: 8, border: "none", background: store.autoHighlight ? "var(--primary)" : "var(--surface-container-high)", color: store.autoHighlight ? "var(--on-primary)" : "var(--on-surface)", fontWeight: 600, fontSize: 13 }}>⚡ {store.autoHighlight ? "Tắt" : "Bật"} Auto Play Highlights</button>
      <section style={{ padding: "16px 16px 0" }}>
        <h1 style={{ fontSize: 16, fontWeight: 700, lineHeight: 1.3 }}>{video.title}</h1>
        <div style={{ display: "flex", gap: 8, fontSize: 11, color: "var(--on-surface-variant)", marginTop: 6 }}>
          <span>{video.view_count ?? "1.2M"} lượt xem</span><span>•</span><span>{video.created_at ? new Date(video.created_at).toLocaleDateString("vi-VN") : "2 ngày trước"}</span>
          {video.category?.name && <span style={{ background: "var(--surface-variant)", padding: "2px 6px", borderRadius: 4, color: "var(--primary)", fontWeight: 700 }}>#{video.category.name}</span>}
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 12, overflowX: "auto" }}>
          <button style={{ display: "flex", gap: 6, alignItems: "center", background: "var(--surface-container-high)", padding: "8px 12px", borderRadius: 9999, border: "none", whiteSpace: "nowrap" }}><span className="material-symbols-outlined" style={{ fontSize: 18 }}>thumb_up</span> 45K</button>
          <button style={{ display: "flex", gap: 6, alignItems: "center", background: "var(--surface-container-high)", padding: "8px 12px", borderRadius: 9999, border: "none", whiteSpace: "nowrap" }}><span className="material-symbols-outlined" style={{ fontSize: 18 }}>bookmark</span> Lưu lại</button>
          <button onClick={() => setSheetOpen(true)} style={{ display: "flex", gap: 6, alignItems: "center", background: "var(--surface-container-high)", padding: "8px 12px", borderRadius: 9999, border: "none", whiteSpace: "nowrap" }}><span className="material-symbols-outlined" style={{ fontSize: 18 }}>description</span> Bản ghi</button>
        </div>
      </section>
      {analysis?.summary && (
        <section style={{ padding: "16px 16px 0" }}>
          <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 8 }}><span className="material-symbols-outlined" style={{ color: "var(--primary)", fontVariationSettings: "'FILL' 1", fontSize: 18 }}>auto_awesome</span><h2 style={{ fontSize: 16, fontWeight: 700 }}>Tóm tắt Thông minh bởi AI</h2></div>
          <div style={{ background: "rgba(124,58,237,0.08)", border: "1px solid rgba(124,58,237,0.15)", borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 14, color: "var(--on-surface-variant)", lineHeight: 1.6 }}>{analysis.summary}</div>
            {analysis.hashtags?.length ? <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" as any }}>{analysis.hashtags.map((h: string) => <span key={h} style={{ fontSize: 11, color: "var(--primary)", background: "var(--primary-fixed)", padding: "2px 8px", borderRadius: 9999 }}>{h}</span>)}</div> : null}
          </div>
          {analysis?.key_moments?.length ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 12 }}>
              {analysis.key_moments.slice(0, 2).map((k: any, i: number) => (
                <div key={i} onClick={() => store.seekTo(k.timestamp)} style={{ background: "var(--surface-container-low)", border: "1px solid var(--outline-variant)", borderRadius: 12, padding: 10, cursor: "pointer" }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "var(--primary)", textTransform: "uppercase" as any }}>{i === 0 ? "Điểm Nhấn" : "Kết Luận"}</div>
                  <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4 }}>{k.text} ({Math.floor(k.timestamp / 60)}:{String(Math.floor(k.timestamp % 60)).padStart(2, "0")})</div>
                </div>
              ))}
            </div>
          ) : null}
        </section>
      )}
      <section style={{ padding: "16px 16px 0" }}>
        <h2 style={{ fontSize: 16, fontWeight: 700 }}>Đề xuất cho bạn</h2>
        <div style={{ display: "grid", gap: 12, marginTop: 12 }}>
          {(video.clips ?? []).slice(0, 3).map((c: any) => (
            <Link key={c.id} href={`/videos/${id}?t=${c.start_time}`} style={{ display: "flex", gap: 12 }}>
              <div style={{ width: 140, height: 80, borderRadius: 8, background: "var(--surface-variant)", overflow: "hidden", flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{c.title}</div>
                <div style={{ fontSize: 11, color: "var(--on-surface-variant)", marginTop: 4 }}>{c.start_time.toFixed(1)}–{c.end_time.toFixed(1)}s</div>
              </div>
            </Link>
          ))}
          {(video.clips ?? []).length === 0 && <div style={{ fontSize: 13, color: "var(--on-surface-variant)" }}>Chưa có clip highlight cho video này.</div>}
        </div>
      </section>
      <nav style={{ position: "fixed", bottom: 0, left: 0, width: "100%", display: "flex", justifyContent: "space-around", alignItems: "center", padding: "0 16px", paddingBottom: "env(safe-area-inset-bottom)", height: 56, background: "var(--surface-container, white)", borderTop: "1px solid var(--outline-variant)", zIndex: 30 }}>
        <Link href="/feed" style={{ display: "flex", flexDirection: "column", alignItems: "center", color: "var(--on-surface-variant)" }}><span className="material-symbols-outlined">home</span><span style={{ fontSize: 10 }}>Trang chủ</span></Link>
        <Link href="/discover" style={{ display: "flex", flexDirection: "column", alignItems: "center", color: "var(--on-surface-variant)" }}><span className="material-symbols-outlined">explore</span><span style={{ fontSize: 10 }}>Khám phá</span></Link>
        <Link href="/profile" style={{ display: "flex", flexDirection: "column", alignItems: "center", background: "var(--primary-container)", color: "var(--on-primary-container)", borderRadius: 12, padding: "4px 12px" }}><span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>video_library</span><span style={{ fontSize: 10 }}>Thư viện</span></Link>
        <Link href="/profile" style={{ display: "flex", flexDirection: "column", alignItems: "center", color: "var(--on-surface-variant)" }}><span className="material-symbols-outlined">person</span><span style={{ fontSize: 10 }}>Cá nhân</span></Link>
      </nav>
      {sheetOpen && (
        <div style={{ position: "fixed", inset: 0, zIndex: 50 }}>
          <div onClick={() => setSheetOpen(false)} style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.4)", backdropFilter: "blur(4px)" }} />
          <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, maxHeight: "75dvh", background: "white", borderRadius: "24px 24px 0 0", display: "flex", flexDirection: "column", overflow: "hidden", boxShadow: "0 -8px 32px rgba(0,0,0,0.15)" }}>
            <div onClick={() => setSheetOpen(false)} style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "8px 0 12px", cursor: "pointer" }}>
              <div style={{ width: 40, height: 4, borderRadius: 9999, background: "var(--outline-variant)" }} />
              <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 8 }}>Bản ghi Nội dung</h3>
            </div>
            <div style={{ flex: 1, overflow: "auto", padding: "0 24px 24px", display: "grid", gap: 12 }}>
              {segments.map((s: any, i: number) => (
                <div key={i} data-seg data-text={s.text.toLowerCase()} onClick={() => { store.seekTo(s.start_time); setSheetOpen(false); }} style={{ display: "flex", gap: 12, padding: i === activeIdx ? 12 : "0", background: i === activeIdx ? "rgba(124,58,237,0.08)" : "transparent", borderLeft: i === activeIdx ? "4px solid var(--primary)" : "4px solid transparent", borderRadius: 8, cursor: "pointer" }}>
                  <span style={{ fontWeight: 700, color: "var(--primary)", fontSize: 13, flexShrink: 0 }}>{String(Math.floor(s.start_time / 60)).padStart(2, "0")}:{(Math.floor(s.start_time % 60)).toString().padStart(2, "0")}</span>
                  <span style={{ fontSize: 14, color: i === activeIdx ? "var(--on-surface)" : "var(--on-surface-variant)", fontWeight: i === activeIdx ? 600 : 400 }}>{s.text}</span>
                </div>
              ))}
              {segments.length === 0 && <div style={{ color: "var(--on-surface-variant)", fontSize: 13, padding: 12 }}>Chưa có phụ đề</div>}
            </div>
            <div style={{ padding: 12, borderTop: "1px solid var(--outline-variant)", display: "flex", gap: 8, background: "white" }}>
              <div style={{ flex: 1, background: "var(--surface-container)", borderRadius: 9999, padding: "8px 16px", display: "flex", gap: 8, alignItems: "center" }}>
                <span className="material-symbols-outlined" style={{ color: "var(--on-surface-variant)", fontSize: 18 }}>search</span>
                <input placeholder="Tìm trong bản ghi..." onChange={(e) => {
                  const q = e.target.value.toLowerCase();
                  document.querySelectorAll("[data-seg]").forEach((el) => {
                    const t = (el as HTMLElement).dataset.text ?? "";
                    (el as HTMLElement).style.display = t.includes(q) ? "" : "none";
                  });
                }} style={{ flex: 1, border: "none", background: "transparent", outline: "none", fontSize: 13 }} />
              </div>
              <button onClick={() => {
                const blob = new Blob([segments.map((s: any) => `[${s.start_time.toFixed(1)}-${s.end_time.toFixed(1)}] ${s.text}`).join("\n")], { type: "text/plain" });
                const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = `${id}.txt`; a.click(); URL.revokeObjectURL(url);
              }} style={{ padding: "8px 12px", borderRadius: 9999, border: "none", background: "var(--primary)", color: "white", fontWeight: 600, fontSize: 13 }}>Tải .txt</button>
              <button onClick={() => setSheetOpen(false)} style={{ padding: 8, borderRadius: 9999, border: "none", background: "transparent" }}><span className="material-symbols-outlined">close</span></button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

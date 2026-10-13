"use client";
import { useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/apiClient";
import { BottomNav } from "@/components/BottomNav";
export default function SearchPage() {
  const [tab, setTab] = useState<"visual" | "text">("text");
  const [q, setQ] = useState("");
  const [visualResults, setVisualResults] = useState<any[]>([]);
  const [textResults, setTextResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [similarity, setSimilarity] = useState(85);
  const doVisual = async (file: File) => {
    setLoading(true);
    const fd = new FormData(); fd.append("image", file); fd.append("min_similarity", String(similarity / 100));
    try { const r = await apiClient.post("/api/search/visual", fd, { headers: { "Content-Type": "multipart/form-data" } }); setVisualResults(r.data.results ?? []); } catch (e) { setVisualResults([]); } finally { setLoading(false); }
  };
  const doText = async (qq: string) => {
    if (!qq) { setTextResults([]); return; }
    setLoading(true);
    try { const r = await apiClient.get("/api/search", { params: { q: qq } }); setTextResults(r.data.items ?? []); } catch { setTextResults([]); } finally { setLoading(false); }
  };
  return (
    <div style={{ maxWidth: 640, margin: "0 auto", minHeight: "100dvh", background: "var(--background)", paddingBottom: 72 }}>
      <header style={{ position: "sticky", top: 0, zIndex: 20, display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", background: "rgba(255,248,245,0.85)", backdropFilter: "blur(12px)", borderBottom: "1px solid var(--outline-variant)" }}>
        <Link href="/feed" style={{ width: 36, height: 36, borderRadius: 9999, display: "grid", placeItems: "center", background: "var(--surface-container)" }}><span className="material-symbols-outlined" style={{ fontSize: 20 }}>arrow_back</span></Link>
        <h1 style={{ fontSize: 18, fontWeight: 800, color: "var(--primary)" }}>Tìm kiếm</h1>
        <span className="material-symbols-outlined" style={{ marginLeft: "auto", color: "var(--on-surface-variant)" }}>history</span>
      </header>
      <div style={{ display: "flex", padding: 6, background: "var(--surface-container)", borderRadius: 12, margin: "16px 16px 0", gap: 6 }}>
        <button onClick={() => setTab("text")} style={{ flex: 1, padding: "8px 12px", borderRadius: 8, border: "none", background: tab === "text" ? "var(--primary)" : "transparent", color: tab === "text" ? "var(--on-primary)" : "var(--on-surface-variant)", fontWeight: 700, fontSize: 13, boxShadow: tab === "text" ? "0 2px 8px rgba(99,14,212,0.2)" : "none" }}>Văn bản</button>
        <button onClick={() => setTab("visual")} style={{ flex: 1, padding: "8px 12px", borderRadius: 8, border: "none", background: tab === "visual" ? "var(--primary)" : "transparent", color: tab === "visual" ? "var(--on-primary)" : "var(--on-surface-variant)", fontWeight: 700, fontSize: 13, boxShadow: tab === "visual" ? "0 2px 8px rgba(99,14,212,0.2)" : "none" }}>Hình ảnh</button>
      </div>
      {tab === "text" ? (
        <div style={{ padding: "16px 16px 0" }}>
          <div style={{ position: "relative" }}>
            <span className="material-symbols-outlined" style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--outline)", fontSize: 20 }}>search</span>
            <input value={q} onChange={(e) => { setQ(e.target.value); doText(e.target.value); }} placeholder="Nhập mô tả video hoặc khoảnh khắc..." style={{ width: "100%", padding: "14px 44px 14px 44px", background: "white", border: "1px solid var(--outline-variant)", borderRadius: 16, fontSize: 14, outline: "none", boxShadow: "0 1px 4px rgba(0,0,0,0.04)" }} />
            <span className="material-symbols-outlined" style={{ position: "absolute", right: 14, top: "50%", transform: "translateY(-50%)", color: "var(--primary)", fontSize: 20 }}>mic</span>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" as any }}>
            {(["#ng_ký", "#ambient", "#thiên_nhiên", "#vlog"] as const).map((t) => (
              <span key={t} onClick={() => { setQ(t.slice(1)); doText(t.slice(1)); }} style={{ padding: "6px 12px", background: "var(--surface-container-high)", borderRadius: 9999, fontSize: 11, color: "var(--on-surface-variant)", cursor: "pointer" }}>{t}</span>
            ))}
          </div>
          <h3 style={{ fontSize: 15, fontWeight: 700, marginTop: 20 }}>Kết quả tìm kiếm</h3>
          {loading ? <div style={{ padding: 16, color: "var(--on-surface-variant)", textAlign: "center" }}>Đang tìm…</div> : null}
          <div style={{ display: "grid", gap: 12, marginTop: 12 }}>
            {textResults.map((r: any, i: number) => (
              <Link key={i} href={`/videos/${r.video_id}?t=${r.timestamp ?? 0}`} style={{ display: "flex", gap: 12, background: "white", border: "1px solid var(--outline-variant)", borderRadius: 16, padding: 10, boxShadow: "0 1px 6px rgba(0,0,0,0.04)" }}>
                <div style={{ width: 120, height: 72, borderRadius: 8, background: "var(--surface-variant)", overflow: "hidden", flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 13, display: "-webkit-box", WebkitLineClamp: 1, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{r.title ?? r.video_id}</div>
                  <div style={{ fontSize: 11, color: "var(--on-surface-variant)", fontStyle: "italic", marginTop: 4, display: "-webkit-box", WebkitLineClamp: 1, WebkitBoxOrient: "vertical", overflow: "hidden" }}>"{r.matched_text ?? ""}"</div>
                  <div style={{ fontSize: 10, color: "var(--outline)", marginTop: 4 }}>{r.timestamp != null ? `${r.timestamp.toFixed(1)}s` : ""}</div>
                </div>
                <div style={{ width: 32, height: 32, borderRadius: 9999, background: "var(--primary)", display: "grid", placeItems: "center", flexShrink: 0, alignSelf: "center" }}>
                  <span className="material-symbols-outlined" style={{ color: "white", fontSize: 16, fontVariationSettings: "'FILL' 1" }}>play_arrow</span>
                </div>
              </Link>
            ))}
            {textResults.length === 0 && q && !loading && <div style={{ color: "var(--on-surface-variant)", fontSize: 13, textAlign: "center", padding: 16 }}>Không có kết quả cho "{q}"</div>}
          </div>
        </div>
      ) : (
        <div style={{ padding: "16px 16px 0" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <label style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: 20, background: "white", border: "2px dashed var(--outline-variant)", borderRadius: 16, cursor: "pointer", textAlign: "center" }}>
              <div style={{ width: 44, height: 44, borderRadius: 9999, background: "var(--primary-container)", display: "grid", placeItems: "center", marginBottom: 8 }}><span className="material-symbols-outlined" style={{ color: "var(--on-primary-container)" }}>photo_library</span></div>
              <span style={{ fontSize: 12, fontWeight: 600 }}>Chọn từ thư viện</span>
              <input type="file" accept="image/*" style={{ display: "none" }} onChange={(e) => { const f = e.target.files?.[0]; if (f) doVisual(f); }} />
            </label>
            <label style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: 20, background: "white", border: "2px dashed var(--outline-variant)", borderRadius: 16, cursor: "pointer", textAlign: "center" }}>
              <div style={{ width: 44, height: 44, borderRadius: 9999, background: "var(--secondary-container)", display: "grid", placeItems: "center", marginBottom: 8 }}><span className="material-symbols-outlined" style={{ color: "var(--on-secondary-container)" }}>photo_camera</span></div>
              <span style={{ fontSize: 12, fontWeight: 600 }}>Mở máy ảnh</span>
              <input type="file" accept="image/*" capture="environment" style={{ display: "none" }} onChange={(e) => { const f = e.target.files?.[0]; if (f) doVisual(f); }} />
            </label>
          </div>
          <div style={{ marginTop: 12, display: "flex", gap: 8, background: "var(--surface-container-low)", padding: 12, borderRadius: 12, border: "1px solid var(--outline-variant)", fontSize: 12, color: "var(--on-surface-variant)", alignItems: "center" }}>
            <span className="material-symbols-outlined" style={{ color: "var(--primary)", fontSize: 18 }}>info</span> AI sẽ tìm video có khung hình tương đồng với ảnh của bạn.
          </div>
          <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "var(--on-surface-variant)", whiteSpace: "nowrap" as any }}>Tương đồng {similarity}%</span>
            <input type="range" min={50} max={100} value={similarity} onChange={(e) => setSimilarity(Number(e.target.value))} style={{ flex: 1, accentColor: "var(--primary)" }} />
          </div>
          {loading && <div style={{ padding: 16, textAlign: "center", color: "var(--on-surface-variant)" }}>Đang so khớp…</div>}
          <div style={{ display: "grid", gap: 12, marginTop: 12 }}>
            {visualResults.map((r: any, i: number) => (
              <div key={i} style={{ display: "flex", gap: 12, background: "white", border: "1px solid var(--outline-variant)", borderRadius: 16, padding: 10, boxShadow: "0 1px 6px rgba(0,0,0,0.04)" }}>
                <div style={{ width: 120, height: 72, borderRadius: 8, background: "var(--surface-variant)", overflow: "hidden", flexShrink: 0, position: "relative" }}>
                  {r.thumbnail_url ? <img src={r.thumbnail_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : null}
                  <span style={{ position: "absolute", bottom: 4, right: 4, background: "rgba(0,0,0,0.65)", color: "white", fontSize: 10, padding: "2px 6px", borderRadius: 4 }}>{r.timestamp?.toFixed(1)}s</span>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>{r.video_id}</div>
                  <div style={{ fontSize: 10, fontWeight: 700, marginTop: 4, color: r.similarity_score > 0.9 ? "#008631" : "var(--primary)", background: r.similarity_score > 0.9 ? "rgba(0,134,49,0.1)" : "rgba(99,14,212,0.1)", display: "inline-block", padding: "2px 6px", borderRadius: 4 }}>{(r.similarity_score * 100).toFixed(0)}% Tương đồng</div>
                  <div style={{ fontSize: 11, color: "var(--on-surface-variant)", fontStyle: "italic", marginTop: 4, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>—</div>
                </div>
                <Link href={`/videos/${r.video_id}?t=${r.timestamp}`} style={{ width: 32, height: 32, borderRadius: 9999, background: "var(--primary)", display: "grid", placeItems: "center", flexShrink: 0, alignSelf: "center" }}>
                  <span className="material-symbols-outlined" style={{ color: "white", fontSize: 16, fontVariationSettings: "'FILL' 1" }}>play_arrow</span>
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}
      <BottomNav active="home" />
    </div>
  );
}

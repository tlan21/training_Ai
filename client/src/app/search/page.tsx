"use client";
import { useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/apiClient";
export default function SearchPage() {
  const [tab, setTab] = useState<"visual" | "text">("visual");
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
    <div style={{ maxWidth: 640, margin: "0 auto", padding: 12, minHeight: "100vh", background: "var(--bg-base)" }}>
      <div style={{ display: "flex", gap: 8, borderBottom: "1px solid var(--border)", marginBottom: 12 }}>
        <button onClick={() => setTab("visual")} style={{ padding: "8px 12px", borderBottom: tab === "visual" ? "2px solid var(--accent)" : "2px solid transparent", background: "none", color: tab === "visual" ? "var(--text-primary)" : "var(--text-secondary)", fontWeight: 700 }}>Visual</button>
        <button onClick={() => setTab("text")} style={{ padding: "8px 12px", borderBottom: tab === "text" ? "2px solid var(--accent)" : "2px solid transparent", background: "none", color: tab === "text" ? "var(--text-primary)" : "var(--text-secondary)", fontWeight: 700 }}>Text</button>
        <Link href="/feed" style={{ marginLeft: "auto", color: "var(--info)", fontSize: 13, padding: 8 }}>Feed</Link>
      </div>
      {tab === "visual" ? (
        <div>
          <div style={{ border: "2px dashed var(--border)", borderRadius: 12, padding: 24, textAlign: "center", background: "var(--bg-surface)" }}>
            <div>Kéo thả ảnh hoặc</div>
            <label style={{ display: "inline-block", marginTop: 8, padding: "8px 16px", background: "var(--accent)", color: "white", borderRadius: 8, cursor: "pointer" }}>
              📷 Mở camera / Chọn ảnh
              <input type="file" accept="image/*" capture="environment" style={{ display: "none" }} onChange={(e) => { const f = e.target.files?.[0]; if (f) doVisual(f); }} />
            </label>
          </div>
          <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Mức độ tương đồng {similarity}%</span>
            <input type="range" min={50} max={100} value={similarity} onChange={(e) => setSimilarity(Number(e.target.value))} style={{ flex: 1 }} />
          </div>
          {loading && <div style={{ padding: 12, color: "var(--text-secondary)" }}>Đang so khớp…</div>}
          <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
            {visualResults.map((r: any, i: number) => (
              <div key={i} style={{ display: "flex", gap: 12, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 8 }}>
                <div style={{ width: 80, height: 60, borderRadius: 8, background: "var(--bg-surface-2)", overflow: "hidden" }}>{r.thumbnail_url ? <img src={r.thumbnail_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : null}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{r.video_id}</div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{r.timestamp?.toFixed(1)}s · khớp {(r.similarity_score * 100).toFixed(1)}%</div>
                  <Link href={`/videos/${r.video_id}?t=${r.timestamp}`} style={{ fontSize: 12, color: "var(--info)" }}>Jump to Scene</Link>
                </div>
              </div>
            ))}
            {visualResults.length === 0 && !loading && <div style={{ color: "var(--text-secondary)", fontSize: 13 }}>Không tìm thấy phân cảnh khớp</div>}
          </div>
        </div>
      ) : (
        <div>
          <input value={q} onChange={(e) => { setQ(e.target.value); doText(e.target.value); }} placeholder="Nhập từ khóa…" style={{ width: "100%", background: "var(--bg-surface-2)", border: "1px solid var(--border)", borderRadius: 8, padding: 12, color: "white" }} />
          {loading && <div style={{ padding: 12, color: "var(--text-secondary)" }}>Đang tìm…</div>}
          <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
            {textResults.map((r: any, i: number) => (
              <Link key={i} href={`/videos/${r.video_id}?t=${r.timestamp ?? 0}`} style={{ padding: 10, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 8 }}>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{r.title ?? r.video_id}</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>"{r.matched_text ?? ""}" {r.timestamp != null ? `· ${r.timestamp.toFixed(1)}s` : ""}</div>
              </Link>
            ))}
            {textResults.length === 0 && q && !loading && <div style={{ color: "var(--text-secondary)", fontSize: 13 }}>Không có kết quả cho "{q}"</div>}
          </div>
        </div>
      )}
    </div>
  );
}

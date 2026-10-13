"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/apiClient";
type Clip = { id: string; video_id: string; title: string; thumbnail_url?: string; playback_url?: string; average_score?: number };
export default function FeedPage() {
  const [items, setItems] = useState<Clip[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const load = async (c?: string | null) => {
    setLoading(true);
    try { const r = await apiClient.get("/api/feed", { params: { cursor: c ?? undefined, limit: 10 } }); setItems((prev) => c ? [...prev, ...(r.data.items ?? [])] : (r.data.items ?? [])); setCursor(r.data.next_cursor ?? null); } catch {} finally { setLoading(false); }
  };
  useEffect(() => { load(null); }, []);
  const track = (clip: Clip, type: string, extra: any = {}) => apiClient.post("/api/interactions", { video_id: clip.video_id, clip_id: clip.id, interaction_type: type, ...extra }).catch(() => {});
  return (
    <div style={{ maxWidth: 420, margin: "0 auto", minHeight: "100vh", background: "var(--bg-base)" }}>
      <div style={{ padding: 12, display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)" }}>
        <strong>VidsAI Feed</strong>
        <div style={{ display: "flex", gap: 8 }}>
          <Link href="/search" style={{ color: "var(--info)" }}>Tìm kiếm</Link>
          <Link href="/discover" style={{ color: "var(--info)" }}>Khám phá</Link>
          <Link href="/profile" style={{ color: "var(--text-secondary)" }}>Profile</Link>
        </div>
      </div>
      {loading && items.length === 0 ? <div style={{ padding: 24, textAlign: "center", color: "var(--text-secondary)" }}>Đang tải…</div> : null}
      {items.length === 0 && !loading ? <div style={{ padding: 24, textAlign: "center", color: "var(--text-secondary)" }}>Chưa có nội dung — chọn thêm chủ đề <Link href="/onboarding" style={{ color: "var(--accent)" }}>ở đây</Link></div> : null}
      <div style={{ display: "grid", gap: 12, padding: 12 }}>
        {items.map((clip) => (
          <div key={clip.id} style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
            <div style={{ aspectRatio: "16/9", background: "var(--bg-surface-2)", display: "grid", placeItems: "center", color: "var(--text-secondary)" }}>{clip.thumbnail_url ? <img src={clip.thumbnail_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : "No thumbnail"}</div>
            <div style={{ padding: 12 }}>
              <div style={{ fontWeight: 700 }}>{clip.title}</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>avg {clip.average_score ?? "—"} | {clip.id.slice(0, 8)}</div>
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <Link href={`/videos/${clip.video_id}`} onClick={() => track(clip, "click")} style={{ background: "var(--accent)", color: "white", padding: "6px 12px", borderRadius: 8, fontSize: 13 }}>Xem video gốc</Link>
                <button onClick={() => track(clip, "like")} style={{ padding: "6px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "white" }}>♥ Like</button>
                <button onClick={() => track(clip, "save")} style={{ padding: "6px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "white" }}>☆ Lưu</button>
              </div>
            </div>
          </div>
        ))}
      </div>
      {cursor && <button onClick={() => load(cursor)} style={{ width: "100%", padding: 12, background: "transparent", border: "none", color: "var(--info)" }}>Tải thêm</button>}
    </div>
  );
}

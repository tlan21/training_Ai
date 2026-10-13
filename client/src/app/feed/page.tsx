"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/apiClient";
import { BottomNav } from "@/components/BottomNav";
type Clip = { id: string; video_id: string; title: string; thumbnail_url?: string; playback_url?: string; average_score?: number };
export default function FeedPage() {
  const [items, setItems] = useState<Clip[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(0);
  const refs = useRef<(HTMLDivElement | null)[]>([]);
  const load = async (c?: string | null) => {
    setLoading(true);
    try { const r = await apiClient.get("/api/feed", { params: { cursor: c ?? undefined, limit: 10 } }); setItems((prev) => c ? [...prev, ...(r.data.items ?? [])] : (r.data.items ?? [])); setCursor(r.data.next_cursor ?? null); } catch {} finally { setLoading(false); }
  };
  useEffect(() => { load(null); }, []);
  useEffect(() => {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { const idx = Number((e.target as HTMLElement).dataset.idx); setActive(idx); const clip = items[idx]; if (clip) apiClient.post("/api/interactions", { video_id: clip.video_id, clip_id: clip.id, interaction_type: "click" }).catch(() => {}); } });
    }, { threshold: 0.7 });
    refs.current.forEach((el) => el && obs.observe(el));
    return () => obs.disconnect();
  }, [items]);
  const track = (clip: Clip, type: string, extra: any = {}) => apiClient.post("/api/interactions", { video_id: clip.video_id, clip_id: clip.id, interaction_type: type, ...extra }).catch(() => {});
  const [liked, setLiked] = useState<Set<string>>(new Set());
  const toggleLike = (c: Clip) => {
    const on = liked.has(c.id);
    setLiked((s) => { const n = new Set(s); if (on) n.delete(c.id); else n.add(c.id); return n; });
    track(c, "like");
  };
  return (
    <div style={{ background: "black", minHeight: "100dvh", paddingBottom: 56 }}>
      <header style={{ position: "sticky", top: 0, zIndex: 10, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", background: "linear-gradient(to bottom, rgba(0,0,0,0.5), transparent)", color: "white" }}>
        <span style={{ fontSize: 11, fontWeight: 700, borderBottom: "2px solid white", paddingBottom: 2 }}>Dành cho bạn</span>
        <Link href="/search" style={{ color: "white" }}><span className="material-symbols-outlined">search</span></Link>
      </header>
      {loading && items.length === 0 ? <div style={{ padding: 40, textAlign: "center", color: "white" }}>Đang tải…</div> : null}
      {items.length === 0 && !loading ? <div style={{ padding: 40, textAlign: "center", color: "white" }}>Chưa có nội dung — <Link href="/onboarding" style={{ color: "var(--primary)" }}>chọn chủ đề</Link></div> : null}
      <div style={{ scrollSnapType: "y mandatory", scrollBehavior: "smooth" }}>
        {items.map((clip, i) => (
          <div key={clip.id} data-idx={i} ref={(el) => { refs.current[i] = el; }} style={{ height: "calc(100dvh - 56px)", scrollSnapAlign: "start", position: "relative", overflow: "hidden", background: "black" }}>
            <div style={{ position: "absolute", inset: 0, background: clip.thumbnail_url ? `url(${clip.thumbnail_url}) center/cover` : "var(--bg-surface-2)", opacity: 0.9 }} />
            <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.3) 40%, transparent 70%)" }} />
            <aside style={{ position: "absolute", right: 12, bottom: 100, display: "flex", flexDirection: "column", gap: 16, alignItems: "center", zIndex: 2 }}>
              <button onClick={() => toggleLike(clip)} style={{ width: 44, height: 44, borderRadius: 9999, background: "rgba(0,0,0,0.25)", backdropFilter: "blur(8px)", border: "none", display: "grid", placeItems: "center", color: liked.has(clip.id) ? "#ff4b4b" : "white" }}>
                <span className="material-symbols-outlined" style={{ fontVariationSettings: liked.has(clip.id) ? "'FILL' 1" : "'FILL' 0", fontSize: 28 }}>favorite</span>
              </button>
              <div style={{ fontSize: 10, color: "white", fontWeight: 600 }}>Like</div>
              <button onClick={() => track(clip, "save")} style={{ width: 44, height: 44, borderRadius: 9999, background: "rgba(0,0,0,0.25)", backdropFilter: "blur(8px)", border: "none", display: "grid", placeItems: "center", color: "white" }}>
                <span className="material-symbols-outlined" style={{ fontSize: 24 }}>bookmark</span>
              </button>
              <button onClick={() => track(clip, "share")} style={{ width: 44, height: 44, borderRadius: 9999, background: "rgba(0,0,0,0.25)", backdropFilter: "blur(8px)", border: "none", display: "grid", placeItems: "center", color: "white" }}>
                <span className="material-symbols-outlined" style={{ fontSize: 24 }}>share</span>
              </button>
            </aside>
            <div style={{ position: "absolute", bottom: 20, left: 12, right: 60, zIndex: 2, color: "white" }}>
              <div style={{ fontWeight: 700, fontSize: 13 }}>@{clip.video_id.slice(0, 8)}</div>
              <div style={{ fontSize: 13, marginTop: 4, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" as any }}>{clip.title}</div>
              <Link href={`/videos/${clip.video_id}`} style={{ display: "inline-block", marginTop: 8, background: "white", color: "black", padding: "6px 12px", borderRadius: 9999, fontSize: 12, fontWeight: 700 }}>Xem video gốc</Link>
            </div>
          </div>
        ))}
      </div>
      {cursor && <button onClick={() => load(cursor)} style={{ width: "100%", padding: 12, background: "black", color: "white", border: "none" }}>Tải thêm</button>}
      <BottomNav active="home" />
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/apiClient";
import { BottomNav } from "@/components/BottomNav";
export default function DiscoverPage() {
  const [cats, setCats] = useState<{ id: string; name: string }[]>([]);
  const [active, setActive] = useState<string>("");
  const [videos, setVideos] = useState<any[]>([]);
  const [sort, setSort] = useState<"newest" | "trending">("newest");
  useEffect(() => { apiClient.get("/api/categories").then((r) => setCats(r.data)).catch(() => {}); }, []);
  useEffect(() => {
    apiClient.get("/api/videos", { params: { category_id: active || undefined, sort } }).then((r) => setVideos(r.data.items ?? [])).catch(() => setVideos([]));
  }, [active, sort]);
  return (
    <div style={{ minHeight: "100dvh", background: "var(--background)", paddingBottom: 72 }}>
      <header style={{ position: "sticky", top: 0, zIndex: 20, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", background: "rgba(255,248,245,0.85)", backdropFilter: "blur(12px)", borderBottom: "1px solid var(--outline-variant)" }}>
        <span style={{ fontWeight: 800, fontSize: 18, color: "var(--primary)" }}>VidsAI</span>
        <div style={{ display: "flex", gap: 12, color: "var(--on-surface-variant)" }}>
          <span className="material-symbols-outlined">search</span>
          <span className="material-symbols-outlined">notifications</span>
        </div>
      </header>
      <section style={{ padding: "12px 16px" }}>
        <div style={{ display: "flex", background: "var(--surface-container-low)", borderRadius: 12, padding: "10px 12px", gap: 8, alignItems: "center", border: "1px solid var(--outline-variant)" }}>
          <span className="material-symbols-outlined" style={{ color: "var(--outline)", fontSize: 20 }}>search</span>
          <input placeholder="Tìm kiếm video, hình ảnh..." style={{ flex: 1, border: "none", background: "transparent", outline: "none", fontSize: 13 }} />
          <span className="material-symbols-outlined" style={{ color: "var(--primary)", fontVariationSettings: "'FILL' 1" }}>image_search</span>
        </div>
      </section>
      <section style={{ padding: "0 16px", display: "flex", gap: 8, overflowX: "auto", scrollbarWidth: "none" } as any}>
        <button onClick={() => setActive("")} style={{ flexShrink: 0, padding: "8px 16px", borderRadius: 9999, border: "none", background: active === "" ? "var(--primary)" : "var(--surface-container-high)", color: active === "" ? "var(--on-primary)" : "var(--on-surface)", fontWeight: 600, fontSize: 13 }}>Tất cả</button>
        {cats.map((c) => (
          <button key={c.id} onClick={() => setActive(c.id)} style={{ flexShrink: 0, padding: "8px 16px", borderRadius: 9999, border: "none", background: active === c.id ? "var(--primary)" : "var(--surface-container-high)", color: active === c.id ? "var(--on-primary)" : "var(--on-surface)", fontWeight: 600, fontSize: 13 }}>{c.name}</button>
        ))}
      </section>
      <section style={{ padding: "16px 16px 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <h2 style={{ fontSize: 16, fontWeight: 700 }}>Tiếp tục xem</h2>
          <Link href="/feed" style={{ color: "var(--primary)", fontSize: 13, fontWeight: 600 }}>Xem tất cả</Link>
        </div>
        <div style={{ display: "flex", gap: 12, overflowX: "auto", marginTop: 12, scrollbarWidth: "none" } as any}>
          {videos.slice(0, 2).map((v: any) => (
            <Link key={v.id} href={`/videos/${v.id}`} style={{ minWidth: 240, flexShrink: 0 }}>
              <div style={{ aspectRatio: "16/9", borderRadius: 12, background: "var(--surface-variant)", overflow: "hidden", position: "relative" }}>
                {v.thumbnail_url ? <img src={v.thumbnail_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : null}
                <span style={{ position: "absolute", bottom: 6, right: 6, background: "rgba(0,0,0,0.65)", color: "white", fontSize: 10, padding: "2px 6px", borderRadius: 4 }}>12:45</span>
                <div style={{ position: "absolute", bottom: 0, left: 0, width: "100%", height: 4, background: "var(--surface-variant)" }}><div style={{ height: "100%", width: "65%", background: "var(--primary)" }} /></div>
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 6, display: "-webkit-box", WebkitLineClamp: 1, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{v.title}</div>
              <div style={{ fontSize: 11, color: "var(--on-surface-variant)" }}>{v.category?.name ?? ""} • 1.2M lượt xem</div>
            </Link>
          ))}
          {videos.length === 0 && <div style={{ color: "var(--on-surface-variant)", fontSize: 13 }}>Không có video</div>}
        </div>
      </section>
      <section style={{ padding: "16px 16px 0" }}>
        <h2 style={{ fontSize: 16, fontWeight: 700 }}>Gợi ý cho bạn</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 }}>
          {videos.slice(0, 3).map((v: any, i: number) => (
            <Link key={v.id} href={`/videos/${v.id}`} style={{ gridColumn: i === 0 ? "span 2" : "span 1", borderRadius: 16, overflow: "hidden", background: "var(--surface-container-lowest)", border: "1px solid var(--outline-variant)", display: "block" }}>
              <div style={{ aspectRatio: i === 0 ? "16/9" : "1/1", background: "var(--surface-variant)", position: "relative" }}>
                {v.thumbnail_url ? <img src={v.thumbnail_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : null}
                {i === 0 && <span style={{ position: "absolute", top: 8, left: 8, background: "var(--primary)", color: "white", fontSize: 10, fontWeight: 700, padding: "4px 8px", borderRadius: 9999 }}>Nổi bật</span>}
              </div>
              <div style={{ padding: 10 }}>
                <div style={{ fontSize: 13, fontWeight: 700, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{v.title}</div>
                <div style={{ fontSize: 11, color: "var(--on-surface-variant)", marginTop: 4 }}>{v.category?.name ?? ""}</div>
              </div>
            </Link>
          ))}
        </div>
      </section>
      <section style={{ padding: "16px 16px 0" }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, display: "flex", gap: 6 }}><span className="material-symbols-outlined" style={{ color: "var(--secondary)", fontVariationSettings: "'FILL' 1" }}>trending_up</span> Đang thịnh hành</h2>
        <div style={{ display: "grid", gap: 12, marginTop: 12 }}>
          {videos.slice(0, 2).map((v: any) => (
            <Link key={v.id} href={`/videos/${v.id}`} style={{ display: "flex", gap: 12 }}>
              <div style={{ width: 120, height: 72, borderRadius: 8, background: "var(--surface-variant)", flexShrink: 0, overflow: "hidden" }}>{v.thumbnail_url ? <img src={v.thumbnail_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : null}</div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{v.title}</div>
                <div style={{ fontSize: 11, color: "var(--on-surface-variant)", marginTop: 4 }}>Gaming Hub • 2.4M views</div>
              </div>
            </Link>
          ))}
        </div>
      </section>
      <BottomNav active="discover" />
    </div>
  );
}

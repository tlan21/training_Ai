"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/apiClient";
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
    <div style={{ maxWidth: 640, margin: "0 auto", padding: 12, minHeight: "100vh", background: "var(--bg-base)" }}>
      <h2>Khám phá</h2>
      <div style={{ display: "flex", gap: 8, overflowX: "auto", padding: "8px 0" }}>
        <button onClick={() => setActive("")} style={{ padding: "6px 12px", borderRadius: 9999, border: active === "" ? "none" : "1px solid var(--border)", background: active === "" ? "var(--accent)" : "transparent", color: "white", whiteSpace: "nowrap" }}>Tất cả</button>
        {cats.map((c) => (
          <button key={c.id} onClick={() => setActive(c.id)} style={{ padding: "6px 12px", borderRadius: 9999, border: active === c.id ? "none" : "1px solid var(--border)", background: active === c.id ? "var(--accent)" : "transparent", color: "white", whiteSpace: "nowrap" }}>{c.name}</button>
        ))}
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button onClick={() => setSort("newest")} style={{ padding: "6px 12px", borderRadius: 8, background: sort === "newest" ? "var(--bg-surface-2)" : "transparent", color: sort === "newest" ? "white" : "var(--text-secondary)", border: "1px solid var(--border)" }}>Mới nhất</button>
        <button onClick={() => setSort("trending")} style={{ padding: "6px 12px", borderRadius: 8, background: sort === "trending" ? "var(--bg-surface-2)" : "transparent", color: sort === "trending" ? "white" : "var(--text-secondary)", border: "1px solid var(--border)" }}>Thịnh hành</button>
        <Link href="/feed" style={{ marginLeft: "auto", color: "var(--info)", padding: 8 }}>Feed</Link>
      </div>
      <div style={{ display: "grid", gap: 12, marginTop: 12 }}>
        {videos.length === 0 ? <div style={{ color: "var(--text-secondary)", textAlign: "center", padding: 16 }}>Không có video</div> : null}
        {videos.map((v: any) => (
          <Link key={v.id} href={`/videos/${v.id}`} style={{ display: "flex", gap: 12, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 8 }}>
            <div style={{ width: 100, height: 70, borderRadius: 8, background: "var(--bg-surface-2)", overflow: "hidden" }}>{v.thumbnail_url ? <img src={v.thumbnail_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : null}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 13 }}>{v.title}</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{v.category?.name ?? ""}</div>
              {v.category && <span style={{ fontSize: 10, background: "var(--accent)", color: "white", padding: "2px 6px", borderRadius: 4 }}>AI Highlight</span>}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

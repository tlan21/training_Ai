"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/apiClient";
import { useAuthStore } from "@/stores/authStore";
export default function ProfilePage() {
  const [tab, setTab] = useState<"history" | "likes">("history");
  const [history, setHistory] = useState<any[]>([]);
  const [likes, setLikes] = useState<any[]>([]);
  const [me, setMe] = useState<any>(null);
  const router = useRouter();
  const logout = () => { apiClient.post("/api/auth/logout").catch(() => {}); useAuthStore.getState().logout(); router.push("/login"); };
  useEffect(() => {
    apiClient.get("/api/users/me").then((r) => setMe(r.data)).catch(() => {});
    apiClient.get("/api/users/me/history").then((r) => setHistory(r.data.items ?? [])).catch(() => {});
    apiClient.get("/api/users/me/likes").then((r) => setLikes(r.data.items ?? r.data ?? [])).catch(() => {});
  }, []);
  const items = tab === "history" ? history : likes;
  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: 12, minHeight: "100vh", background: "var(--bg-base)" }}>
      <div style={{ display: "flex", gap: 12, alignItems: "center", padding: 12, background: "var(--bg-surface)", borderRadius: 12 }}>
        <div style={{ width: 48, height: 48, borderRadius: 9999, background: "var(--accent)", display: "grid", placeItems: "center", fontWeight: 800 }}>{me?.username?.[0] ?? "U"}</div>
        <div>
          <div style={{ fontWeight: 700 }}>@{me?.username ?? "—"}</div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{me?.email ?? ""}</div>
        </div>
        <Link href="/feed" style={{ marginLeft: "auto", color: "var(--info)", fontSize: 13 }}>Feed</Link>
      </div>
      <Link href="/onboarding" style={{ display: "block", marginTop: 8, padding: 10, borderRadius: 8, border: "1px solid var(--border)", textAlign: "center", color: "var(--info)" }}>Sửa chủ đề yêu thích</Link>
      <div style={{ display: "flex", gap: 8, marginTop: 12, borderBottom: "1px solid var(--border)" }}>
        <button onClick={() => setTab("history")} style={{ padding: "8px 12px", borderBottom: tab === "history" ? "2px solid var(--accent)" : "2px solid transparent", background: "none", color: tab === "history" ? "white" : "var(--text-secondary)", fontWeight: 700 }}>Lịch sử</button>
        <button onClick={() => setTab("likes")} style={{ padding: "8px 12px", borderBottom: tab === "likes" ? "2px solid var(--accent)" : "2px solid transparent", background: "none", color: tab === "likes" ? "white" : "var(--text-secondary)", fontWeight: 700 }}>Đã thích</button>
      </div>
      <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
        {items.length === 0 ? <div style={{ color: "var(--text-secondary)", textAlign: "center", padding: 16 }}>{tab === "history" ? "Chưa xem clip nào" : "Chưa thích clip nào"}</div> : null}
        {items.map((it: any, i: number) => {
          const clip = it.clip ?? it;
          return (
            <Link key={i} href={`/videos/${clip.video_id ?? ""}?t=${clip.start_time ?? 0}`} style={{ display: "flex", gap: 12, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 8 }}>
              <div style={{ width: 80, height: 60, borderRadius: 8, background: "var(--bg-surface-2)", overflow: "hidden" }}>{clip.thumbnail_url ? <img src={clip.thumbnail_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : null}</div>
              <div><div style={{ fontWeight: 600, fontSize: 13 }}>{clip.title ?? clip.id}</div><div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{it.watched_at ?? ""}</div></div>
            </Link>
          );
        })}
      </div>
      <button onClick={logout} style={{ marginTop: 16, width: "100%", padding: 12, borderRadius: 8, border: "none", background: "var(--danger)", color: "white", fontWeight: 700 }}>Đăng xuất</button>
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/apiClient";
import { useAuthStore } from "@/stores/authStore";
import { BottomNav } from "@/components/BottomNav";
export default function ProfilePage() {
  const [tab, setTab] = useState<"liked" | "saved" | "history">("liked");
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
  return (
    <div style={{ minHeight: "100dvh", background: "var(--background)", paddingBottom: 72 }}>
      <header style={{ position: "sticky", top: 0, zIndex: 20, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", background: "var(--background)", borderBottom: "1px solid var(--outline-variant)", height: 56 }}>
        <span style={{ fontWeight: 800, fontSize: 18, color: "var(--primary)" }}>VidsAI</span>
        <div style={{ display: "flex", gap: 12 }}>
          <span className="material-symbols-outlined" style={{ color: "var(--on-surface-variant)" }}>history</span>
          <span className="material-symbols-outlined" style={{ color: "var(--on-surface-variant)" }}>notifications</span>
          <div style={{ width: 32, height: 32, borderRadius: 9999, background: "var(--primary-container)", display: "grid", placeItems: "center", overflow: "hidden" }}><span className="material-symbols-outlined" style={{ fontSize: 18, color: "var(--on-primary-container)" }}>person</span></div>
        </div>
      </header>
      <div style={{ padding: "16px 16px 0", display: "flex", flexDirection: "column", gap: 8, alignItems: "center" }}>
        <div style={{ width: 64, height: 64, borderRadius: 9999, background: "var(--primary)", display: "grid", placeItems: "center", color: "white", fontWeight: 800, fontSize: 22 }}>{me?.username?.[0]?.toUpperCase() ?? "U"}</div>
        <div style={{ fontWeight: 800, fontSize: 16 }}>@{me?.username ?? "—"}</div>
        <div style={{ fontSize: 12, color: "var(--on-surface-variant)" }}>{me?.email ?? ""}</div>
        <Link href="/onboarding" style={{ marginTop: 8, padding: "8px 16px", borderRadius: 9999, border: "1px solid var(--outline-variant)", fontSize: 13, fontWeight: 600 }}>Sửa chủ đề yêu thích</Link>
      </div>
      <nav style={{ display: "flex", marginTop: 16, borderBottom: "1px solid var(--outline-variant)", padding: "0 16px", gap: 16, overflowX: "auto" as any }}>
        {(["liked", "saved", "history"] as const).map((id) => (
          <button key={id} onClick={() => setTab(id)} style={{ padding: "12px 0", borderBottom: tab === id ? "2px solid var(--primary)" : "2px solid transparent", color: tab === id ? "var(--primary)" : "var(--on-surface-variant)", fontWeight: tab === id ? 700 : 500, fontSize: 13, background: "none", borderTop: "none", borderLeft: "none", borderRight: "none", whiteSpace: "nowrap" as any }}>
            {id === "liked" ? "Đã thích" : id === "saved" ? "Đã lưu" : "Lịch sử"}
          </button>
        ))}
      </nav>
      <div style={{ padding: 16 }}>
        {tab === "liked" && (
          <div style={{ display: "grid", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Video đã thích</h3>
              <span style={{ fontSize: 11, color: "var(--on-surface-variant)" }}>{likes.length} video</span>
            </div>
            {likes.length === 0 ? <div style={{ color: "var(--on-surface-variant)", textAlign: "center", padding: 24 }}>Chưa thích video nào</div> : likes.map((it: any, i: number) => {
              const clip = it.clip ?? it;
              return (
                <div key={i} style={{ display: "flex", gap: 12 }}>
                  <div style={{ width: 140, height: 80, borderRadius: 12, background: "var(--surface-variant)", overflow: "hidden", flexShrink: 0, position: "relative" }}>
                    {clip.thumbnail_url ? <img src={clip.thumbnail_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : null}
                    <span style={{ position: "absolute", bottom: 4, right: 4, background: "rgba(0,0,0,0.65)", color: "white", fontSize: 10, padding: "2px 6px", borderRadius: 4 }}>12:45</span>
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{clip.title ?? clip.id}</div>
                    <div style={{ fontSize: 11, color: "var(--on-surface-variant)", marginTop: 4 }}>{it.watched_at ? new Date(it.watched_at).toLocaleDateString("vi-VN") : ""} • Đã thích</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {tab === "saved" && (
          <div style={{ textAlign: "center", padding: "40px 16px" }}>
            <div style={{ width: 96, height: 96, borderRadius: 9999, background: "rgba(99,14,212,0.08)", display: "grid", placeItems: "center", margin: "0 auto 16px" }}><span className="material-symbols-outlined" style={{ fontSize: 48, color: "rgba(99,14,212,0.2)", fontVariationSettings: "'FILL' 1" }}>bookmark</span></div>
            <h3 style={{ fontSize: 16, fontWeight: 700 }}>Bạn chưa lưu video nào</h3>
            <p style={{ fontSize: 13, color: "var(--on-surface-variant)", marginTop: 8, maxWidth: 320, marginLeft: "auto", marginRight: "auto" }}>Hãy lưu lại những nội dung thú vị để xem lại sau bất cứ khi nào bạn muốn.</p>
            <Link href="/discover" style={{ display: "inline-block", marginTop: 16, padding: "10px 20px", background: "var(--primary)", color: "white", borderRadius: 9999, fontWeight: 600, fontSize: 13 }}>Khám phá ngay</Link>
          </div>
        )}
        {tab === "history" && (
          <div style={{ display: "grid", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Gần đây</h3>
              <button style={{ color: "var(--primary)", fontWeight: 700, background: "none", border: "none", fontSize: 12 }}>Xóa tất cả</button>
            </div>
            {history.length === 0 ? <div style={{ color: "var(--on-surface-variant)", textAlign: "center", padding: 24 }}>Chưa có lịch sử</div> : history.map((it: any, i: number) => {
              const clip = it.clip ?? it;
              return (
                <div key={i} style={{ display: "flex", gap: 12 }}>
                  <div style={{ width: 100, height: 64, borderRadius: 8, background: "var(--surface-variant)", flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{clip.title ?? clip.id}</div>
                    <div style={{ fontSize: 11, color: "var(--on-surface-variant)" }}>Đã xem {it.watched_at ? new Date(it.watched_at).toLocaleDateString("vi-VN") : ""}</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
      <div style={{ padding: "16px 16px calc(16px + env(safe-area-inset-bottom))" }}>
        <button onClick={logout} style={{ width: "100%", padding: 12, borderRadius: 12, border: "none", background: "var(--error-container)", color: "var(--on-error-container)", fontWeight: 700 }}>Đăng xuất</button>
      </div>
      <BottomNav active="profile" />
    </div>
  );
}

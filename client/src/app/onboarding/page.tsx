"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/apiClient";
const thumbs: Record<string, string> = {
  "Bóng đá": "https://lh3.googleusercontent.com/aida-public/AB6AXuAO0F8yVkmpAS0JyDCjgz2z9Wn94H7JQdR3_Q09dklOECEsKQd_OfMBGqOrtAHSuY7KY3P9Pwe2hHaxq2ARdwOW_NgL0dZlbFyohtrfZmlxmKzd9flmLAUArnIxhysX6_3MC2l5yNctrHJNmc8kwieAeuUK4PR8WtUZD0K5W7PGRkSpaV1DOTk0zi2yVkrsRoXI36Dky_d3a9hrEVrIhut4NNPy0PxjTp54IkN72iRi78PxPNSCDjPr9_C6OKAo5-XiuFZt-0EvlGs",
};
export default function OnboardingPage() {
  const [cats, setCats] = useState<{ id: string; name: string }[]>([]);
  const [sel, setSel] = useState<string[]>([]);
  const router = useRouter();
  useEffect(() => { apiClient.get("/api/categories").then((r) => setCats(r.data)).catch(() => setCats([{ id: "cat_bongda", name: "Bóng đá" }, { id: "cat_canhac", name: "Ca nhạc" }, { id: "cat_tintuc", name: "Tin tức" }])); }, []);
  const toggle = (id: string) => setSel((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);
  const submit = async () => {
    if (sel.length < 3) return;
    try { await apiClient.put("/api/users/me/preferences", { category_ids: sel }); } catch {}
    router.push("/feed");
  };
  const progress = Math.min(40 + (sel.length / 3) * 20, 60);
  return (
    <div style={{ minHeight: "100vh", background: "#FAFAF9", paddingBottom: 100 }}>
      <div style={{ position: "fixed", top: 0, left: 0, width: "100%", height: 4, background: "#f4ece8", zIndex: 50 }}>
        <div style={{ height: "100%", background: "var(--primary)", width: `${progress}%`, transition: "width 0.5s" }} />
      </div>
      <header style={{ position: "sticky", top: 4, background: "rgba(255,248,245,0.85)", backdropFilter: "blur(12px)", padding: "24px 16px 16px", borderBottom: "1px solid rgba(204,195,216,0.3)", zIndex: 40 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
          <span className="material-symbols-outlined" style={{ color: "var(--on-surface-variant)", cursor: "pointer" }} onClick={() => router.back()}>arrow_back</span>
          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--primary)" }}>BƯỚC 2/5</span>
          <span style={{ width: 24 }} />
        </div>
        <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0, color: "var(--on-surface)" }}>Chào mừng bạn đến với VidsAI</h1>
        <p style={{ fontSize: 14, color: "var(--on-surface-variant)", marginTop: 4 }}>Chọn ít nhất 3 chủ đề bạn yêu thích để chúng tôi tối ưu hóa trải nghiệm của bạn.</p>
      </header>
      <main style={{ padding: "16px 16px 24px", maxWidth: 640, margin: "0 auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {cats.map((c) => {
            const active = sel.includes(c.id);
            return (
              <div key={c.id} onClick={() => toggle(c.id)} style={{ height: active ? 160 : 160, borderRadius: 12, overflow: "hidden", border: active ? "2px solid var(--primary)" : "1px solid var(--outline-variant)", background: active ? "#ede0ff" : "white", display: "flex", flexDirection: "column", cursor: "pointer", boxShadow: "0 1px 4px rgba(0,0,0,0.06)", transition: "all 0.2s" }}>
                <div style={{ flex: "2 1 0", overflow: "hidden", background: "#f4ece8" }}>
                  {thumbs[c.name] ? <img src={thumbs[c.name]} alt="" style={{ width: "100%", height: "100%", objectFit: "cover", opacity: active ? 1 : 0.85 }} /> : <div style={{ width: "100%", height: "100%", display: "grid", placeItems: "center", color: "var(--outline)", fontSize: 24 }}><span className="material-symbols-outlined">category</span></div>}
                </div>
                <div style={{ padding: 10, display: "flex", justifyContent: "space-between", alignItems: "center", background: "white" }}>
                  <span style={{ fontWeight: 700, fontSize: 13 }}>{c.name}</span>
                  <span className="material-symbols-outlined" style={{ fontSize: 18, color: "var(--primary)", opacity: active ? 1 : 0, transform: active ? "scale(1)" : "scale(0.5)", transition: "all 0.2s" }}>check_circle</span>
                </div>
              </div>
            );
          })}
        </div>
      </main>
      <div style={{ position: "fixed", bottom: 0, left: 0, width: "100%", background: "rgba(255,255,255,0.85)", backdropFilter: "blur(12px)", borderTop: "1px solid rgba(204,195,216,0.3)", padding: "16px 16px calc(16px + env(safe-area-inset-bottom))", zIndex: 50 }}>
        <div style={{ maxWidth: 640, margin: "0 auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12, fontSize: 11, fontWeight: 600 }}>
            <span style={{ color: "var(--on-surface-variant)" }}>Đã chọn: <span style={{ color: sel.length >= 3 ? "var(--secondary-container)" : "var(--primary)", fontWeight: 800 }}>{sel.length}</span>/3</span>
            <button onClick={() => router.push("/feed")} style={{ color: "var(--on-surface-variant)", textDecoration: "underline", background: "none", border: "none", fontSize: 11, cursor: "pointer" }}>Bỏ qua</button>
          </div>
          <button onClick={submit} disabled={sel.length < 3} style={{ width: "100%", height: 56, borderRadius: 9999, border: "none", background: sel.length >= 3 ? "var(--primary)" : "#7b7487", color: "white", fontWeight: 800, fontSize: 15, display: "flex", alignItems: "center", justifyContent: "center", gap: 8, opacity: sel.length < 3 ? 0.5 : 1, boxShadow: sel.length >= 3 ? "0 8px 24px rgba(99,14,212,0.2)" : "none" }}>
            Hoàn tất <span className="material-symbols-outlined" style={{ fontSize: 18 }}>chevron_right</span>
          </button>
        </div>
      </div>
    </div>
  );
}

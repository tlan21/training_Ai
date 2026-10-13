"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/apiClient";
export default function OnboardingPage() {
  const [cats, setCats] = useState<{ id: string; name: string }[]>([]);
  const [sel, setSel] = useState<string[]>([]);
  const router = useRouter();
  useEffect(() => { apiClient.get("/api/categories").then((r) => setCats(r.data)).catch(() => setCats([{ id: "cat_bongda", name: "Bóng đá" }, { id: "cat_canhac", name: "Ca nhạc" }])); }, []);
  const toggle = (id: string) => setSel((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);
  const submit = async () => {
    if (sel.length < 3) return;
    try { await apiClient.put("/api/users/me/preferences", { category_ids: sel }); } catch {}
    router.push("/feed");
  };
  return (
    <div style={{ minHeight: "100vh", padding: 16, background: "var(--bg-base)", maxWidth: 420, margin: "0 auto" }}>
      <h2>Chọn chủ đề bạn thích (tối thiểu 3)</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8, marginTop: 16 }}>
        {cats.map((c) => (
          <button key={c.id} onClick={() => toggle(c.id)} style={{ padding: 16, borderRadius: 12, border: sel.includes(c.id) ? "2px solid var(--accent)" : "1px solid var(--border)", background: sel.includes(c.id) ? "rgba(255,45,85,0.15)" : "var(--bg-surface)", color: "white", fontWeight: 600 }}>
            {c.name} {sel.includes(c.id) ? "✓" : ""}
          </button>
        ))}
      </div>
      <div style={{ marginTop: 12, color: "var(--text-secondary)", fontSize: 13 }}>Đã chọn: {sel.length}/3</div>
      <button onClick={submit} disabled={sel.length < 3} style={{ marginTop: 12, width: "100%", padding: 12, borderRadius: 8, border: "none", background: sel.length >= 3 ? "var(--accent)" : "var(--bg-surface-2)", color: "white", fontWeight: 700, opacity: sel.length < 3 ? 0.5 : 1 }}>Tiếp tục</button>
      <button onClick={() => router.push("/feed")} style={{ marginTop: 8, width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text-secondary)" }}>Bỏ qua</button>
    </div>
  );
}

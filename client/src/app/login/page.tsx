"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiClient } from "@/lib/apiClient";
import { useAuthStore } from "@/stores/authStore";
export default function LoginPage() {
  const [email, setEmail] = useState("client@test.local");
  const [password, setPassword] = useState("password123");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const submit = async () => {
    setErr(""); setLoading(true);
    try {
      const r = await apiClient.post("/api/auth/login", { email, password });
      setAuth({ accessToken: r.data.access_token, user: r.data.user });
      const prefs = r.data.user?.preferences ?? [];
      if (prefs.length < 3) router.push("/onboarding");
      else router.push("/feed");
    } catch (e: any) { setErr(e?.response?.data?.error?.message ?? e.message); }
    finally { setLoading(false); }
  };
  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 16, background: "var(--bg-base)" }}>
      <div style={{ width: "100%", maxWidth: 360, display: "grid", gap: 16 }}>
        <div style={{ textAlign: "center" }}><div style={{ fontSize: 28, fontWeight: 800 }}>VidsAI</div><div style={{ color: "var(--text-secondary)", fontSize: 13 }}>Xem highlight bằng AI</div></div>
        <input style={{ background: "var(--bg-surface-2)", border: "1px solid var(--border)", borderRadius: 8, padding: 12, color: "var(--text-primary)", width: "100%" }} placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input style={{ background: "var(--bg-surface-2)", border: "1px solid var(--border)", borderRadius: 8, padding: 12, color: "var(--text-primary)", width: "100%" }} type="password" placeholder="Mật khẩu" value={password} onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => e.key === "Enter" && submit()} />
        {err && <div style={{ background: "#450a0a", color: "#fecaca", padding: 10, borderRadius: 8, fontSize: 13 }}>{err}</div>}
        <button onClick={submit} disabled={loading} style={{ background: "var(--accent)", color: "white", padding: 12, borderRadius: 8, border: "none", fontWeight: 700, width: "100%" }}>{loading ? "Đang xử lý…" : "Đăng nhập"}</button>
        <div style={{ textAlign: "center", fontSize: 13, color: "var(--text-secondary)" }}>Chưa có tài khoản? <Link href="/register" style={{ color: "var(--accent)" }}>Đăng ký</Link></div>
      </div>
    </div>
  );
}

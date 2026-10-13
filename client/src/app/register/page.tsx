"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiClient } from "@/lib/apiClient";
import { useAuthStore } from "@/stores/authStore";
export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const submit = async () => {
    setErr("");
    if (!email.includes("@") || password.length < 8) { setErr("Email/password không hợp lệ"); return; }
    try {
      const r = await apiClient.post("/api/auth/register", { username, email, password });
      setAuth({ accessToken: r.data.access_token, user: r.data.user });
      router.push("/onboarding");
    } catch (e: any) { setErr(e?.response?.data?.error?.message ?? e.message); }
  };
  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 16, background: "var(--bg-base)" }}>
      <div style={{ width: "100%", maxWidth: 360, display: "grid", gap: 12 }}>
        <h2 style={{ textAlign: "center", fontSize: 22, fontWeight: 800 }}>Tạo tài khoản</h2>
        <input style={{ background: "var(--bg-surface-2)", border: "1px solid var(--border)", borderRadius: 8, padding: 12, color: "white", width: "100%" }} placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
        <input style={{ background: "var(--bg-surface-2)", border: "1px solid var(--border)", borderRadius: 8, padding: 12, color: "white", width: "100%" }} placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input style={{ background: "var(--bg-surface-2)", border: "1px solid var(--border)", borderRadius: 8, padding: 12, color: "white", width: "100%" }} type="password" placeholder="Mật khẩu ≥8" value={password} onChange={(e) => setPassword(e.target.value)} />
        {err && <div style={{ background: "#450a0a", color: "#fecaca", padding: 10, borderRadius: 8, fontSize: 13 }}>{err}</div>}
        <button onClick={submit} style={{ background: "var(--accent)", color: "white", padding: 12, borderRadius: 8, border: "none", fontWeight: 700 }}>Đăng ký</button>
        <div style={{ textAlign: "center", fontSize: 13, color: "var(--text-secondary)" }}>Đã có tài khoản? <Link href="/login" style={{ color: "var(--accent)" }}>Đăng nhập</Link></div>
      </div>
    </div>
  );
}

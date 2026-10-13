"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiClient } from "@/lib/apiClient";
import { useAuthStore } from "@/stores/authStore";
export default function LoginPage() {
  const [email, setEmail] = useState("client@test.local");
  const [password, setPassword] = useState("password123");
  const [show, setShow] = useState(false);
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
    <div style={{ minHeight: "100vh", background: "var(--background)", padding: "0 16px", display: "flex", flexDirection: "column" }}>
      <div style={{ position: "fixed", top: -96, left: -96, width: 256, height: 256, background: "rgba(99,14,212,0.08)", borderRadius: 9999, filter: "blur(40px)", pointerEvents: "none" }} />
      <header style={{ padding: "80px 0 48px", display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ width: 64, height: 64, background: "var(--primary-container)", borderRadius: 16, display: "grid", placeItems: "center", marginBottom: 16, boxShadow: "0 8px 24px rgba(99,14,212,0.2)" }}>
          <span className="material-symbols-outlined" style={{ fontSize: 32, color: "var(--on-primary-container)", fontVariationSettings: "'FILL' 1" }}>movie_filter</span>
        </div>
        <div style={{ fontSize: 24, fontWeight: 800, color: "var(--primary)" }}>VidsAI</div>
        <div style={{ fontSize: 13, color: "var(--on-surface-variant)", marginTop: 4 }}>Trí tuệ nhân tạo cho video của bạn</div>
      </header>
      <section style={{ maxWidth: 360, width: "100%", margin: "0 auto", display: "grid", gap: 16 }}>
        <div style={{ display: "grid", gap: 4 }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: "var(--on-surface-variant)", marginLeft: 4 }}>Email hoặc Số điện thoại</label>
          <div style={{ position: "relative" }}>
            <span className="material-symbols-outlined" style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--outline)", fontSize: 20 }}>person</span>
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@example.com" style={{ width: "100%", height: 56, paddingLeft: 44, paddingRight: 12, background: "var(--surface-container-lowest)", border: "1px solid var(--outline-variant)", borderRadius: 12, fontSize: 15, outline: "none" }} />
          </div>
        </div>
        <div style={{ display: "grid", gap: 4 }}>
          <div style={{ display: "flex", justifyContent: "space-between", padding: "0 4px" }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: "var(--on-surface-variant)" }}>Mật khẩu</label>
            <span style={{ fontSize: 11, color: "var(--primary)", cursor: "pointer" }}>Quên mật khẩu?</span>
          </div>
          <div style={{ position: "relative" }}>
            <span className="material-symbols-outlined" style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--outline)", fontSize: 20 }}>lock</span>
            <input type={show ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => e.key === "Enter" && submit()} placeholder="••••••••" style={{ width: "100%", height: 56, paddingLeft: 44, paddingRight: 44, background: "var(--surface-container-lowest)", border: "1px solid var(--outline-variant)", borderRadius: 12, fontSize: 15, outline: "none" }} />
            <button type="button" onClick={() => setShow((v) => !v)} style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "var(--outline)" }}>
              <span className="material-symbols-outlined" style={{ fontSize: 20 }}>{show ? "visibility_off" : "visibility"}</span>
            </button>
          </div>
        </div>
        {err && <div style={{ background: "var(--error-container)", color: "var(--on-error-container)", padding: 10, borderRadius: 8, fontSize: 13 }}>{err}</div>}
        <button onClick={submit} disabled={loading} style={{ width: "100%", height: 56, background: "var(--primary)", color: "var(--on-primary)", borderRadius: 12, border: "none", fontWeight: 700, fontSize: 15, display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
          {loading ? "Đang xử lý…" : <>Đăng nhập <span className="material-symbols-outlined" style={{ fontSize: 18 }}>arrow_forward</span></>}
        </button>
      </section>
      <footer style={{ padding: "40px 0 24px", textAlign: "center" }}>
        <div style={{ fontSize: 14, color: "var(--on-surface-variant)" }}>Chưa có tài khoản? <Link href="/register" style={{ color: "var(--primary)", fontWeight: 700 }}>Đăng ký ngay</Link></div>
        <div style={{ marginTop: 20, display: "flex", gap: 16, justifyContent: "center", fontSize: 11, opacity: 0.6 }}>
          <a href="#">Điều khoản</a><a href="#">Bảo mật</a><a href="#">Trợ giúp</a>
        </div>
      </footer>
    </div>
  );
}

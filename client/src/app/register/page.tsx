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
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const submit = async () => {
    setErr("");
    if (!email.includes("@") || password.length < 8) { setErr("Email/password không hợp lệ (≥8)"); return; }
    if (password !== confirm) { setErr("Mật khẩu xác nhận không khớp"); return; }
    try {
      const r = await apiClient.post("/api/auth/register", { username: username || email.split("@")[0], email, password });
      setAuth({ accessToken: r.data.access_token, user: r.data.user });
      router.push("/onboarding");
    } catch (e: any) { setErr(e?.response?.data?.error?.message ?? e.message); }
  };
  return (
    <div style={{ minHeight: "100vh", background: "var(--background)", display: "flex", flexDirection: "column", alignItems: "center", padding: "0 16px" }}>
      <div style={{ position: "fixed", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
        <div style={{ position: "absolute", top: -96, right: -96, width: 256, height: 256, background: "rgba(99,14,212,0.08)", borderRadius: 9999, filter: "blur(40px)" }} />
        <div style={{ position: "absolute", top: "50%", left: -128, width: 320, height: 320, background: "rgba(254,166,25,0.04)", borderRadius: 9999, filter: "blur(40px)" }} />
      </div>
      <main style={{ width: "100%", maxWidth: 480, display: "flex", flexDirection: "column", minHeight: "100vh", position: "relative" }}>
        <header style={{ padding: "32px 0 16px", display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{ width: 64, height: 64, borderRadius: 16, background: "var(--primary)", display: "grid", placeItems: "center", boxShadow: "0 8px 24px rgba(99,14,212,0.2)", transform: "rotate(3deg)" }}>
            <span className="material-symbols-outlined" style={{ fontSize: 40, color: "var(--on-primary)", fontVariationSettings: "'FILL' 1" }}>play_circle</span>
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: "var(--primary)", marginTop: 12 }}>VidsAI</h1>
        </header>
        <section style={{ flex: 1 }}>
          <div style={{ textAlign: "center", marginBottom: 20 }}>
            <h2 style={{ fontSize: 22, fontWeight: 700 }}>Tham gia VidsAI</h2>
            <p style={{ fontSize: 14, color: "var(--on-surface-variant)", marginTop: 4 }}>Khám phá sức mạnh của video AI ngay hôm nay.</p>
          </div>
          <div style={{ display: "grid", gap: 12 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: "var(--on-surface-variant)", marginLeft: 4 }}>Họ và tên</label>
            <div style={{ position: "relative" }}>
              <span className="material-symbols-outlined" style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--on-surface-variant)", opacity: 0.6, fontSize: 20 }}>person</span>
              <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Nguyễn Văn A" style={{ width: "100%", padding: "14px 14px 14px 44px", borderRadius: 12, border: "1px solid var(--outline-variant)", background: "var(--surface-container-lowest)", fontSize: 15, outline: "none" }} />
            </div>
            <label style={{ fontSize: 13, fontWeight: 600, color: "var(--on-surface-variant)", marginLeft: 4 }}>Email hoặc Số điện thoại</label>
            <div style={{ position: "relative" }}>
              <span className="material-symbols-outlined" style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--on-surface-variant)", opacity: 0.6, fontSize: 20 }}>alternate_email</span>
              <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email@vidsai.vn" style={{ width: "100%", padding: "14px 14px 14px 44px", borderRadius: 12, border: "1px solid var(--outline-variant)", background: "var(--surface-container-lowest)", fontSize: 15, outline: "none" }} />
            </div>
            <label style={{ fontSize: 13, fontWeight: 600, color: "var(--on-surface-variant)", marginLeft: 4 }}>Mật khẩu</label>
            <div style={{ position: "relative" }}>
              <span className="material-symbols-outlined" style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--on-surface-variant)", opacity: 0.6, fontSize: 20 }}>lock</span>
              <input type={show ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" style={{ width: "100%", padding: "14px 44px 14px 44px", borderRadius: 12, border: "1px solid var(--outline-variant)", background: "var(--surface-container-lowest)", fontSize: 15, outline: "none" }} />
              <button type="button" onClick={() => setShow((v) => !v)} style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "var(--on-surface-variant)" }}>
                <span className="material-symbols-outlined" style={{ fontSize: 20 }}>{show ? "visibility_off" : "visibility"}</span>
              </button>
            </div>
            <label style={{ fontSize: 13, fontWeight: 600, color: "var(--on-surface-variant)", marginLeft: 4 }}>Xác nhận mật khẩu</label>
            <div style={{ position: "relative" }}>
              <span className="material-symbols-outlined" style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--on-surface-variant)", opacity: 0.6, fontSize: 20 }}>verified_user</span>
              <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="••••••••" style={{ width: "100%", padding: "14px 14px 14px 44px", borderRadius: 12, border: "1px solid var(--outline-variant)", background: "var(--surface-container-lowest)", fontSize: 15, outline: "none" }} />
            </div>
            {err && <div style={{ background: "var(--error-container)", color: "var(--on-error-container)", padding: 10, borderRadius: 8, fontSize: 13 }}>{err}</div>}
            <button onClick={submit} style={{ width: "100%", padding: 14, background: "var(--primary)", color: "var(--on-primary)", borderRadius: 12, border: "none", fontWeight: 700, fontSize: 15, display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
              Đăng ký ngay <span className="material-symbols-outlined" style={{ fontSize: 18 }}>arrow_forward</span>
            </button>
          </div>
        </section>
        <footer style={{ padding: "20px 0 16px", display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
          <div style={{ fontSize: 14, color: "var(--on-surface-variant)" }}>Đã có tài khoản? <Link href="/login" style={{ color: "var(--primary)", fontWeight: 700 }}>Đăng nhập ngay</Link></div>
          <div style={{ fontSize: 11, color: "var(--on-surface-variant)", opacity: 0.6, textAlign: "center", maxWidth: 360 }}>Bằng cách đăng ký, bạn đồng ý với <a href="#" style={{ textDecoration: "underline" }}>Điều khoản</a> và <a href="#" style={{ textDecoration: "underline" }}>Chính sách bảo mật</a> của VidsAI.</div>
        </footer>
      </main>
    </div>
  );
}

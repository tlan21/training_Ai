"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { apiClient } from "@/lib/apiClient";
import "../login.css";
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [token, setToken] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const submit = async () => {
    setErr(""); setLoading(true);
    try {
      const r = await apiClient.post("/api/auth/forgot-password", { email });
      setToken(r.data.reset_token ?? "");
      setSent(true);
    } catch (e: any) { setErr(e?.response?.data?.error?.message ?? e.message); }
    finally { setLoading(false); }
  };
  return (
    <div style={{ minHeight: "100vh", background: "var(--background)", padding: "0 16px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 360, display: "grid", gap: 16, background: "white", border: "1px solid var(--outline-variant)", borderRadius: 16, padding: 20 }}>
        <h2 style={{ fontSize: 16, fontWeight: 800 }}>Quên mật khẩu</h2>
        <p style={{ fontSize: 13, color: "var(--on-surface-variant)" }}>Nhập email đã đăng ký — hệ thống sẽ tạo mã đặt lại (dev trả token để test, không cần email).</p>
        {!sent ? (
          <div style={{ display: "grid", gap: 12 }}>
            <label htmlFor="fp-email" style={{ fontSize: 11, fontWeight: 700, color: "var(--on-surface-variant)", letterSpacing: 1, textTransform: "uppercase" }}>Email</label>
            <div className="input-wrap">
              <span className="input-icon input-icon--left" aria-hidden><Icon name="mail" size={18} /></span>
              <input id="fp-email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@example.com" className="input input--with-left-icon login-input" />
            </div>
            {err && <div style={{ background: "var(--error-container)", color: "var(--on-error-container)", padding: 10, borderRadius: 8, fontSize: 13 }}>{err}</div>}
            <button onClick={submit} disabled={loading || !email.includes("@")} className="btn-primary" style={{ width: "100%", opacity: loading || !email.includes("@") ? 0.6 : 1 }}><span>{loading ? "Đang gửi…" : "Gửi mã đặt lại"}</span><Icon name="send" size={16} /></button>
            <Link href="/login" style={{ textAlign: "center", fontSize: 13, color: "var(--primary)" }}>← Về đăng nhập</Link>
          </div>
        ) : (
          <div style={{ display: "grid", gap: 12 }}>
            <div style={{ padding: 12, background: "var(--surface-container-low)", border: "1px solid var(--outline-variant)", borderRadius: 8, fontSize: 13 }}>
              Đã tạo mã cho <strong>{email}</strong>.
              {token ? (
                <div style={{ marginTop: 8, padding: 8, background: "white", border: "1px solid var(--outline-variant)", borderRadius: 8, wordBreak: "break-all" as any, fontFamily: "monospace", fontSize: 11 }}>
                  Token (dev): {token}
                </div>
              ) : <div style={{ marginTop: 8, color: "var(--on-surface-variant)" }}>Nếu email tồn tại, token đã được tạo (kiểm tra log server).</div>}
            </div>
            <button onClick={() => router.push(`/reset-password?token=${encodeURIComponent(token)}`)} disabled={!token} className="btn-primary" style={{ width: "100%", opacity: token ? 1 : 0.5 }}>Đặt lại mật khẩu →</button>
            <Link href="/login" style={{ textAlign: "center", fontSize: 13, color: "var(--primary)" }}>Về đăng nhập</Link>
          </div>
        )}
      </div>
    </div>
  );
}

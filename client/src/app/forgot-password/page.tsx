"use client";
import { useState } from "react";
import Link from "next/link";
import { Icon } from "@/components/Icon";
import "../login.css";
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  return (
    <div style={{ minHeight: "100vh", background: "var(--background)", padding: "0 16px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 360, display: "grid", gap: 16, background: "white", border: "1px solid var(--outline-variant)", borderRadius: 16, padding: 20 }}>
        <h2 style={{ fontSize: 16, fontWeight: 800 }}>Quên mật khẩu</h2>
        <p style={{ fontSize: 13, color: "var(--on-surface-variant)" }}>Nhập email để nhận hướng dẫn. Hiện chưa có gửi mail — vui lòng liên hệ quản trị viên.</p>
        {!sent ? (
          <div style={{ display: "grid", gap: 12 }}>
            <label htmlFor="fp-email" style={{ fontSize: 11, fontWeight: 700, color: "var(--on-surface-variant)", letterSpacing: 1, textTransform: "uppercase" }}>Email</label>
            <div className="input-wrap">
              <span className="input-icon input-icon--left" aria-hidden><Icon name="mail" size={18} /></span>
              <input id="fp-email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@example.com" className="input input--with-left-icon login-input" />
            </div>
            <button onClick={() => setSent(true)} className="btn-primary" style={{ width: "100%" }}><span>Gửi yêu cầu</span><Icon name="send" size={16} /></button>
            <Link href="/login" style={{ textAlign: "center", fontSize: 13, color: "var(--primary)" }}>← Về đăng nhập</Link>
          </div>
        ) : (
          <div style={{ padding: 12, background: "var(--surface-container-low)", border: "1px solid var(--outline-variant)", borderRadius: 8, fontSize: 13 }}>
            Đã ghi nhận cho <strong>{email || "—"}</strong>. Liên hệ quản trị viên để cấp lại mật khẩu.
            <div style={{ marginTop: 12 }}><Link href="/login" className="btn-primary" style={{ textDecoration: "none", padding: "8px 16px" }}>Về đăng nhập</Link></div>
          </div>
        )}
      </div>
    </div>
  );
}

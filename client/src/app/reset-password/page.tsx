"use client";
import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { apiClient } from "@/lib/apiClient";
import "../login.css";
function ResetForm() {
  const sp = useSearchParams();
  const initial = sp.get("token") ?? "";
  const [token, setToken] = useState(initial);
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState("");
  const [ok, setOk] = useState(false);
  const router = useRouter();
  const submit = async () => {
    setErr("");
    if (pw.length < 8) { setErr("Mật khẩu phải ≥8 ký tự"); return; }
    if (pw !== confirm) { setErr("Xác nhận không khớp"); return; }
    try {
      await apiClient.post("/api/auth/reset-password", { token, new_password: pw });
      setOk(true);
      setTimeout(() => router.push("/login"), 1500);
    } catch (e: any) { setErr(e?.response?.data?.error?.message ?? e.message); }
  };
  if (ok) return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 16, background: "var(--background)" }}>
      <div style={{ background: "white", border: "1px solid var(--outline-variant)", borderRadius: 16, padding: 24, maxWidth: 360, width: "100%", textAlign: "center" }}>
        <div style={{ color: "var(--primary)", fontWeight: 800 }}>Đã đặt lại mật khẩu!</div>
        <div style={{ fontSize: 13, color: "var(--on-surface-variant)", marginTop: 8 }}>Đang chuyển về đăng nhập…</div>
        <Link href="/login" style={{ display: "inline-block", marginTop: 12, color: "var(--primary)", fontWeight: 700 }}>Đăng nhập ngay</Link>
      </div>
    </div>
  );
  return (
    <div style={{ minHeight: "100vh", background: "var(--background)", padding: "0 16px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 360, display: "grid", gap: 16, background: "white", border: "1px solid var(--outline-variant)", borderRadius: 16, padding: 20 }}>
        <h2 style={{ fontSize: 16, fontWeight: 800 }}>Đặt lại mật khẩu</h2>
        <p style={{ fontSize: 13, color: "var(--on-surface-variant)" }}>Dán token từ bước quên mật khẩu và nhập mật khẩu mới.</p>
        <label style={{ fontSize: 11, fontWeight: 700, color: "var(--on-surface-variant)", letterSpacing: 1, textTransform: "uppercase" }}>Token</label>
        <div className="input-wrap">
          <span className="input-icon input-icon--left" aria-hidden><Icon name="verified_user" size={18} /></span>
          <input value={token} onChange={(e) => setToken(e.target.value)} placeholder="paste reset_token" className="input input--with-left-icon login-input" />
        </div>
        <label style={{ fontSize: 11, fontWeight: 700, color: "var(--on-surface-variant)", letterSpacing: 1, textTransform: "uppercase" }}>Mật khẩu mới</label>
        <div className="input-wrap">
          <span className="input-icon input-icon--left" aria-hidden><Icon name="lock" size={18} /></span>
          <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="≥8 ký tự" className="input input--with-left-icon login-input" />
        </div>
        <label style={{ fontSize: 11, fontWeight: 700, color: "var(--on-surface-variant)", letterSpacing: 1, textTransform: "uppercase" }}>Xác nhận</label>
        <div className="input-wrap">
          <span className="input-icon input-icon--left" aria-hidden><Icon name="verified_user" size={18} /></span>
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="••••••••" className="input input--with-left-icon login-input" />
        </div>
        {err && <div style={{ background: "var(--error-container)", color: "var(--on-error-container)", padding: 10, borderRadius: 8, fontSize: 13 }}>{err}</div>}
        <button onClick={submit} className="btn-primary" style={{ width: "100%" }}><span>Đặt lại mật khẩu</span><Icon name="arrow_forward" size={16} /></button>
        <Link href="/login" style={{ textAlign: "center", fontSize: 13, color: "var(--primary)" }}>← Về đăng nhập</Link>
      </div>
    </div>
  );
}
export default function ResetPasswordPage() {
  return <Suspense fallback={<div style={{ padding: 40, textAlign: "center" }}>Đang tải…</div>}><ResetForm /></Suspense>;
}

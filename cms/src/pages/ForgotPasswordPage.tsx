import { useState } from "react";
import { Link } from "react-router-dom";
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: 16 }}>
      <div className="glass-card" style={{ width: "100%", maxWidth: 460, padding: 32 }}>
        <h1 style={{ fontSize: 18, fontWeight: 800, color: "var(--primary)" }}>Quên mật khẩu</h1>
        <p style={{ fontSize: 13, color: "var(--on-surface-variant)", marginTop: 8 }}>Nhập email để nhận hướng dẫn đặt lại mật khẩu. Hiện chưa cấu hình gửi email — vui lòng liên hệ quản trị viên để cấp lại mật khẩu.</p>
        {!sent ? (
          <div style={{ display: "grid", gap: 12, marginTop: 16 }}>
            <label htmlFor="fp-email" style={{ fontSize: 11, fontWeight: 700, color: "var(--on-surface-variant)", letterSpacing: 1, textTransform: "uppercase" }}>Email</label>
            <div style={{ position: "relative" }}>
              <span className="material-symbols-outlined input-icon input-icon--left" aria-hidden>mail</span>
              <input id="fp-email" className="input input--with-left-icon" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin@stitch.ai" style={{ width: "100%" }} />
            </div>
            <button className="btn-primary" onClick={() => setSent(true)} style={{ width: "100%", justifyContent: "center" }}>
              <span>Gửi yêu cầu</span><span className="material-symbols-outlined" style={{ fontSize: 16 }} aria-hidden>send</span>
            </button>
            <Link to="/login" style={{ textAlign: "center", fontSize: 13, color: "var(--primary)", display: "block", marginTop: 4 }}>← Quay lại đăng nhập</Link>
          </div>
        ) : (
          <div style={{ marginTop: 16, padding: 12, background: "var(--surface-container-low)", border: "1px solid var(--outline-variant)", borderRadius: 8, fontSize: 13 }}>
            Đã ghi nhận yêu cầu cho <strong>{email || "—"}</strong>. Vui lòng liên hệ quản trị viên (admin) qua kênh nội bộ để được cấp lại mật khẩu. API reset qua email sẽ bổ sung khi có hạ tầng gửi mail.
            <div style={{ marginTop: 12 }}><Link to="/login" className="btn-primary" style={{ textDecoration: "none" }}>Về đăng nhập</Link></div>
          </div>
        )}
      </div>
    </div>
  );
}

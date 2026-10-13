import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLogin } from "../hooks/useAuth";

export default function LoginPage() {
  const [email, setEmail] = useState("admin@local");
  const [password, setPassword] = useState("admin123");
  const [showPw, setShowPw] = useState(false);
  const [remember, setRemember] = useState(false);
  const nav = useNavigate();
  const m = useLogin();
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const submit = () => {
    setErrMsg(null);
    m.mutate({ email, password }, {
      onSuccess: () => nav("/dashboard"),
      onError: (e: any) => setErrMsg(e?.apiError?.message || e?.response?.data?.error?.message || e.message || "Đăng nhập thất bại"),
    });
  };
  const quick = (type: "admin" | "editor") => {
    const u = type === "admin" ? "admin@local" : "editor@local";
    const p = type === "admin" ? "admin123" : "editor123";
    setEmail(u); setPassword(p);
    setTimeout(() => m.mutate({ email: u, password: p }, { onSuccess: () => nav("/dashboard"), onError: (e: any) => setErrMsg(e?.apiError?.message || e.message) }), 0);
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: 16 }}>
      <div className="glass-card" style={{ width: "100%", maxWidth: 460, padding: 32 }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginBottom: 32 }}>
          <div style={{ width: 48, height: 48, background: "var(--primary)", borderRadius: 12, display: "grid", placeItems: "center", marginBottom: 12, boxShadow: "0 4px 12px rgba(70,21,153,0.2)" }}>
            <span className="material-symbols-outlined" style={{ color: "white", fontSize: 24 }}>movie_filter</span>
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: "var(--primary)", letterSpacing: "-0.02em" }}>AI Video CMS</h1>
          <p style={{ fontSize: 10, color: "var(--on-surface-variant)", opacity: 0.8, letterSpacing: 2, textTransform: "uppercase", marginTop: 4 }}>Hệ thống biên tập & Quản lý video</p>
        </div>

        {errMsg && (
          <div style={{ marginBottom: 16, padding: 12, background: "var(--error-container)", border: "1px solid #f5c6cb", color: "var(--on-error-container)", fontSize: 13, borderRadius: 8, display: "flex", gap: 8 }}>
            <span className="material-symbols-outlined" style={{ fontSize: 18, color: "var(--error)" }}>error</span>
            <span>{errMsg}</span>
          </div>
        )}

        <div style={{ display: "grid", gap: 16 }}>
          <div>
            <label style={{ fontSize: 10, fontWeight: 700, color: "var(--on-surface-variant)", letterSpacing: 1, textTransform: "uppercase", display: "block", marginBottom: 6 }}>Tên đăng nhập hoặc Email</label>
            <div style={{ position: "relative" }}>
              <span className="material-symbols-outlined" style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--outline)", fontSize: 18 }}>person</span>
              <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin@stitch.ai hoặc admin" style={{ width: "100%", paddingLeft: 40 }} />
            </div>
          </div>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <label style={{ fontSize: 10, fontWeight: 700, color: "var(--on-surface-variant)", letterSpacing: 1, textTransform: "uppercase" }}>Mật khẩu</label>
              <span style={{ fontSize: 11, color: "var(--primary)", cursor: "pointer" }}>Quên mật khẩu?</span>
            </div>
            <div style={{ position: "relative" }}>
              <span className="material-symbols-outlined" style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--outline)", fontSize: 18 }}>lock</span>
              <input className="input" type={showPw ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => e.key === "Enter" && submit()} placeholder="••••••••" style={{ width: "100%", paddingLeft: 40, paddingRight: 40 }} />
              <button type="button" onClick={() => setShowPw((v) => !v)} style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "var(--outline)" }}>
                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>{showPw ? "visibility_off" : "visibility"}</span>
              </button>
            </div>
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--on-surface-variant)", cursor: "pointer" }}>
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} style={{ accentColor: "var(--primary)" }} />
            Duy trì đăng nhập trên thiết bị này
          </label>
          <button className="btn-primary" onClick={submit} disabled={m.isPending} style={{ width: "100%", padding: "12px 16px", fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
            {m.isPending ? <><span className="material-symbols-outlined" style={{ fontSize: 18, animation: "spin 1s linear infinite" }}>progress_activity</span> Đang xử lý...</> : "Đăng nhập"}
          </button>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "20px 0", color: "var(--outline-variant)" }}>
          <span style={{ flex: 1, height: 1, background: "currentColor" }} />
          <span style={{ fontSize: 10, letterSpacing: 1, textTransform: "uppercase", color: "var(--outline)" }}>Đăng nhập nhanh</span>
          <span style={{ flex: 1, height: 1, background: "currentColor" }} />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <button onClick={() => quick("admin")} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "10px 12px", background: "rgba(70,21,153,0.06)", border: "1px solid rgba(70,21,153,0.1)", borderRadius: 8, color: "var(--primary)", fontSize: 11, fontWeight: 600, cursor: "pointer" }}>
            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>shield_person</span> Quản trị viên
          </button>
          <button onClick={() => quick("editor")} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "10px 12px", background: "rgba(84,96,103,0.08)", border: "1px solid rgba(84,96,103,0.15)", borderRadius: 8, color: "var(--on-secondary-container)", fontSize: 11, fontWeight: 600, cursor: "pointer" }}>
            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>edit_document</span> Biên tập viên
          </button>
        </div>
      </div>
      <div style={{ marginTop: 24, fontSize: 11, color: "var(--on-surface-variant)", opacity: 0.6 }}>© 2026 AI Video CMS. Tất cả quyền được bảo lưu.</div>
    </div>
  );
}

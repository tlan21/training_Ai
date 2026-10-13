import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLogin } from "../hooks/useAuth";

export default function LoginPage() {
  const [email, setEmail] = useState("admin@local");
  const [password, setPassword] = useState("123456");
  const nav = useNavigate();
  const m = useLogin();
  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "var(--bg-base)" }}>
      <div className="card" style={{ padding: 32, width: 380 }}>
        <h1 style={{ textAlign: "center", marginBottom: 8 }}>AI Video CMS</h1>
        <p style={{ textAlign: "center", color: "var(--text-secondary)", fontSize: 13, marginBottom: 24 }}>Hệ thống biên tập</p>
        <div style={{ display: "grid", gap: 12 }}>
          <input className="input" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input className="input" type="password" placeholder="Mật khẩu" value={password} onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => e.key === "Enter" && m.mutate({ email, password }, { onSuccess: () => nav("/dashboard") })} />
          {m.isError && (
            <div style={{ color: "var(--danger)", fontSize: 13 }}>
              {(m.error as any)?.apiError?.message || (m.error as Error).message}
            </div>
          )}
          <button
            className="btn-primary"
            disabled={m.isPending}
            onClick={() => m.mutate({ email, password }, { onSuccess: () => nav("/dashboard") })}
          >
            {m.isPending ? "Đang đăng nhập…" : "Đăng nhập"}
          </button>
        </div>
      </div>
    </div>
  );
}

import { useState } from "react";
import { Link } from "react-router-dom";
import type { paths } from "../api-types";
import { apiClient, errorMessage } from "../lib/apiClient";
import { Icon } from "../components/common/Icon";
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      if (token) { await apiClient.post("/api/auth/reset-password", { token, new_password: password }); setDone(true); setToken(""); setPassword(""); setMessage("Đã đặt lại mật khẩu. Bạn có thể đăng nhập bằng mật khẩu mới."); }
      else { const result = await apiClient.post<paths["/api/auth/forgot-password"]["post"]["responses"][200]["content"]["application/json"]>("/api/auth/forgot-password", { email }); setMessage(result.data.message ?? "Yêu cầu đã được gửi."); setToken(result.data.reset_token ?? ""); }
    } catch (failure) { setError(errorMessage(failure)); } finally { setBusy(false); }
  };
  return <div className="auth-page"><form className="glass-card auth-card" onSubmit={submit}><div className="auth-logo"><span className="auth-brand-mark"><Icon name="movie_filter" /></span><h1>{token ? "Đặt lại mật khẩu" : "Quên mật khẩu"}</h1><p>AI Video CMS</p></div>{error && <div className="auth-error" role="alert"><Icon name="error" size={18} />{error}</div>}{message && <p className="auth-message" role="status">{message}</p>}{!done && <div className="auth-fields">{token ? <><label className="field" htmlFor="new-cms-password"><span>Mật khẩu mới</span><div className="input-wrap"><span className="input-icon input-icon--left"><Icon name="lock" size={18} /></span><input id="new-cms-password" className="input input--with-left-icon" type="password" value={password} minLength={8} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" required /></div></label><p className="micro">Đặt mật khẩu tối thiểu 8 ký tự.</p></> : <label className="field" htmlFor="fp-email"><span>Email</span><div className="input-wrap"><span className="input-icon input-icon--left"><Icon name="mail" size={18} /></span><input id="fp-email" className="input input--with-left-icon" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="admin@local" autoComplete="email" required /></div></label>}<button className="btn-primary" disabled={busy}>{busy ? "Đang xử lý…" : token ? "Đặt lại mật khẩu" : "Gửi yêu cầu"}<Icon name="send" size={18} /></button></div>}<Link className="auth-back" to="/login">Quay lại đăng nhập</Link></form></div>;
}

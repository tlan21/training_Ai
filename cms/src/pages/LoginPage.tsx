import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useLogin } from "../hooks/useAuth";
import { useAuthStore } from "../stores/authStore";
import { Icon } from "../components/common/Icon";
import { errorMessage } from "../lib/apiClient";
export default function LoginPage() {
  const [email, setEmail] = useState("admin@local");
  const [password, setPassword] = useState("admin123");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(localStorage.getItem("cms-remember") === "true");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const login = useLogin();
  const token = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);
  if (token && (user?.role === "admin" || user?.role === "editor")) return <Navigate to="/dashboard" replace />;
  const authenticate = (username: string, secret: string) => {
    setError(""); localStorage.setItem("cms-remember", remember ? "true" : "false");
    login.mutate({ email: username.trim() === "admin" ? "admin@local" : username.trim(), password: secret }, { onSuccess: () => navigate("/dashboard"), onError: (failure) => setError(errorMessage(failure)) });
  };
  return <div className="auth-page cms-login"><div className="glass-card auth-card"><div className="auth-logo"><span className="auth-brand-mark"><Icon name="movie_filter" filled /></span><h1>AI Video CMS</h1><p>Hệ thống biên tập & Quản lý video</p></div>{error && <div className="auth-error" role="alert"><Icon name="error" size={18} /><span>{error}</span></div>}
    <form className="auth-fields" onSubmit={(event) => { event.preventDefault(); authenticate(email, password); }}><div className="field"><label htmlFor="cms-email">Tên đăng nhập hoặc Email</label><div className="input-wrap"><span className="input-icon input-icon--left"><Icon name="person" size={18} /></span><input id="cms-email" className="input input--with-left-icon" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="admin@stitch.ai hoặc admin" autoComplete="username" required /></div></div><div className="field"><div className="login-label-row"><label htmlFor="cms-password">Mật khẩu</label><Link to="/forgot-password">Quên mật khẩu?</Link></div><div className="input-wrap"><span className="input-icon input-icon--left"><Icon name="lock" size={18} /></span><input id="cms-password" className="input input--with-left-icon input--with-right-icon" type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" placeholder="••••••••" required /><button type="button" className="input-icon input-icon--right input-icon--action" aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"} onClick={() => setShowPassword((value) => !value)}><Icon name={showPassword ? "visibility_off" : "visibility"} size={18} /></button></div></div><label className="remember-label"><input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} />Duy trì đăng nhập trên thiết bị này</label><button className="btn-primary" disabled={login.isPending}>{login.isPending ? <><Icon name="progress_activity" size={18} />Đang xử lý...</> : <>Đăng nhập</>}</button></form>
    <div className="login-divider"><span>Đăng nhập nhanh</span></div><div className="quick-logins"><button disabled={login.isPending} onClick={() => authenticate("admin@local", "admin123")}><Icon name="shield_person" size={14} />Quản trị viên</button><button disabled={login.isPending} onClick={() => { setEmail("editor@local"); setPassword(""); }}><Icon name="edit_document" size={14} />Biên tập viên</button></div>
  </div><p className="auth-footer">© 2026 AI Video CMS. Tất cả quyền được bảo lưu.</p></div>;
}

"use client";
import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AuthFrame, AuthField } from "@/components/AuthFrame";
import { Icon } from "@/components/Icon";
import { apiClient, errorMessage } from "@/lib/apiClient";
function ResetForm() {
    const sp = useSearchParams();
    const [token, setToken] = useState(sp.get("token") || "");
    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [show, setShow] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [done, setDone] = useState(false);
    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        if (password !== confirm) {
            setError("Mật khẩu xác nhận không khớp.");
            return;
        }
        setLoading(true);
        try {
            await apiClient.post("/api/auth/reset-password", { token, new_password: password });
            setDone(true);
        }
        catch (e) {
            setError(errorMessage(e));
        }
        finally {
            setLoading(false);
        }
    };
    return <AuthFrame mode="reset">{done ? <div className="auth-form"><p className="notice" role="status">Đã đặt lại mật khẩu thành công.</p><Link className="btn-primary" href="/login">Đăng nhập ngay</Link></div> : <form className="auth-form" onSubmit={submit}>
 <AuthField id="token" label="Mã khôi phục" icon="verified_user" required value={token} onChange={e => setToken(e.target.value)} placeholder="Mã đặt lại mật khẩu"/>
 <AuthField id="password" label="Mật khẩu mới" icon="lock" required minLength={8} autoComplete="new-password" type={show ? "text" : "password"} value={password} onChange={e => setPassword(e.target.value)} placeholder="Ít nhất 8 ký tự" action={<button type="button" className="input-icon input-icon--right input-icon--action" aria-label={show ? "Ẩn mật khẩu" : "Hiện mật khẩu"} onClick={() => setShow(!show)}><Icon name={show ? "visibility_off" : "visibility"} size={22}/></button>}/>
 <AuthField id="confirm" label="Xác nhận mật khẩu" icon="verified_user" required minLength={8} autoComplete="new-password" type="password" value={confirm} onChange={e => setConfirm(e.target.value)} placeholder="Nhập lại mật khẩu"/>
 {error && <p className="error-banner" role="alert">{error}</p>}<button className="btn-primary auth-submit" disabled={loading}>{loading ? "Đang cập nhật…" : "Đặt lại mật khẩu"}<Icon name="arrow_forward" size={18}/></button></form>}</AuthFrame>;
}
export default function ResetPasswordPage() { return <Suspense fallback={<div className="page-state">Đang tải…</div>}><ResetForm /></Suspense>; }

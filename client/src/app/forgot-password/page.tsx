"use client";
import { useState } from "react";
import Link from "next/link";
import type { paths } from "@/api-types";
import { AuthFrame, AuthField } from "@/components/AuthFrame";
import { Icon } from "@/components/Icon";
import { apiClient, errorMessage } from "@/lib/apiClient";
export default function ForgotPasswordPage() {
    const [email, setEmail] = useState("");
    const [token, setToken] = useState("");
    const [sent, setSent] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");
        try {
            const { data } = await apiClient.post<paths["/api/auth/forgot-password"]["post"]["responses"][200]["content"]["application/json"]>("/api/auth/forgot-password", { email: email.trim() });
            setToken(data.reset_token || "");
            setSent(true);
        }
        catch (e) {
            setError(errorMessage(e));
        }
        finally {
            setLoading(false);
        }
    };
    return <AuthFrame mode="forgot">{sent ? <div className="auth-form"><p className="notice" role="status">Nếu email đã đăng ký, mã khôi phục đã được tạo.</p>{token && <><p className="reset-code">Mã khôi phục (dev): <code>{token}</code></p><Link className="btn-primary" href={`/reset-password?token=${encodeURIComponent(token)}`}>Đặt lại mật khẩu<Icon name="arrow_forward" size={18}/></Link></>}</div> : <form className="auth-form" onSubmit={submit}><AuthField id="email" label="Email hoặc Số điện thoại" icon="alternate_email" desktopIcon="mail" type="email" required autoComplete="email" placeholder="example@gmail.com" desktopPlaceholder="username@email.com" value={email} onChange={e => setEmail(e.target.value)}/><p className="notice">Bản dev cung cấp mã khôi phục tại đây, không gửi email.</p>{error && <p className="error-banner" role="alert">{error}</p>}<button className="btn-primary auth-submit" disabled={loading}>{loading ? "Đang gửi…" : "Gửi yêu cầu"}<Icon name="send" size={18}/></button></form>}</AuthFrame>;
}

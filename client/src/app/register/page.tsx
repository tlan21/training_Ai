"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { AuthFrame, AuthField } from "@/components/AuthFrame";
import { Icon } from "@/components/Icon";
import { apiClient, errorMessage } from "@/lib/apiClient";
import { useAuthStore } from "@/stores/authStore";
import type { components } from "@/api-types";
export default function RegisterPage() {
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [show, setShow] = useState(false);
    const [terms, setTerms] = useState(false);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const router = useRouter();
    const ready = useAuthStore(s => s.ready);
    const query = useQueryClient();
    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!ready || loading)
            return;
        setError("");
        if (password !== confirm) {
            setError("Mật khẩu xác nhận không khớp.");
            return;
        }
        if (window.matchMedia("(min-width:1024px)").matches && !terms) {
            setError("Vui lòng đồng ý với điều khoản dịch vụ.");
            return;
        }
        setLoading(true);
        try {
            const { data } = await apiClient.post<components["schemas"]["AuthResponse"]>("/api/auth/register", { username: username.trim(), email: email.trim(), password });
            if (!data.access_token || !data.user?.id)
                throw new Error("Phản hồi đăng ký không hợp lệ.");
            query.clear();
            useAuthStore.getState().setAuth({ accessToken: data.access_token, user: data.user });
            router.push("/onboarding");
        }
        catch (e) {
            setError(errorMessage(e));
        }
        finally {
            setLoading(false);
        }
    };
    return <AuthFrame mode="register"><form className="auth-form" onSubmit={submit}>
    <AuthField id="username" label="Họ và tên" icon="person" required autoComplete="name" placeholder="Nguyễn Văn A" value={username} onChange={e => setUsername(e.target.value)}/>
    <AuthField id="email" label="Email hoặc Số điện thoại" icon="alternate_email" desktopIcon="mail" required autoComplete="email" type="email" placeholder="email@vidsai.vn" desktopPlaceholder="example@vidsai.com" value={email} onChange={e => setEmail(e.target.value)}/>
    <AuthField id="password" label="Mật khẩu" icon="lock" required autoComplete="new-password" minLength={6} type={show ? "text" : "password"} placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} action={<button type="button" className="input-icon input-icon--right input-icon--action" aria-label={show ? "Ẩn mật khẩu" : "Hiện mật khẩu"} onClick={() => setShow(!show)}><Icon name={show ? "visibility_off" : "visibility"} size={22}/></button>}/>
    <AuthField id="confirm" label="Xác nhận mật khẩu" icon="verified_user" desktopIcon="shield" required autoComplete="new-password" minLength={6} type="password" placeholder="••••••••" value={confirm} onChange={e => setConfirm(e.target.value)}/>
    <label className="terms desktop-only"><input type="checkbox" checked={terms} onChange={e => setTerms(e.target.checked)}/>Tôi đồng ý với Điều khoản dịch vụ và Chính sách bảo mật của VidsAI.</label>
    {error && <p className="error-banner" role="alert">{error}</p>}
    <button type="submit" className="btn-primary auth-submit" disabled={loading || !ready}>{loading ? "Đang tạo tài khoản…" : <><span className="mobile-only">Đăng ký ngay</span><span className="desktop-only">Đăng ký tài khoản</span></>}<span className="mobile-only"><Icon name="arrow_forward" size={20}/></span></button>
  </form></AuthFrame>;
}

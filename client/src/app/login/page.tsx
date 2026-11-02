"use client";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Link from "next/link";
import type { components } from "@/api-types";
import { AuthFrame, AuthField } from "@/components/AuthFrame";
import { Icon } from "@/components/Icon";
import { apiClient, errorMessage } from "@/lib/apiClient";
import { useAuthStore } from "@/stores/authStore";
export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [show, setShow] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [remember, setRemember] = useState(false);
    const router = useRouter();
    const ready = useAuthStore(s => s.ready);
    const query = useQueryClient();
    useEffect(() => { const stored = localStorage.getItem("client-remember-email"); if (stored) {
        setEmail(stored);
        setRemember(true);
    } }, []);
    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!ready || loading)
            return;
        setLoading(true);
        setError("");
        try {
            const { data } = await apiClient.post<components["schemas"]["AuthResponse"]>("/api/auth/login", { email: email.trim(), password });
            if (!data.access_token || !data.user?.id)
                throw new Error("Phản hồi đăng nhập không hợp lệ.");
            query.clear();
            useAuthStore.getState().setAuth({ accessToken: data.access_token, user: data.user });
            const { data: me } = await apiClient.get<components["schemas"]["UserMe"]>("/api/users/me");
            const token = useAuthStore.getState().accessToken;
            if (!token || useAuthStore.getState().user?.id !== data.user.id || me.id !== data.user.id) throw new Error("Phiên đăng nhập đã thay đổi.");
            useAuthStore.getState().setAuth({ accessToken: token, user: me });
            if (remember)
                localStorage.setItem("client-remember-email", email.trim());
            else
                localStorage.removeItem("client-remember-email");
            const skipped = sessionStorage.getItem(`onboarding-skipped-${me.id}`);
            router.push((me.preferences?.length || 0) >= 3 || skipped ? "/feed" : "/onboarding");
        }
        catch (e) {
            setError(errorMessage(e));
        }
        finally {
            setLoading(false);
        }
    };
    return <AuthFrame mode="login"><form onSubmit={submit} className="auth-form">
    <AuthField id="email" label="Email hoặc Số điện thoại" icon="person" type="email" autoComplete="email" required placeholder="name@example.com" desktopPlaceholder="example@email.com" value={email} onChange={e => setEmail(e.target.value)}/>
    <div className="login-password"><Link className="forgot-mobile mobile-only" href="/forgot-password">Quên mật khẩu?</Link><AuthField id="password" label="Mật khẩu" icon="lock" type={show ? "text" : "password"} autoComplete="current-password" required placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} action={<button className="input-icon input-icon--right input-icon--action" type="button" aria-label={show ? "Ẩn mật khẩu" : "Hiện mật khẩu"} onClick={() => setShow(!show)}><Icon name={show ? "visibility_off" : "visibility"} size={22}/></button>}/></div>
    <div className="remember-row desktop-only"><label><input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)}/>Ghi nhớ tôi</label><Link href="/forgot-password">Quên mật khẩu?</Link></div>
    {error && <p className="error-banner" role="alert">{error}</p>}
    <button type="submit" className="btn-primary auth-submit" disabled={loading || !ready}>{loading ? "Đang xử lý…" : "Đăng nhập"}{!loading && <span className="mobile-only"><Icon name="arrow_forward"/></span>}</button>
  </form><div className="quick-login desktop-only"><p>Đăng nhập nhanh</p><button className="btn-outline" disabled title="Đăng nhập nhanh chưa khả dụng"><Icon name="account_circle"/>Digital Creator</button></div></AuthFrame>;
}

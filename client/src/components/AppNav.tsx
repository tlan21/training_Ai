"use client";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Icon } from "@/components/Icon";
import { useAuthStore } from "@/stores/authStore";
import { apiClient, errorMessage } from "@/lib/apiClient";
export type NavTab = "home" | "discover" | "library" | "profile" | "search";
export function AppNav({ active, search = true, children }: {
    active: NavTab;
    search?: boolean;
    children?: React.ReactNode;
}) {
    const user = useAuthStore(s => s.user);
    const router = useRouter();
    const query = useQueryClient();
    const [q, setQ] = useState("");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    const logout = async () => {
        setBusy(true);
        setError("");
        try {
            await apiClient.post("/api/auth/logout");
            useAuthStore.getState().logout();
            query.clear();
            router.replace("/login");
        }
        catch (e) {
            setError(errorMessage(e));
        }
        finally {
            setBusy(false);
        }
    };
    return <header className="desktop-nav">
    <Link href="/feed" className="brand">VidsAI</Link>
    <nav aria-label="Điều hướng chính">{[["home", "Trang chủ", "/feed"], ["discover", "Khám phá", "/discover"], ["library", "Thư viện", "/profile?view=library"]].map(([id, label, href]) => <Link key={id} href={href} className={active === id || active === "search" && id === "discover" ? "active" : ""}>{label}</Link>)}</nav>
    {search && <form className="nav-search input-wrap" onSubmit={e => { e.preventDefault(); router.push(`/search?q=${encodeURIComponent(q)}`); }}>
      <span className="input-icon input-icon--left"><Icon name="search" size={22}/></span>
      <input aria-label="Tìm kiếm video" value={q} onChange={e => setQ(e.target.value)} placeholder="Tìm kiếm video, hình ảnh, hoặc khoảnh khắc..."/>
      <Link className="input-icon input-icon--right" aria-label="Tìm bằng hình ảnh" href="/search?tab=visual"><Icon name="image" size={22}/></Link>
    </form>}
    {children}
    <div className="nav-actions">
      <button className="icon-button" disabled title="Thông báo chưa có API" aria-label="Thông báo"><Icon name="notifications"/></button>
      <Link className="icon-button" aria-label="Lịch sử xem" href="/profile?view=library&tab=history"><Icon name="history"/></Link>
      <details className="account-menu">
        <summary aria-label="Tài khoản" className="avatar">{user?.username?.[0]?.toUpperCase() || <Icon name="person" size={20}/>}</summary>
        <div className="account-dropdown"><strong>{user?.username || "Tài khoản"}</strong><small>{user?.email}</small><Link href="/profile?view=account">Cá nhân</Link><Link href="/profile?view=library">Thư viện của tôi</Link><Link href="/onboarding">Sửa chủ đề yêu thích</Link>{error && <p role="alert">{error}</p>}<button onClick={logout} disabled={busy}><Icon name="logout" size={18}/>{busy ? "Đang đăng xuất…" : "Đăng xuất"}</button></div>
      </details>
    </div>
  </header>;
}
export function MobileHeader({ title = "VidsAI", back, center = false, children }: {
    title?: string;
    back?: boolean;
    center?: boolean;
    children?: React.ReactNode;
}) {
    return <header className={`mobile-header ${center ? "centered" : ""}`}>{back && <Link href="/feed" className="icon-button" aria-label="Về Trang chủ"><Icon name={center ? "arrow_back_ios" : "arrow_back"}/></Link>}<span className="mobile-brand">{title}</span><div className="mobile-header-actions">{children || <><Link href="/search" className="icon-button" aria-label="Tìm kiếm"><Icon name="search"/></Link><button className="icon-button" disabled title="Thông báo chưa có API" aria-label="Thông báo"><Icon name="notifications"/></button></>}</div></header>;
}

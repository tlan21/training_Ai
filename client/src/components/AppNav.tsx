"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "@/api-types";
import { Icon } from "@/components/Icon";
import { useAuthStore } from "@/stores/authStore";
import { apiClient, logoutSession, errorMessage } from "@/lib/apiClient";
import { formatTime } from "@/lib/content";
export type NavTab = "home" | "discover" | "library" | "profile" | "search";
export function AppNav({ active, search = true, variant = active, children }: {
    active: NavTab;
    search?: boolean;
    variant?: NavTab | "detail";
    children?: React.ReactNode;
}) {
    const user = useAuthStore(s => s.user);
    const router = useRouter();
    const query = useQueryClient();
    const [q, setQ] = useState("");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    // Inline suggestions (top 5 text matches); Enter still opens the full /search page.
    const ready = useAuthStore(s => s.ready);
    const [open, setOpen] = useState(false);
    const [term, setTerm] = useState("");
    useEffect(() => { const timer = setTimeout(() => setTerm(q.trim()), 300); return () => clearTimeout(timer); }, [q]);
    const suggest = useQuery({ queryKey: ["search-suggest", term], enabled: ready && search && term.length >= 2, queryFn: async ({ signal }) => (await apiClient.get<{ items?: components["schemas"]["TextSearchResult"][] }>("/api/search", { params: { q: term }, signal })).data });
    const suggestions = suggest.data?.items?.slice(0, 5) ?? [];
    const logout = async () => {
        setBusy(true);
        setError("");
        try {
            await logoutSession();
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
    return <header className={`desktop-nav nav-${variant}`}>
    <div className="nav-brand-group"><Link href="/feed" className="brand">VidsAI</Link>
    <nav aria-label="Điều hướng chính">{[["home", "Trang chủ", "/feed"], ["discover", "Khám phá", "/discover"], ["library", "Thư viện", "/profile?view=library"]].map(([id, label, href]) => <Link key={id} href={href} className={variant !== "detail" && (active === id || active === "search" && id === "discover") ? "active" : ""}>{label}</Link>)}</nav></div>
    {(search || children) && <div className="nav-search-shell">{search && <form className="nav-search input-wrap" onSubmit={e => { e.preventDefault(); router.push(`/search?q=${encodeURIComponent(q)}`); }}>
      <span className="input-icon input-icon--left"><Icon name="search" size={22}/></span>
      <input aria-label="Tìm kiếm video" value={q} onChange={e => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} onKeyDown={e => { if (e.key === "Escape") setOpen(false); }} aria-expanded={open && term.length >= 2} aria-controls="nav-suggest" placeholder={variant === "home" ? "Tìm kiếm video bằng hình ảnh hoặc văn bản..." : variant === "detail" ? "Tìm kiếm video hoặc nội dung AI..." : "Tìm kiếm video, hình ảnh, hoặc khoảnh khắc..."}/>
      {variant !== "detail" && <Link className="input-icon input-icon--right" aria-label="Tìm bằng hình ảnh" href="/search?tab=visual"><Icon name={variant === "home" ? "add_a_photo" : "image"} size={24}/></Link>}
      {open && term.length >= 2 && q.trim() === term && <div className="nav-suggest" id="nav-suggest" role="listbox" aria-label="Gợi ý tìm kiếm">{suggest.isPending ? <p>Đang tìm…</p> : suggest.error ? <p>Không tải được gợi ý.</p> : !suggestions.length ? <p>Không có kết quả phù hợp.</p> : suggestions.map((r, i) => <Link role="option" aria-selected={false} key={`${r.video_id}-${i}`} href={`/videos/${r.video_id}${r.timestamp != null ? `?t=${Math.floor(r.timestamp)}` : ""}`} onMouseDown={e => e.preventDefault()} onClick={() => setOpen(false)}><strong>{r.title || r.video_id}</strong>{r.matched_text && <small>{r.timestamp != null && `${formatTime(r.timestamp)} · `}{r.matched_text}</small>}</Link>)}<Link className="nav-suggest-all" href={`/search?q=${encodeURIComponent(term)}`} onMouseDown={e => e.preventDefault()} onClick={() => setOpen(false)}>Xem tất cả kết quả</Link></div>}
    </form>}
    {children}</div>}
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

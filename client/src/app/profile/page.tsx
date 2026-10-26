"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "@/api-types";
import { AppNav, MobileHeader } from "@/components/AppNav";
import { BottomNav } from "@/components/BottomNav";
import { Icon } from "@/components/Icon";
import { Thumbnail, PageState } from "@/components/Media";
import { useAuthStore } from "@/stores/authStore";
import { apiClient, errorMessage, logoutSession } from "@/lib/apiClient";
import { useClipPage, useHistory, useCategories, formatTime, formatDate, type Clip } from "@/lib/content";
const tabs = [{ id: "liked", mobile: "Đã thích", desktop: "Video đã thích", icon: "favorite" }, { id: "saved", mobile: "Đã lưu", desktop: "Danh sách xem sau", icon: "schedule" }, { id: "history", mobile: "Lịch sử", desktop: "Lịch sử xem", icon: "history" }] as const;
function Profile() {
    const sp = useSearchParams();
    const router = useRouter();
    const query = useQueryClient();
    const ready = useAuthStore(s => s.ready);
    const [tab, setTab] = useState<"liked" | "saved" | "history">(sp.get("tab") === "history" ? "history" : "liked");
    const [sort, setSort] = useState("recent");
    const [search, setSearch] = useState("");
    const likes = useClipPage("/api/users/me/likes");
    const history = useHistory();
    const categories = useCategories();
    const me = useQuery({ queryKey: ["me"], enabled: ready, queryFn: async () => (await apiClient.get<components["schemas"]["UserMe"]>("/api/users/me")).data });
    const [username, setUsername] = useState("");
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");
    const [saving, setSaving] = useState(false);
    const dialog = useRef<HTMLDialogElement>(null);
    const account = sp.get("view") === "account";
    useEffect(() => { if (sp.get("tab") === "history")
        setTab("history"); }, [sp]);
    useEffect(() => { if (account && !dialog.current?.open)
        dialog.current?.showModal();
    else if (!account && dialog.current?.open)
        dialog.current.close(); }, [account]);
    useEffect(() => { setUsername(me.data?.username || ""); }, [me.data?.username]);
    const closeAccount = () => router.replace("/profile?view=library");
    const saveProfile = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!username.trim()) {
            setError("Nhập họ và tên.");
            return;
        }
        setSaving(true);
        setError("");
        setMessage("");
        try {
            const { data } = await apiClient.put<components["schemas"]["User"]>("/api/users/me", { username: username.trim() });
            await query.invalidateQueries({ queryKey: ["me"] });
            useAuthStore.setState({ user: { ...useAuthStore.getState().user, ...data } });
            setMessage("Đã cập nhật hồ sơ.");
        }
        catch (e) {
            setError(errorMessage(e));
        }
        finally {
            setSaving(false);
        }
    };
    const logout = async () => {
        setSaving(true);
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
            setSaving(false);
        }
    };
    const changeTab = (value: typeof tab) => { setTab(value); setSearch(""); };
    // shortcut: saved-list reading has no endpoint; unlock it when the contract adds one.
    const liked = likes.data?.pages.flatMap(p => p.items || []) || [];
    const watched = history.data?.pages.flatMap(p => p.items || []) || [];
    const items: Clip[] = (tab === "history" ? watched.map(item => item.clip).filter((clip): clip is Clip => !!clip) : liked).filter(clip => clip.title?.toLocaleLowerCase("vi").includes(search.toLocaleLowerCase("vi")) || clip.id?.includes(search)).sort((a, b) => sort === "oldest" ? (a.created_at || "").localeCompare(b.created_at || "") : (b.created_at || "").localeCompare(a.created_at || ""));
    const activeQuery = tab === "history" ? history : likes;
    return <div className="content-page"><AppNav active={account ? "profile" : "library"} search={false}><div className="nav-search input-wrap"><span className="input-icon input-icon--left"><Icon name="search"/></span><input placeholder="Tìm kiếm trong thư viện..." aria-label="Tìm kiếm trong thư viện" value={search} onChange={e => setSearch(e.target.value)}/></div></AppNav>
 <MobileHeader><Link className="icon-button" href="/profile?view=library&tab=history" aria-label="Lịch sử xem"><Icon name="history"/></Link><button className="icon-button" disabled title="Thông báo chưa có API" aria-label="Thông báo"><Icon name="notifications"/></button><Link className="avatar" href="/profile?view=account" aria-label="Tài khoản">{me.data?.username?.[0]?.toUpperCase() || <Icon name="person" size={20}/>}</Link></MobileHeader>
 <nav className="library-tabs" aria-label="Thư viện">{tabs.map(item => <button key={item.id} className={tab === item.id ? "active" : ""} aria-pressed={tab === item.id} onClick={() => changeTab(item.id)}>{item.mobile}</button>)}</nav>
 <main className="library-layout"><aside className="library-sidebar"><h2>Thư viện</h2>{tabs.map(item => <button key={item.id} className={tab === item.id ? "active" : ""} aria-pressed={tab === item.id} onClick={() => changeTab(item.id)}><Icon name={item.icon} filled={tab === item.id}/>{item.desktop}</button>)}<div className="library-divider"/><div className="library-folders">DANH SÁCH CỦA BẠN<button className="icon-button" disabled title="Danh sách riêng chưa khả dụng" aria-label="Thêm danh sách"><Icon name="add" size={18}/></button></div><button disabled title="Danh sách riêng chưa khả dụng"><Icon name="folder"/>Học tập AI</button><button disabled title="Danh sách riêng chưa khả dụng"><Icon name="movie"/>Phim ngắn yêu thích</button><Link className="link" href="/onboarding" style={{ padding: 16 }}>Sửa chủ đề yêu thích</Link></aside>
 <section className="library-main">
  <div className="library-title"><div><h1>{tab === "liked" ? "Video đã thích" : tab === "history" ? "Gần đây" : "Video đã lưu"}</h1><p className="desktop-only">{tab === "saved" ? "Chưa có dữ liệu đồng bộ" : `${items.length} video lưu trữ trong danh sách này`}</p></div><span className="mobile-only">{tab !== "saved" && `${items.length} video`}</span>{tab !== "saved" && <select className="library-sort" aria-label="Sắp xếp thư viện" value={sort} onChange={e => setSort(e.target.value)}><option value="recent">Gần đây</option><option value="oldest">Cũ nhất</option><option disabled>Phổ biến nhất (chưa có dữ liệu)</option></select>}{tab === "history" && <button className="link mobile-only" disabled title="Xóa lịch sử chưa khả dụng">Xóa tất cả</button>}</div>
  {tab === "saved" ? <div className="empty-library"><div className="empty-icon"><Icon name="bookmark" size={48} filled/></div><h2>Danh sách đã lưu chưa khả dụng</h2><p>Hiện chưa thể xem lại danh sách đã lưu. Bạn vẫn có thể tiếp tục khám phá video.</p><Link href="/discover" className="btn-primary">Khám phá ngay</Link></div> : activeQuery.isPending || activeQuery.error || !items.length ? <PageState loading={activeQuery.isPending} error={activeQuery.error} empty={tab === "liked" ? "Chưa thích video nào." : "Chưa có lịch sử xem."} retry={() => activeQuery.refetch()}/> : <div className="library-grid">{items.map((clip, i) => <article className="library-card" key={`${clip.id}-${i}`}>
   <Link className="media-frame" href={`/videos/${clip.video_id}?clip=${clip.id}`} aria-label={clip.title || clip.id}><Thumbnail src={clip.thumbnail_url}/><time className="time-badge">{formatTime((clip.end_time || 0) - (clip.start_time || 0))}</time></Link>
   <div className="library-card-body"><div className="library-card-heading"><Link href={`/videos/${clip.video_id}?clip=${clip.id}`} style={{ minWidth: 0 }}><h3 className="line-clamp-2">{clip.title}</h3></Link><button className="icon-button" disabled title="Xóa khỏi thư viện chưa khả dụng" aria-label="Tùy chọn clip"><Icon name="more_vert" size={20}/></button></div><small>VidsAI · {formatDate(clip.created_at)}</small><div className="library-status"><Icon name={tab === "liked" ? "favorite" : "history"} size={14}/>{tab === "liked" ? "Đã thích" : `Đã xem ${formatDate(watched.find(item => item.clip?.id === clip.id)?.watched_at)}`}</div>{clip.average_score != null && <><div className="mini-heatmap"><div style={{ width: `${Math.max(0, Math.min(100, clip.average_score))}%` }}/></div><small className="desktop-only" style={{ fontSize: 10 }}>Khoảnh khắc nổi bật AI · {Math.round(clip.average_score)}/100</small></>}</div>
  </article>)}</div>}
  {tab !== "saved" && activeQuery.hasNextPage && <div className="load-more"><button className="btn-outline" disabled={activeQuery.isFetchingNextPage} onClick={() => activeQuery.fetchNextPage()}>Tải thêm</button></div>}
 </section></main>
 <dialog ref={dialog} className="account-dialog" onCancel={closeAccount} onClose={() => { if (account)
        closeAccount(); }}><header><h2>Cá nhân</h2><button className="icon-button" onClick={closeAccount} aria-label="Đóng hồ sơ"><Icon name="close"/></button></header>
 {me.isPending || me.error ? <PageState loading={me.isPending} error={me.error} retry={() => me.refetch()}/> : <><div className="profile-card"><span className="avatar">{me.data?.username?.[0]?.toUpperCase()}</span><strong>@{me.data?.username}</strong><small>{me.data?.email}</small></div><form className="profile-form" onSubmit={saveProfile}><label htmlFor="username">Họ và tên</label><input className="input" id="username" value={username} onChange={e => setUsername(e.target.value)} required/><button className="btn-primary" disabled={saving}>{saving ? "Đang lưu…" : "Lưu thay đổi"}</button></form>
 <div className="profile-topics"><h3>Chủ đề yêu thích</h3><div className="profile-preferences">{me.data?.preferences?.map(id => <span className="pill" key={id}>{categories.data?.find(c => c.id === id)?.name || id}</span>)}</div><Link className="link" href="/onboarding">Sửa chủ đề yêu thích</Link></div></>}
 {error && <p className="error-banner" role="alert">{error}</p>}{message && <p className="notice" role="status">{message}</p>}<button className="profile-logout" onClick={logout} disabled={saving}><Icon name="logout" size={20}/>Đăng xuất</button></dialog>
 <BottomNav active={account ? "profile" : "library"}/></div>;
}
export default function ProfilePage() { return <Suspense fallback={<PageState loading/>}><Profile /></Suspense>; }

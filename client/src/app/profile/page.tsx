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
import { listErrorMessage, useHistoryActions, useListActions, useListItems, useLists, useToggleMark } from "@/lib/library";
import { ListPicker } from "@/components/Library";
import { NotificationBell } from "@/components/NotificationBell";
const tabs = [{ id: "liked", mobile: "Đã thích", desktop: "Video đã thích", icon: "favorite" }, { id: "saved", mobile: "Xem sau", desktop: "Danh sách xem sau", icon: "schedule" }, { id: "history", mobile: "Lịch sử", desktop: "Lịch sử xem", icon: "history" }, { id: "lists", mobile: "Danh sách", desktop: "Danh sách của tôi", icon: "playlist_play" }] as const;
type Tab = typeof tabs[number]["id"];
const tabFrom = (value: string | null): Tab => tabs.some(t => t.id === value) ? value as Tab : "liked";
function Profile() {
    const sp = useSearchParams();
    const router = useRouter();
    const query = useQueryClient();
    const ready = useAuthStore(s => s.ready);
    const [tab, setTab] = useState<Tab>(tabFrom(sp.get("tab")));
    const listId = sp.get("list");
    const [sort, setSort] = useState("recent");
    const [search, setSearch] = useState("");
    const [listClip, setListClip] = useState<string | null>(null);
    const [notice, setNotice] = useState("");
    const likes = useClipPage("/api/users/me/likes");
    const saved = useClipPage("/api/users/me/saved");
    const history = useHistory();
    const lists = useLists();
    const listItems = useListItems(listId);
    const listActions = useListActions();
    const historyActions = useHistoryActions();
    const unlike = useToggleMark("likes");
    const unsave = useToggleMark("saved");
    const categories = useCategories();
    const me = useQuery({ queryKey: ["me"], enabled: ready, queryFn: async () => (await apiClient.get<components["schemas"]["UserMe"]>("/api/users/me")).data });
    const [username, setUsername] = useState("");
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");
    const [saving, setSaving] = useState(false);
    const dialog = useRef<HTMLDialogElement>(null);
    const account = sp.get("view") === "account";
    useEffect(() => { if (sp.get("tab"))
        setTab(tabFrom(sp.get("tab"))); }, [sp]);
    useEffect(() => { if (!notice)
        return; const timer = setTimeout(() => setNotice(""), 4000); return () => clearTimeout(timer); }, [notice]);
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
    const changeTab = (value: Tab) => { setTab(value); setSearch(""); if (listId) router.replace(`/profile?view=library&tab=${value}`); };
    const openList = (id: string) => { setSearch(""); router.replace(`/profile?view=library&list=${id}`); };
    const pages = (q: { data?: { pages: { items?: Clip[] }[] } }) => q.data?.pages.flatMap(p => p.items || []) || [];
    const watched = history.data?.pages.flatMap(p => p.items || []) || [];
    const current = listId ? lists.data?.find(l => l.id === listId) : undefined;
    // "recent" keeps the server order (newest liked / saved / watched / added first); "oldest" reverses it.
    const source: Clip[] = listId ? pages(listItems) : tab === "history" ? watched.map(item => item.clip).filter((clip): clip is Clip => !!clip) : tab === "saved" ? pages(saved) : pages(likes);
    const filtered = source.filter(clip => clip.title?.toLocaleLowerCase("vi").includes(search.toLocaleLowerCase("vi")) || clip.id?.includes(search));
    const items = sort === "oldest" ? [...filtered].reverse() : filtered;
    const activeQuery = listId ? listItems : tab === "history" ? history : tab === "saved" ? saved : likes;
    const run = async (fn: () => Promise<unknown>, done?: string) => {
        try { await fn(); if (done) setNotice(done); } catch (e) { setNotice(listErrorMessage(e)); }
    };
    const createList = () => { const name = window.prompt("Tên danh sách mới (1–60 ký tự)"); if (name?.trim()) void run(async () => openList((await listActions.create(name)).id), "Đã tạo danh sách."); };
    const renameList = () => { if (!current) return; const name = window.prompt("Đổi tên danh sách", current.name); if (name?.trim() && name.trim() !== current.name) void run(() => listActions.rename(current.id, name), "Đã đổi tên danh sách."); };
    const deleteList = () => { if (current && window.confirm(`Xóa danh sách "${current.name}"? Clip không bị xóa.`)) void run(async () => { await listActions.remove(current.id); router.replace("/profile?view=library&tab=lists"); }, "Đã xóa danh sách."); };
    const clearHistory = () => { if (window.confirm("Xóa toàn bộ lịch sử xem? Video sẽ hiện lại nếu bạn xem lại.")) void run(historyActions.clear, "Đã xóa lịch sử xem."); };
    const removeLabel = listId ? "Bỏ khỏi danh sách" : tab === "liked" ? "Bỏ thích" : tab === "saved" ? "Bỏ khỏi Xem sau" : "Xóa khỏi lịch sử";
    const removeClip = (clipId: string) => void run(() => listId ? listActions.setMember(listId, clipId, false) : tab === "liked" ? unlike.mutateAsync({ clipId, on: false }) : tab === "saved" ? unsave.mutateAsync({ clipId, on: false }) : historyActions.remove(clipId), `Đã ${removeLabel.toLocaleLowerCase("vi")}.`);
    const title = listId ? current?.name || "Danh sách" : tabs.find(t => t.id === tab)?.desktop;
    const emptyText = listId ? "Danh sách này chưa có clip." : tab === "liked" ? "Chưa thích video nào." : tab === "saved" ? "Chưa có video trong Xem sau." : "Chưa có lịch sử xem.";
    const showLists = !listId && tab === "lists";
    return <div className="content-page"><AppNav active={account ? "profile" : "library"} search={false}><div className="nav-search input-wrap"><span className="input-icon input-icon--left"><Icon name="search"/></span><input placeholder="Tìm kiếm video hoặc nội dung..." aria-label="Tìm kiếm trong thư viện" value={search} onChange={e => setSearch(e.target.value)}/></div></AppNav>
 <MobileHeader><Link className="icon-button" href="/profile?view=library&tab=history" aria-label="Lịch sử xem"><Icon name="history"/></Link><NotificationBell/><Link className="avatar" href="/profile?view=account" aria-label="Tài khoản">{me.data?.username?.[0]?.toUpperCase() || <Icon name="person" size={20}/>}</Link></MobileHeader>
 <nav className="library-tabs" aria-label="Thư viện">{tabs.map(item => <button key={item.id} className={!listId && tab === item.id ? "active" : ""} aria-pressed={!listId && tab === item.id} onClick={() => changeTab(item.id)}>{item.mobile}</button>)}</nav>
 <main className="library-layout"><aside className="library-sidebar"><h2>Thư viện</h2>{tabs.filter(t => t.id !== "lists").map(item => <button key={item.id} className={!listId && tab === item.id ? "active" : ""} aria-pressed={!listId && tab === item.id} onClick={() => changeTab(item.id)}><Icon name={item.icon} filled={!listId && tab === item.id}/>{item.desktop}</button>)}<div className="library-divider"/><div className="library-folders">DANH SÁCH CỦA BẠN<button className="icon-button" onClick={createList} aria-label="Thêm danh sách"><Icon name="add" size={18}/></button></div>
  {lists.isPending ? <p className="library-folders-empty">Đang tải…</p> : lists.error ? <p className="library-folders-empty">{errorMessage(lists.error)}</p> : !lists.data?.length ? <p className="library-folders-empty">Chưa có danh sách</p> : lists.data.map(list => <button key={list.id} className={listId === list.id ? "active" : ""} aria-pressed={listId === list.id} onClick={() => openList(list.id)}><Icon name="playlist_play" filled={listId === list.id}/><span className="line-clamp-1">{list.name}</span><small className="library-folder-count">{list.item_count}</small></button>)}
  <Link className="link" href="/onboarding" style={{ padding: 16 }}>Sửa chủ đề yêu thích</Link></aside>
 <section className="library-main">
  <div className="library-title"><div><h1>{listId && <button className="icon-button" aria-label="Quay lại danh sách" onClick={() => changeTab("lists")}><Icon name="arrow_back" size={20}/></button>}{title}</h1><p className="desktop-only">{showLists ? `${lists.data?.length ?? 0} danh sách` : `${items.length} video trong mục này`}</p></div>
   {!showLists && <span className="mobile-only">{`${items.length} video`}</span>}
   {!showLists && <select className="library-sort" aria-label="Sắp xếp thư viện" value={sort} onChange={e => setSort(e.target.value)}><option value="recent">Gần đây</option><option value="oldest">Cũ nhất</option></select>}
   {listId && current && <div className="library-title-actions"><button className="btn-outline" onClick={renameList}><Icon name="edit" size={18}/>Đổi tên</button><button className="btn-outline" onClick={deleteList}><Icon name="delete" size={18}/>Xóa danh sách</button></div>}
   {showLists && <button className="btn-primary" onClick={createList}><Icon name="add" size={18}/>Danh sách mới</button>}
   {!listId && tab === "history" && !!watched.length && <button className="btn-outline" onClick={clearHistory}><Icon name="delete_sweep" size={18}/>Xóa toàn bộ lịch sử</button>}</div>
  {showLists ? (lists.isPending || lists.error || !lists.data?.length ? <PageState loading={lists.isPending} error={lists.error} empty="Chưa có danh sách. Tạo danh sách để gom các clip yêu thích." retry={() => lists.refetch()}/> : <div className="library-grid">{lists.data.map(list => <article className="library-card" key={list.id}>
   <button className="media-frame" onClick={() => openList(list.id)} aria-label={`Mở danh sách ${list.name}`}><Thumbnail src={list.cover_thumbnail_url}/><span className="time-badge">{list.item_count} clip</span></button>
   <div className="library-card-body"><button className="library-list-name" onClick={() => openList(list.id)}><h3 className="line-clamp-2">{list.name}</h3></button><small>Cập nhật {formatDate(list.updated_at)}</small></div>
  </article>)}</div>)
   : activeQuery.isPending || activeQuery.error || !items.length ? <PageState loading={activeQuery.isPending} error={activeQuery.error} empty={emptyText} retry={() => activeQuery.refetch()}/> : <div className="library-grid">{items.map((clip, i) => <article className="library-card" key={`${clip.id}-${i}`}>
   <Link className="media-frame" href={`/videos/${clip.video_id}?clip=${clip.id}`} aria-label={clip.title || clip.id}><Thumbnail src={clip.thumbnail_url}/><time className="time-badge">{formatTime((clip.end_time || 0) - (clip.start_time || 0))}</time></Link>
   <div className="library-card-body"><div className="library-card-heading"><Link href={`/videos/${clip.video_id}?clip=${clip.id}`} style={{ minWidth: 0 }}><h3 className="line-clamp-2">{clip.title}</h3></Link>
    <details className="card-menu"><summary className="icon-button" aria-label="Tùy chọn clip"><Icon name="more_vert" size={20}/></summary><div role="menu"><button role="menuitem" onClick={e => { e.currentTarget.closest("details")?.removeAttribute("open"); if (clip.id) removeClip(clip.id); }}><Icon name="remove_circle" size={18}/>{removeLabel}</button><button role="menuitem" onClick={e => { e.currentTarget.closest("details")?.removeAttribute("open"); setListClip(clip.id || null); }}><Icon name="playlist_add" size={18}/>Thêm vào danh sách</button></div></details></div>
    <small>VidsAI · {formatDate(clip.created_at)}</small><div className="library-status"><Icon name={listId ? "playlist_play" : tab === "liked" ? "favorite" : tab === "saved" ? "schedule" : "history"} size={14}/>{listId ? current?.name : tab === "liked" ? "Đã thích" : tab === "saved" ? "Xem sau" : `Đã xem ${formatDate(watched.find(item => item.clip?.id === clip.id)?.watched_at)}`}</div>{clip.average_score != null && <><div className="mini-heatmap"><div style={{ width: `${Math.max(0, Math.min(100, clip.average_score))}%` }}/></div><small className="desktop-only" style={{ fontSize: 10 }}>Khoảnh khắc nổi bật AI · {Math.round(clip.average_score)}/100</small></>}</div>
  </article>)}</div>}
  {!showLists && activeQuery.hasNextPage && <div className="load-more"><button className="btn-outline" disabled={activeQuery.isFetchingNextPage} onClick={() => activeQuery.fetchNextPage()}>Tải thêm</button></div>}
 </section></main>
 <ListPicker clipId={listClip} onClose={() => setListClip(null)}/>{notice && <div className="feed-toast" role="status">{notice}</div>}
 <dialog ref={dialog} className="account-dialog" onCancel={closeAccount} onClose={() => { if (account)
        closeAccount(); }}><header><h2>Cá nhân</h2><button className="icon-button" onClick={closeAccount} aria-label="Đóng hồ sơ"><Icon name="close"/></button></header>
 {me.isPending || me.error ? <PageState loading={me.isPending} error={me.error} retry={() => me.refetch()}/> : <><div className="profile-card"><span className="avatar">{me.data?.username?.[0]?.toUpperCase()}</span><strong>@{me.data?.username}</strong><small>{me.data?.email}</small></div><form className="profile-form" onSubmit={saveProfile}><label htmlFor="username">Họ và tên</label><input className="input" id="username" value={username} onChange={e => setUsername(e.target.value)} required/><button className="btn-primary" disabled={saving}>{saving ? "Đang lưu…" : "Lưu thay đổi"}</button></form>
 <div className="profile-topics"><h3>Chủ đề yêu thích</h3><div className="profile-preferences">{me.data?.preferences?.map(id => <span className="pill" key={id}>{categories.data?.find(c => c.id === id)?.name || id}</span>)}</div><Link className="link" href="/onboarding">Sửa chủ đề yêu thích</Link></div></>}
 {error && <p className="error-banner" role="alert">{error}</p>}{message && <p className="notice" role="status">{message}</p>}<button className="profile-logout" onClick={logout} disabled={saving}><Icon name="logout" size={20}/>Đăng xuất</button></dialog>
 <BottomNav active={account ? "profile" : "library"}/></div>;
}
export default function ProfilePage() { return <Suspense fallback={<PageState loading/>}><Profile /></Suspense>; }

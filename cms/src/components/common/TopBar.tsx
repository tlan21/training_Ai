import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useSystemHealth } from "../../hooks/useAuth";
import { Icon } from "./Icon";
import { AIModelList } from "./AIModelList";
import { useAlertsSeen, useMarkAlertsSeen, useNotificationCounts, useSettings } from "../../hooks/useCms";

// INT-59: in-app alerts only (no email/push); each kind follows its Settings > Thông báo switch.
function NotificationBell() {
  const [open, setOpen] = useState(false);
  const { pathname, search } = useLocation();
  const settings = useSettings();
  const counts = useNotificationCounts();
  const seen = useAlertsSeen();
  const markSeen = useMarkAlertsSeen();
  // The snapshot as it was when the panel opened: opening marks everything seen, but the panel must still show what was new.
  const [openedWith, setOpenedWith] = useState<{ failed_jobs: number; uncategorized_videos: number } | null>(null);
  useEffect(() => setOpen(false), [pathname, search]);
  const base = open && openedWith ? openedWith : { failed_jobs: seen.data?.failed_jobs ?? 0, uncategorized_videos: seen.data?.uncategorized_videos ?? 0 };
  const alerts = [
    { on: settings.data?.notify_failed_jobs ?? true, count: counts.data?.failed_jobs ?? 0, seen: base.failed_jobs, label: "Job xử lý lỗi", to: "/queue?status=failed", icon: "error" },
    { on: settings.data?.notify_uncategorized_videos ?? true, count: counts.data?.uncategorized_videos ?? 0, seen: base.uncategorized_videos, label: "Video đã xử lý chưa gán danh mục", to: "/videos?status=processed", icon: "category" },
  ].filter((alert) => alert.on);
  // INT-64: the badge shows only what grew since this account last opened the bell (server-side snapshot); the list keeps the live counts.
  const total = open || seen.isLoading ? 0 : alerts.reduce((sum, alert) => sum + Math.max(0, alert.count - alert.seen), 0);
  const toggle = () => {
    if (!open && counts.data) {
      setOpenedWith({ failed_jobs: seen.data?.failed_jobs ?? 0, uncategorized_videos: seen.data?.uncategorized_videos ?? 0 });
      markSeen.mutate({ failed_jobs: counts.data.failed_jobs ?? 0, uncategorized_videos: counts.data.uncategorized_videos ?? 0 });
    }
    setOpen((value) => !value);
  };
  return <div className="bell-wrap">
    <button className="icon-button" aria-label={total ? `Cảnh báo hệ thống (${total})` : "Cảnh báo hệ thống"} aria-expanded={open} onClick={toggle}><Icon name="notifications" />{total > 0 && <span className="bell-badge" aria-hidden="true">{total > 99 ? "99+" : total}</span>}</button>
    {open && <div className="health-popover bell-popover card" role="dialog" aria-label="Thông báo">
      <strong>Thông báo</strong>
      {!alerts.length ? <p className="muted">Đã tắt thông báo. Bật lại tại Cài đặt › Thông báo.</p>
        : counts.isError ? <p className="error-text">Không đọc được số liệu thông báo</p>
        : counts.isLoading ? <p className="muted">Đang tải…</p>
        : alerts.map((alert) => <Link key={alert.to} to={alert.to} className="bell-item"><Icon name={alert.icon} size={18} /><span>{alert.label}{alert.count > alert.seen && <small className="bell-new"> +{alert.count - alert.seen} mới</small>}</span><b>{alert.count}</b></Link>)}
      <button className="btn-text" onClick={() => setOpen(false)}>Đóng</button>
    </div>}
  </div>;
}
export function TopBar({ onMenu }: { onMenu: () => void }) {
  const { pathname } = useLocation();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [search, setSearch] = useState(params.get("q") ?? "");
  const [showHealth, setShowHealth] = useState(false);
  const health = useSystemHealth();
  useEffect(() => { setSearch(params.get("q") ?? ""); setShowHealth(false); }, [pathname, params]);
  const placeholders: Record<string, string> = { "/users": "Tìm tên hoặc email người dùng...", "/queue": "Tìm kiếm video trong hàng đợi...", "/videos": "Tìm theo tiêu đề video...", "/highlight": "Tìm kiếm video hoặc clips...", "/subtitles": "Tìm kiếm nội dung...", "/categories": "Tìm theo tên danh mục...", "/published": "Tìm theo tiêu đề video hoặc clip..." };
  const systemLast = ["/queue", "/subtitles", "/published"].includes(pathname);
  const variant = pathname === "/highlight" ? "pill" : pathname === "/categories" ? "soft" : pathname === "/queue" || pathname === "/published" ? "plain" : pathname === "/videos" ? "video" : "";
  const system = <button className={`system-button system-button-${variant}`} aria-label="Trạng thái hệ thống" onClick={() => setShowHealth((show) => !show)} aria-expanded={showHealth}>{pathname === "/highlight" ? <span className={`system-dot ${(health.isError || health.data?.ai_available === false) ? "is-error" : ""}`} /> : (pathname === "/queue" ? null : <Icon name={pathname === "/videos" ? "bolt" : pathname === "/subtitles" ? "cloud_done" : "dns"} size={pathname === "/subtitles" ? 14 : 18} />)}<span>Trạng thái hệ thống</span></button>;
  return <header className="cms-topbar" data-page={pathname.slice(1)}>
    <button className="icon-button mobile-menu" aria-label="Mở điều hướng" onClick={onMenu}><Icon name="menu" /></button>
    <form className="topbar-search input-wrap" onSubmit={(event) => { event.preventDefault(); const target = ["/queue", "/categories", "/published", "/users"].includes(pathname) ? pathname : "/videos"; navigate(`${target}?q=${encodeURIComponent(search)}`); }}>
      <span className="input-icon input-icon--left"><Icon name="search" size={18} /></span><input aria-label="Tìm kiếm CMS" className="input input--with-left-icon" placeholder={placeholders[pathname] ?? "Tìm kiếm video, metadata hoặc log..."} value={search} onChange={(event) => setSearch(event.target.value)} />
    </form>
    <div className="topbar-actions">
      {(pathname === "/queue" || pathname === "/published") && <Link to="/queue" className="btn-primary topbar-upload"><Icon name="cloud_upload" size={18} />{pathname === "/queue" ? "Tải lên" : "Tải lên video"}</Link>}
      {!systemLast && system}
      <NotificationBell />
      <Link to="/dashboard" className="icon-button" aria-label="Tổng quan hệ thống"><Icon name="analytics" /></Link>
      {systemLast && system}
      {pathname === "/dashboard" && <span className="topbar-avatar" aria-label="Tài khoản CMS"><Icon name="person" size={20} /></span>}
    </div>
    {showHealth && <div className="health-popover card"><strong>Trạng thái hệ thống</strong><p className={(health.isError || health.data?.ai_available === false) ? "error-text" : "muted"}>{(health.isError || health.data?.ai_available === false) ? "Không kết nối được inference" : health.isLoading ? "Đang tải…" : `${health.data?.models_loaded?.length ?? 0}/6 model đã nạp`}</p><AIModelList models={health.data?.ai_models} /><p>GPU: {health.data?.gpu_util ?? "—"}% · VRAM: {health.data?.gpu_vram_used ?? "—"} GB</p><p>Hàng đợi: {health.data?.queue_depth ?? "—"}</p><button className="btn-text" onClick={() => setShowHealth(false)}>Đóng</button></div>}
  </header>;
}

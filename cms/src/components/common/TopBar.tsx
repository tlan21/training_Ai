import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useSystemHealth } from "../../hooks/useAuth";
import { Icon } from "./Icon";
export function TopBar({ onMenu }: { onMenu: () => void }) {
  const { pathname } = useLocation();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [search, setSearch] = useState(params.get("q") ?? "");
  const [showHealth, setShowHealth] = useState(false);
  const health = useSystemHealth();
  useEffect(() => { setSearch(params.get("q") ?? ""); setShowHealth(false); }, [pathname, params]);
  const placeholders: Record<string, string> = { "/queue": "Tìm kiếm video trong hàng đợi...", "/videos": "Tìm kiếm video, thẻ hoặc người tạo...", "/highlight": "Tìm kiếm video hoặc clips...", "/subtitles": "Tìm kiếm nội dung...", "/categories": "Tìm kiếm danh mục, video...", "/published": "Tìm kiếm video, thẻ, hoặc biên tập viên..." };
  const systemLast = ["/queue", "/subtitles", "/published"].includes(pathname);
  const variant = pathname === "/highlight" ? "pill" : pathname === "/categories" ? "soft" : pathname === "/queue" || pathname === "/published" ? "plain" : pathname === "/videos" ? "video" : "";
  const system = <button className={`system-button system-button-${variant}`} aria-label="Trạng thái hệ thống" onClick={() => setShowHealth((show) => !show)} aria-expanded={showHealth}>{pathname === "/highlight" ? <span className={`system-dot ${health.isError ? "is-error" : ""}`} /> : <Icon name={pathname === "/videos" ? "bolt" : "dns"} size={18} />}<span>Trạng thái hệ thống</span></button>;
  return <header className="cms-topbar" data-page={pathname.slice(1)}>
    <button className="icon-button mobile-menu" aria-label="Mở điều hướng" onClick={onMenu}><Icon name="menu" /></button>
    <form className="topbar-search input-wrap" onSubmit={(event) => { event.preventDefault(); const target = ["/queue", "/categories", "/published"].includes(pathname) ? pathname : "/videos"; navigate(`${target}?q=${encodeURIComponent(search)}`); }}>
      <span className="input-icon input-icon--left"><Icon name="search" size={18} /></span><input aria-label="Tìm kiếm CMS" className="input input--with-left-icon" placeholder={placeholders[pathname] ?? "Tìm kiếm video, metadata hoặc log..."} value={search} onChange={(event) => setSearch(event.target.value)} />
    </form>
    <div className="topbar-actions">
      {(pathname === "/queue" || pathname === "/published") && <Link to="/queue" className="btn-primary topbar-upload"><Icon name="cloud_upload" size={18} />{pathname === "/queue" ? "Tải lên" : "Tải lên video"}</Link>}
      {!systemLast && system}
      <Link to="/queue?status=failed" className="icon-button" aria-label="Cảnh báo hệ thống"><Icon name="notifications" /></Link>
      <Link to="/dashboard" className="icon-button" aria-label="Tổng quan hệ thống"><Icon name="analytics" /></Link>
      {systemLast && system}
      {pathname === "/dashboard" && <span className="topbar-avatar" aria-label="Tài khoản CMS"><Icon name="person" size={20} /></span>}
    </div>
    {showHealth && <div className="health-popover card"><strong>Trạng thái hệ thống</strong><p className={health.isError ? "error-text" : "muted"}>{health.isError ? "Không kết nối được inference" : health.isLoading ? "Đang tải…" : `${health.data?.models_loaded?.length ?? 0}/6 model đã nạp`}</p><p>GPU: {health.data?.gpu_util ?? "—"}% · VRAM: {health.data?.gpu_vram_used ?? "—"} GB</p><p>Hàng đợi: {health.data?.queue_depth ?? "—"}</p><button className="btn-text" onClick={() => setShowHealth(false)}>Đóng</button></div>}
  </header>;
}

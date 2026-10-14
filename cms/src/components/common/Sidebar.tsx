import { NavLink } from "react-router-dom";
import { useAuthStore } from "../../stores/authStore";
import { Icon } from "./Icon";
const items = [
  { to: "/dashboard", label: "Tổng quan", icon: "dashboard" },
  { to: "/videos", label: "Video", icon: "video_library" },
  { to: "/queue", label: "Hàng đợi xử lý", icon: "queue_play_next" },
  { to: "/highlight", label: "Highlight AI", icon: "auto_awesome" },
  { to: "/categories", label: "Danh mục", icon: "category" },
  { to: "/subtitles", label: "Phụ đề & Tóm tắt", icon: "closed_caption" },
  { to: "/published", label: "Nội dung đã xuất bản", icon: "publish" },
  { to: "/settings", label: "Cài đặt", icon: "settings", adminOnly: true },
  { to: "/users", label: "Người dùng", icon: "group", adminOnly: true },
];
export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const user = useAuthStore((s) => s.user);
  return <aside className={`cms-sidebar ${open ? "is-open" : ""}`} onKeyDown={(event) => { if (event.key === "Escape") onClose(); }}>
    <button className="icon-button sidebar-close" aria-label="Đóng menu CMS" onClick={onClose}><Icon name="close" /></button>
    <div className="sidebar-brand"><span className="brand-mark"><Icon name="movie_filter" filled /></span><div><h1>AI Video CMS</h1><p>Hệ thống biên tập</p></div></div>
    <nav aria-label="Điều hướng CMS" className="sidebar-nav">
      {items.filter((item) => !item.adminOnly || user?.role === "admin").map((item) => <NavLink key={item.to} to={item.to} onClick={onClose} className={({ isActive }) => `sidebar-link ${isActive ? "is-active" : ""} ${item.to === "/settings" ? "sidebar-divider" : ""}`}>{({ isActive }) => <><Icon name={item.icon} filled={isActive} /><span>{item.label}</span></>}</NavLink>)}
    </nav>
    <div className="sidebar-account"><div className="account-row"><span className="avatar"><Icon name="person" /></span><div className="min-zero"><strong>{user?.username ?? "Admin CMS"}</strong><p>{user?.role === "admin" ? "Quản trị viên" : "Biên tập viên"}</p></div></div><button className="logout-button" onClick={() => useAuthStore.getState().logout()}><Icon name="logout" size={16} />Đăng xuất</button></div>
  </aside>;
}

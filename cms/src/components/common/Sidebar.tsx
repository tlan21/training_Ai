import { NavLink } from "react-router-dom";
import { useAuthStore } from "../../stores/authStore";
const items = [
  { to: "/dashboard", label: "Tổng quan", icon: "dashboard" },
  { to: "/videos", label: "Video", icon: "video_library" },
  { to: "/queue", label: "Hàng đợi xử lý", icon: "queue_play_next" },
  { to: "/highlight", label: "Highlight AI", icon: "auto_awesome" },
  { to: "/categories", label: "Danh mục", icon: "category" },
  { to: "/subtitles", label: "Phụ đề & Tóm tắt", icon: "closed_caption" },
  { to: "/published", label: "Nội dung đã xuất bản", icon: "publish" },
  { to: "/settings", label: "Cài đặt", icon: "settings" },
  { to: "/users", label: "Người dùng", icon: "group", adminOnly: true },
];
export function Sidebar() {
  const role = useAuthStore((s) => s.user?.role);
  return (
    <aside style={{ width: 260, background: "var(--bg-surface)", borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", height: "100vh", position: "fixed", left: 0, top: 0 }}>
      <div style={{ padding: 16, display: "flex", gap: 8, alignItems: "center", borderBottom: "1px solid var(--border)" }}>
        <div style={{ width: 32, height: 32, background: "var(--primary)", borderRadius: 8, display: "grid", placeItems: "center" }}>
          <span className="material-symbols-outlined" style={{ color: "white" }}>movie_filter</span>
        </div>
        <div>
          <div style={{ fontWeight: 700, color: "var(--primary)" }}>AI Video CMS</div>
          <div style={{ fontSize: 10, letterSpacing: 1, color: "var(--text-muted)" }}>HỆ THỐNG BIÊN TẬP</div>
        </div>
      </div>
      <nav style={{ flex: 1, padding: 8, display: "grid", gap: 2, alignContent: "start", overflowY: "auto" }}>
        {items.filter((it) => !(it as any).adminOnly || role === "admin").map((it) => (
          <NavLink
            key={it.to}
            to={it.to}
            style={({ isActive }) => ({
              display: "flex", gap: 12, padding: "8px 12px", borderRadius: 8,
              background: isActive ? "var(--primary)" : "transparent",
              color: isActive ? "white" : "var(--text-secondary)",
            })}
          >
            <span className="material-symbols-outlined">{it.icon}</span>
            {it.label}
          </NavLink>
        ))}
      </nav>
      <div style={{ padding: 12, borderTop: "1px solid var(--border)" }}>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{useAuthStore((s) => s.user?.username) ?? "—"}</div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{role ?? "—"}</div>
        <button onClick={() => useAuthStore.getState().logout()} style={{ marginTop: 8, width: "100%" }} className="btn-primary">
          Đăng xuất
        </button>
      </div>
    </aside>
  );
}

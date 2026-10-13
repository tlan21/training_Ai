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
    <aside style={{ width: 260, background: "var(--surface)", borderRight: "1px solid var(--outline-variant)", display: "flex", flexDirection: "column", height: "100vh", position: "fixed", left: 0, top: 0, zIndex: 40 }}>
      <div style={{ padding: 16, display: "flex", gap: 8, alignItems: "center" }}>
        <div style={{ width: 32, height: 32, background: "var(--primary)", borderRadius: 8, display: "grid", placeItems: "center" }}>
          <span className="material-symbols-outlined" style={{ color: "var(--on-primary)", fontVariationSettings: "'FILL' 1" }}>movie_filter</span>
        </div>
        <div>
          <div style={{ fontWeight: 700, color: "var(--primary)", fontSize: 16, lineHeight: 1 }}>AI Video CMS</div>
          <div style={{ fontSize: 10, letterSpacing: 1, color: "var(--outline)", textTransform: "uppercase", marginTop: 2 }}>Hệ thống biên tập</div>
        </div>
      </div>
      <nav style={{ flex: 1, padding: "8px 8px", display: "grid", gap: 2, alignContent: "start", overflowY: "auto" }}>
        {items.filter((it) => !(it as any).adminOnly || role === "admin").map((it) => (
          <NavLink
            key={it.to}
            to={it.to}
            style={({ isActive }) => ({
              display: "flex", gap: 12, padding: "8px 12px", borderRadius: 8,
              background: isActive ? "var(--primary-container)" : "transparent",
              color: isActive ? "var(--on-primary-container)" : "var(--on-surface-variant)",
              borderLeft: isActive ? "4px solid var(--primary)" : "4px solid transparent",
            })}
          >
            <span className="material-symbols-outlined">{it.icon}</span>
            {it.label}
          </NavLink>
        ))}
        <div style={{ margin: "12px 0", borderTop: "1px solid var(--outline-variant)", opacity: 0.5 }} />
      </nav>
      <div style={{ padding: 12, background: "var(--surface-container-low)", borderTop: "1px solid var(--outline-variant)", marginTop: "auto" }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
          <div style={{ width: 40, height: 40, borderRadius: 9999, background: "var(--primary)", display: "grid", placeItems: "center", color: "var(--on-primary)" }}>
            <span className="material-symbols-outlined">person</span>
          </div>
          <div style={{ flex: 1, overflow: "hidden" }}>
            <div style={{ fontSize: 13, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{useAuthStore((s) => s.user?.username) ?? "Admin CMS"}</div>
            <div style={{ fontSize: 11, color: "var(--on-surface-variant)" }}>{role ?? "Biên tập viên"}</div>
          </div>
        </div>
        <button onClick={() => useAuthStore.getState().logout()} style={{ width: "100%", padding: "6px 12px", background: "rgba(186,26,26,0.08)", color: "#ba1a1a", border: "none", borderRadius: 8, fontSize: 12, fontWeight: 600, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, cursor: "pointer" }}>
          <span className="material-symbols-outlined" style={{ fontSize: 14 }}>logout</span> Đăng xuất
        </button>
      </div>
    </aside>
  );
}

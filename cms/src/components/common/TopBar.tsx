export function TopBar() {
  return (
    <header style={{ height: 48, display: "flex", alignItems: "center", padding: "0 16px", borderBottom: "1px solid var(--border)", background: "var(--bg-surface)" }}>
      <input className="input" placeholder="Tìm kiếm video, metadata hoặc log..." style={{ flex: 1, maxWidth: 420 }} />
      <div style={{ marginLeft: "auto", display: "flex", gap: 12 }}>
        <span className="material-symbols-outlined">notifications</span>
      </div>
    </header>
  );
}

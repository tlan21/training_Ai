"use client";
import Link from "next/link";
export function BottomNav({ active }: { active: "home" | "discover" | "library" | "profile" }) {
  const items = [
    { id: "home", label: "Trang chủ", icon: "home", href: "/feed" },
    { id: "discover", label: "Khám phá", icon: "explore", href: "/discover" },
    { id: "library", label: "Thư viện", icon: "video_library", href: "/profile" },
    { id: "profile", label: "Cá nhân", icon: "person", href: "/profile" },
  ] as const;
  return (
    <nav style={{ position: "fixed", bottom: 0, left: 0, width: "100%", display: "flex", justifyContent: "space-around", alignItems: "center", padding: "0 16px", paddingBottom: "env(safe-area-inset-bottom)", height: 56, background: "var(--surface-container, white)", borderTop: "1px solid var(--outline-variant, #e0d8d5)", zIndex: 50 }}>
      {items.map((it) => {
        const on = active === it.id;
        return (
          <Link key={it.id} href={it.href} style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "4px 12px", borderRadius: 12, background: on ? "var(--primary-container, #ede0ff)" : "transparent", color: on ? "var(--on-primary-container, #25005a)" : "var(--on-surface-variant, #4a4455)" }}>
            <span className="material-symbols-outlined" style={{ fontVariationSettings: on ? "'FILL' 1" : "'FILL' 0", fontSize: 22 }}>{it.icon}</span>
            <span style={{ fontSize: 10, fontWeight: on ? 700 : 500 }}>{it.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

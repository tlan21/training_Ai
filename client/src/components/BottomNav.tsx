"use client";
import Link from "next/link";
import { Icon } from "@/components/Icon";
import type { NavTab } from "@/components/AppNav";
export function BottomNav({ active, camera = false }: {
    active: NavTab;
    camera?: boolean;
}) {
    return <nav className="bottom-nav" aria-label="Điều hướng mobile">
    <Link href="/feed" className={active === "home" ? "active" : ""} aria-current={active === "home" ? "page" : undefined}><Icon name="home" filled={active === "home"}/><span>Trang chủ</span></Link>
    <Link href="/discover" className={active === "discover" || active === "search" ? "active" : ""}><Icon name="explore" filled={active === "discover" || active === "search"}/><span>Khám phá</span></Link>
    {camera && <Link className="camera-nav" href="/search?tab=visual&camera=1" aria-label="Tìm kiếm bằng máy ảnh"><Icon name="add" size={32}/></Link>}
    <Link href="/profile?view=library" className={active === "library" ? "active" : ""}><Icon name="video_library" filled={active === "library"}/><span>Thư viện</span></Link>
    <Link href="/profile?view=account" className={active === "profile" ? "active" : ""}><Icon name="person" filled={active === "profile"}/><span>Cá nhân</span></Link>
  </nav>;
}

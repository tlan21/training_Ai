"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "@/components/Icon";
export function AuthFrame({ mode, children }: {
    mode: "login" | "register" | "forgot" | "reset";
    children: React.ReactNode;
}) {
    return <main className={`auth-page auth-${mode}`}><div className="auth-backdrop"/><div className="auth-glow auth-glow-one"/><div className="auth-glow auth-glow-two"/><div className="auth-card">
    <header className="auth-heading">
      <div className="auth-brand-row"><span className="auth-logo logo-mobile"><Icon name={mode === "register" || mode === "forgot" ? "play_circle" : "movie_filter"} size={mode === "forgot" ? 32 : 40} filled/></span>
      <span className="auth-logo logo-desktop"><Icon name={mode === "register" ? "movie_edit" : mode === "forgot" ? "play_circle" : "videocam"} size={mode === "forgot" ? 24 : 40}/></span>
      <h1>VidsAI</h1></div>
      {mode === "forgot" && <span className="reset-emblem mobile-only"><Icon name="lock_reset" size={48}/></span>}
      {mode === "login" ? <p><span className="mobile-only">Trí tuệ nhân tạo cho video của bạn</span><span className="desktop-only">Nâng tầm video của bạn bằng AI</span></p> : mode === "register" ? <><h2>Tham gia VidsAI</h2><p><span className="mobile-only">Khám phá sức mạnh của video AI ngay hôm nay.</span><span className="desktop-only">Bắt đầu hành trình sáng tạo cùng AI</span></p></> : <><h2>{mode === "forgot" ? <><span className="mobile-only">Quên mật khẩu?</span><span className="desktop-only">Khôi phục mật khẩu</span></> : "Đặt lại mật khẩu"}</h2><p>{mode === "forgot" ? "Đừng lo lắng, chúng tôi sẽ giúp bạn khôi phục tài khoản." : "Tạo mật khẩu mới cho tài khoản của bạn."}</p></>}
    </header>
    {children}
    <footer className="auth-footer">{mode === "login" ? <p>Chưa có tài khoản? <Link href="/register">Đăng ký ngay</Link></p> : mode === "register" ? <p>Đã có tài khoản? <Link href="/login">Đăng nhập ngay</Link></p> : <Link href="/login" className="back-login"><Icon name="arrow_back" size={18}/>Quay lại đăng nhập</Link>}
    {mode === "login" && <div className="legal-links mobile-only"><span>Điều khoản</span><span>Bảo mật</span><span>Trợ giúp</span></div>}
    {mode === "register" && <p className="legal-copy mobile-only">Bằng cách đăng ký, bạn đồng ý với Điều khoản và Chính sách bảo mật của VidsAI.</p>}
      {mode === "forgot" && <p className="auth-copyright mobile-only">© 2024 VidsAI. Nền tảng video thông minh.</p>}
    </footer>
  </div></main>;
}
export function AuthField({ id, label, icon, desktopIcon, desktopPlaceholder, action, ...props }: {
    id: string;
    label: string;
    icon: string;
    desktopIcon?: string;
    desktopPlaceholder?: string;
    action?: React.ReactNode;
} & React.InputHTMLAttributes<HTMLInputElement>) {
    const [desktop, setDesktop] = useState(false);
    useEffect(() => { const media = window.matchMedia("(min-width:1024px)"); const update = () => setDesktop(media.matches); update(); media.addEventListener("change", update); return () => media.removeEventListener("change", update); }, []);
    return <div className="auth-field"><label htmlFor={id}>{label}</label><div className="input-wrap"><span className="input-icon input-icon--left"><Icon name={desktop && desktopIcon ? desktopIcon : icon} size={22}/></span><input id={id} {...props} placeholder={desktop && desktopPlaceholder ? desktopPlaceholder : props.placeholder} className={`input input--with-left-icon ${action ? "input--with-right-icon" : ""}`}/>{action}</div></div>;
}

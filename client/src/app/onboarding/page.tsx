"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useCategories } from "@/lib/content";
import { useAuthStore } from "@/stores/authStore";
import { apiClient, errorMessage } from "@/lib/apiClient";
import { PageState } from "@/components/Media";
import { Icon } from "@/components/Icon";
const categoryArt: Record<string, {
    mobile: number;
    desktop: number;
    icon: string;
}> = {
    "Bóng đá": { mobile: 2, desktop: 0, icon: "sports_soccer" }, "Thể thao": { mobile: 2, desktop: 1, icon: "fitness_center" }, "Ca nhạc": { mobile: 5, desktop: 3, icon: "music_note" },
    "Âm nhạc": { mobile: 5, desktop: 3, icon: "music_note" }, "Tin tức": { mobile: 6, desktop: 4, icon: "newspaper" }, "Công nghệ": { mobile: 0, desktop: 5, icon: "memory" },
    "Phim ảnh": { mobile: 7, desktop: 6, icon: "movie" }, "Giải trí": { mobile: 1, desktop: 7, icon: "theater_comedy" }, "Ẩm thực": { mobile: 4, desktop: 7, icon: "restaurant" },
    "Du lịch": { mobile: 8, desktop: 7, icon: "flight" }, "Giáo dục": { mobile: 6, desktop: 4, icon: "school" }, "Game": { mobile: 9, desktop: 2, icon: "sports_esports" },
    "Trò chơi": { mobile: 9, desktop: 2, icon: "sports_esports" }
};
export default function OnboardingPage() {
    const categories = useCategories();
    const [selected, setSelected] = useState<string[]>([]);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const { user, ready } = useAuthStore();
    const router = useRouter();
    const query = useQueryClient();
    useEffect(() => { if (ready && user?.preferences)
        setSelected(user.preferences); }, [ready, user]);
    const toggle = (id: string) => setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);
    const complete = async () => {
        setSaving(true);
        setError("");
        try {
            await apiClient.put("/api/users/me/preferences", { category_ids: selected });
            if (user)
                useAuthStore.setState({ user: { ...user, preferences: selected } });
            await query.invalidateQueries({ queryKey: ["/api/feed"] });
            router.push("/feed");
        }
        catch (e) {
            setError(errorMessage(e));
        }
        finally {
            setSaving(false);
        }
    };
    const skip = () => { sessionStorage.setItem(`onboarding-skipped-${user?.id}`, "1"); router.push("/feed"); };
    return <div className="onboarding-page">
  <div className="onboard-progress"><div style={{ width: "40%" }}/></div>
  <div className="onboard-desktop-header desktop-only"><span className="brand">VidsAI</span><div className="onboard-desktop-step"><i className="step-dot"/><i className="step-dot"/><i className="step-dot"/><span>Bước 1 / 3</span></div></div>
  <header className="onboard-header">
   <div className="onboard-step mobile-only"><button className="icon-button" onClick={() => router.back()} aria-label="Quay lại"><Icon name="arrow_back"/></button><span>BƯỚC 2/5</span><span style={{ width: 40 }}/></div>
   <h1><span className="mobile-only">Chào mừng bạn đến với VidsAI</span><span className="desktop-only">Sở thích của bạn là gì?</span></h1>
   <p><span className="mobile-only">Chọn ít nhất 3 chủ đề bạn yêu thích để chúng tôi tối ưu hóa trải nghiệm của bạn.</span><span className="desktop-only">Chọn ít nhất 3 hạng mục để chúng tôi cá nhân hóa trải nghiệm của bạn.</span></p>
  </header>
  {categories.isPending ? <PageState loading/> : categories.error ? <PageState error={categories.error} retry={() => categories.refetch()}/> : categories.data?.length ? <main className="onboard-grid">
   {categories.data.filter(c => c.id).map((c, i) => {
                const art = categoryArt[c.name || ""];
                return <button key={c.id} aria-pressed={selected.includes(c.id!)} onClick={() => toggle(c.id!)} className={`interest-card ${["Thể thao", "Phim ảnh"].includes(c.name || "") ? "wide" : ""} ${selected.includes(c.id!) ? "selected" : ""}`}>
    <span className="thumbnail"><picture><source media="(min-width:1024px)" srcSet={`/stitch/interest_onboarding_desktop-${art?.desktop ?? i % 8}.jpg`}/><img src={`/stitch/interest_onboarding_mobile-${art?.mobile ?? i % 10}.jpg`} alt=""/></picture></span>
    <span className="interest-label"><span><span className="desktop-only"><Icon name={art?.icon || "interests"}/></span>{c.name}{c.name === "Thể thao" && <small>Bóng đá, NBA, Fitness...</small>}{c.name === "Phim ảnh" && <small>Review, Trailer, Hậu trường...</small>}</span><span className="check"><Icon name="check_circle" filled size={24}/></span></span>
   </button>;
            })}
  </main> : <PageState empty="Chưa có chủ đề"/>}
  <footer className="onboard-footer"><div className="onboard-footer-inner">
   {error && <p className="error-banner" role="alert">{error}</p>}
   <div className="onboard-count"><span>Đã chọn: <b>{selected.length}</b>/3</span><div className="onboard-progress-bottom desktop-only"><div style={{ width: `${Math.min(100, selected.length / 3 * 100)}%` }}/></div><button onClick={skip} disabled={saving}>Bỏ qua</button></div>
   <button className="btn-primary onboard-complete" disabled={selected.length < 3 || saving} onClick={complete}>{saving ? "Đang lưu…" : <><span className="mobile-only">Hoàn tất</span><span className="desktop-only">Hoàn tất và khám phá</span></>}<Icon name="chevron_right" size={20}/></button>
  </div></footer>
 </div>;
}

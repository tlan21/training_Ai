"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { paths } from "@/api-types";
import { Icon } from "@/components/Icon";
import { apiClient, errorMessage } from "@/lib/apiClient";
import { useAuthStore } from "@/stores/authStore";

// INT-62 (API 0.14.0): in-app inbox filled from Kafka clip.published. Polls every 60 s — simple, no socket.
type Inbox = paths["/api/users/me/notifications"]["get"]["responses"][200]["content"]["application/json"];
const KEY = ["notifications"];

function ago(iso: string) {
    const minutes = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60_000));
    if (minutes < 1) return "Vừa xong";
    if (minutes < 60) return `${minutes} phút trước`;
    if (minutes < 60 * 24) return `${Math.round(minutes / 60)} giờ trước`;
    return new Date(iso).toLocaleDateString("vi-VN");
}

export function NotificationBell() {
    const ready = useAuthStore(s => s.ready && !!s.accessToken);
    const router = useRouter();
    const qc = useQueryClient();
    const [open, setOpen] = useState(false);
    const box = useRef<HTMLSpanElement>(null);
    const inbox = useQuery({ queryKey: KEY, enabled: ready, refetchInterval: 60_000,
        queryFn: async () => (await apiClient.get<Inbox>("/api/users/me/notifications", { params: { limit: 20 } })).data });
    const read = useMutation({ mutationFn: (ids?: string[]) => apiClient.post("/api/users/me/notifications/read", ids ? { ids } : undefined),
        onSettled: () => qc.invalidateQueries({ queryKey: KEY }) });
    useEffect(() => {
        if (!open) return;
        const close = (e: MouseEvent | KeyboardEvent) => { if (e instanceof KeyboardEvent ? e.key === "Escape" : !box.current?.contains(e.target as Node)) setOpen(false); };
        document.addEventListener("mousedown", close);
        document.addEventListener("keydown", close);
        return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", close); };
    }, [open]);
    const unread = inbox.data?.unread_count ?? 0;
    const items = inbox.data?.items ?? [];
    return <span className="notify" ref={box}>
        <button className="icon-button" aria-label={unread ? `Thông báo (${unread} chưa đọc)` : "Thông báo"} aria-expanded={open} aria-haspopup="dialog" onClick={() => setOpen(v => !v)}>
            <Icon name="notifications" filled={unread > 0}/>{unread > 0 && <span className="notify-badge" aria-hidden="true">{unread > 99 ? "99+" : unread}</span>}
        </button>
        {open && <div className="notify-panel" role="dialog" aria-label="Thông báo">
            <header><strong>Thông báo</strong><button className="link" disabled={!unread || read.isPending} onClick={() => read.mutate(undefined)}>Đánh dấu tất cả đã đọc</button></header>
            {inbox.isPending ? <p className="notify-empty">Đang tải…</p> : inbox.error ? <p className="notify-empty" role="alert">{errorMessage(inbox.error)}</p>
                : !items.length ? <p className="notify-empty">Chưa có thông báo. Khi có clip mới thuộc chủ đề bạn yêu thích, thông báo sẽ hiện ở đây.</p>
                : <ul>{items.map(n => <li key={n.id}><button className={n.read ? "" : "unread"} onClick={() => {
                    if (!n.read) read.mutate([n.id]);
                    setOpen(false);
                    router.push(`/videos/${n.video_id}?clip=${n.clip_id}`);
                }}>{!n.read && <span className="notify-dot" aria-label="Chưa đọc"/>}<span className="notify-text"><span>Clip mới: <b>{n.title}</b></span><small>{ago(n.created_at)}</small></span></button></li>)}</ul>}
        </div>}
    </span>;
}

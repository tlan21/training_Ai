"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
export default function RootPage() {
    const { ready, accessToken } = useAuthStore();
    const router = useRouter();
    useEffect(() => { if (ready)
        router.replace(accessToken ? "/feed" : "/login"); }, [ready, accessToken, router]);
    return <div className="page-state" role="status">Đang chuyển hướng…</div>;
}

"use client";
import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { apiClient, refreshSession } from "@/lib/apiClient";
import { useAuthStore } from "@/stores/authStore";
import type { components } from "@/api-types";
import { usePathname, useRouter } from "next/navigation";
import { PageState } from "@/components/Media";
export function Providers({ children }: {
    children: React.ReactNode;
}) {
    const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } }));
    const { accessToken, user, ready } = useAuthStore();
    const pathname = usePathname();
    const router = useRouter();
    const protectedPage = !["/", "/login", "/register", "/forgot-password", "/reset-password"].includes(pathname);
    const signedIn = !!accessToken && !!user?.id;
    useEffect(() => useAuthStore.subscribe((state, previous) => {
        if (state.user?.id !== previous.user?.id || (!state.accessToken && previous.accessToken)) queryClient.clear();
    }), [queryClient]);
    useEffect(() => {
        if (ready && protectedPage && !signedIn) router.replace("/login");
    }, [ready, protectedPage, signedIn, router]);
    useEffect(() => {
        // Remove the legacy persisted access token; restore sessions through the HttpOnly cookie.
        localStorage.removeItem("client-auth");
        if (localStorage.getItem("client-signed-out")) { useAuthStore.getState().setReady(); return; }
        let mounted = true;
        refreshSession().then(async () => {
            const { data } = await apiClient.get<components["schemas"]["UserMe"]>("/api/users/me");
            const token = useAuthStore.getState().accessToken;
            if (!token || !data.id) throw new Error("Phiên đăng nhập không hợp lệ.");
            if (mounted)
                useAuthStore.getState().setAuth({ accessToken: token, user: data });
        }).catch(() => { if (mounted)
            useAuthStore.getState().logout(); });
        return () => { mounted = false; };
    }, []);
    return <QueryClientProvider client={queryClient}>{protectedPage && (!ready || !signedIn) ? <PageState loading /> : children}</QueryClientProvider>;
}

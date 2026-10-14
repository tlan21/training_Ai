"use client";
import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { apiClient, refreshSession } from "@/lib/apiClient";
import { useAuthStore } from "@/stores/authStore";
import type { components } from "@/api-types";
export function Providers({ children }: {
    children: React.ReactNode;
}) {
    const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } }));
    useEffect(() => {
        // Remove the legacy persisted access token; restore sessions through the HttpOnly cookie.
        localStorage.removeItem("client-auth");
        let mounted = true;
        refreshSession().then(async (token) => {
            const { data } = await apiClient.get<components["schemas"]["UserMe"]>("/api/users/me");
            if (mounted)
                useAuthStore.getState().setAuth({ accessToken: token, user: data });
        }).catch(() => { if (mounted)
            useAuthStore.getState().setReady(); });
        return () => { mounted = false; };
    }, []);
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

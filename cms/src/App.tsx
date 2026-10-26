import { RouterProvider } from "react-router-dom";
import { router } from "./router";
import { useEffect } from "react";
import { apiClient, refreshSession } from "./lib/apiClient";
import { useAuthStore } from "./stores/authStore";
import { Skeleton } from "./components/common/Skeleton";
import type { components } from "./api-types";

export default function App() {
  const ready = useAuthStore((state) => state.ready);
  useEffect(() => {
    if (localStorage.getItem("cms-signed-out") || (localStorage.getItem("cms-remember") === "false" && !sessionStorage.getItem("cms-session-active"))) {
      useAuthStore.getState().setReady();
      return;
    }
    let mounted = true;
    refreshSession().then(async () => {
      const { data: user } = await apiClient.get<components["schemas"]["UserMe"]>("/api/users/me", { timeout: 10_000 });
      if (mounted) {
        const accessToken = useAuthStore.getState().accessToken;
        if (accessToken && (user.role === "admin" || user.role === "editor")) useAuthStore.getState().setAuth({ accessToken, user });
        else useAuthStore.getState().logout();
      }
    }).catch(() => { if (mounted) useAuthStore.getState().logout(); });
    return () => { mounted = false; };
  }, []);
  if (!ready) return <div className="auth-page" role="status" aria-label="Đang khôi phục phiên đăng nhập"><Skeleton h={48} w={240} /></div>;
  return <RouterProvider router={router} />;
}

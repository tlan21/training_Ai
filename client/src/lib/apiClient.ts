import axios from "axios";
import { useAuthStore } from "@/stores/authStore";
import type { components, paths } from "@/api-types";
export const apiClient = axios.create({ baseURL: process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000", withCredentials: true });
apiClient.interceptors.request.use((cfg) => {
    const token = useAuthStore.getState().accessToken;
    if (token)
        cfg.headers.Authorization = `Bearer ${token}`;
    return cfg;
});
let refreshRequest: Promise<string> | null = null;
export function refreshSession() {
    if (!refreshRequest)
        refreshRequest = axios.post<paths["/api/auth/refresh"]["post"]["responses"][200]["content"]["application/json"]>(`${apiClient.defaults.baseURL}/api/auth/refresh`, {}, { withCredentials: true }).then(({ data }) => {
            if (!data.access_token)
                throw new Error("Phiên đăng nhập không hợp lệ.");
            useAuthStore.getState().setToken(data.access_token);
            return data.access_token;
        }).finally(() => { refreshRequest = null; });
    return refreshRequest;
}
apiClient.interceptors.response.use(r => r, async (err) => {
    const orig = err.config;
    if (orig && err.response?.status === 401 && !orig._retry && !orig.url?.startsWith("/api/auth/")) {
        orig._retry = true;
        try {
            const token = await refreshSession();
            orig.headers.Authorization = `Bearer ${token}`;
            return apiClient(orig);
        }
        catch {
            useAuthStore.getState().logout();
            if (typeof window !== "undefined")
                window.location.assign("/login");
        }
    }
    return Promise.reject(err);
});
export function errorMessage(error: unknown) {
    if (axios.isAxiosError<components["schemas"]["Error"]>(error))
        return error.response?.data?.error?.message || "Không thể kết nối máy chủ. Vui lòng thử lại.";
    return error instanceof Error ? error.message : "Không thể thực hiện yêu cầu.";
}

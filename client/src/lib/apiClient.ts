import axios from "axios";
import type { InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "@/stores/authStore";
import type { components, paths } from "@/api-types";
export const apiClient = axios.create({ baseURL: process.env.NEXT_PUBLIC_API_BASE || "", withCredentials: true, timeout: 10_000 });
let refreshRequest: Promise<string> | null = null;
let logoutRequest: Promise<void> | null = null;
type SessionRequest = InternalAxiosRequestConfig & { _retry?: boolean; _sessionUser?: string | null };
apiClient.interceptors.request.use(async (cfg: SessionRequest) => {
    if (cfg.url === "/api/auth/login" || cfg.url === "/api/auth/register") {
        if (logoutRequest) await logoutRequest.catch(() => {});
        if (refreshRequest) await refreshRequest.catch(() => {});
    }
    const state = useAuthStore.getState();
    if (cfg._retry && cfg._sessionUser !== (state.user?.id ?? null)) throw new axios.CanceledError("Phiên đăng nhập đã thay đổi.");
    const token = state.accessToken;
    if (token)
        cfg.headers.Authorization = `Bearer ${token}`;
    cfg._sessionUser = state.user?.id ?? null;
    return cfg;
});
export function refreshSession() {
    if (logoutRequest) return Promise.reject(new Error("Phiên đăng nhập đã kết thúc."));
    if (!refreshRequest) {
        const previousToken = useAuthStore.getState().accessToken;
        const previousUser = useAuthStore.getState().user;
        refreshRequest = axios.post<paths["/api/auth/refresh"]["post"]["responses"][200]["content"]["application/json"]>(`${apiClient.defaults.baseURL}/api/auth/refresh`, {}, { withCredentials: true, timeout: 10_000 }).then(async ({ data }) => {
            if (!data.access_token)
                throw new Error("Phiên đăng nhập không hợp lệ.");
            if (useAuthStore.getState().accessToken !== previousToken) throw new Error("Phiên đăng nhập đã thay đổi.");
            if (previousUser?.id) {
                const { data: user } = await axios.get<components["schemas"]["UserMe"]>(`${apiClient.defaults.baseURL}/api/users/me`, { headers: { Authorization: `Bearer ${data.access_token}` }, withCredentials: true, timeout: 10_000 });
                if (user.id !== previousUser.id || useAuthStore.getState().accessToken !== previousToken) throw new Error("Phiên đăng nhập đã thay đổi.");
                if (!logoutRequest) useAuthStore.getState().setAuth({ accessToken: data.access_token, user });
                else useAuthStore.getState().setToken(data.access_token);
            } else useAuthStore.getState().setToken(data.access_token);
            return data.access_token;
        }).finally(() => { refreshRequest = null; });
    }
    return refreshRequest;
}
export function logoutSession() {
    if (!logoutRequest) {
        localStorage.setItem("client-signed-out", "1");
        const pendingRefresh = refreshRequest;
        logoutRequest = (async () => {
            try {
                if (pendingRefresh) await pendingRefresh.catch(() => {});
                await apiClient.post("/api/auth/logout");
            } finally {
                useAuthStore.getState().logout();
                logoutRequest = null;
            }
        })();
    }
    return logoutRequest;
}
apiClient.interceptors.response.use(r => r, async (err) => {
    const orig = err.config;
    const state = useAuthStore.getState();
    if (orig && err.response?.status === 401 && orig._retry && orig._sessionUser === (state.user?.id ?? null) && orig.headers.Authorization === `Bearer ${state.accessToken}`) state.logout();
    if (orig && err.response?.status === 401 && !orig._retry && !orig.url?.startsWith("/api/auth/")) {
        orig._retry = true;
        const previousToken = state.accessToken;
        if (!previousToken || orig._sessionUser !== (state.user?.id ?? null)) return Promise.reject(err);
        try {
            const token = orig.headers.Authorization !== `Bearer ${previousToken}` ? previousToken : await refreshSession();
            orig.headers.Authorization = `Bearer ${token}`;
            return apiClient(orig);
        }
        catch (error) {
            if (useAuthStore.getState().accessToken === previousToken) useAuthStore.getState().logout();
            return Promise.reject(error);
        }
    }
    return Promise.reject(err);
});
export function errorMessage(error: unknown) {
    if (axios.isAxiosError<components["schemas"]["Error"]>(error))
        return error.response?.data?.error?.message || "Không thể kết nối máy chủ. Vui lòng thử lại.";
    return error instanceof Error ? error.message : "Không thể thực hiện yêu cầu.";
}

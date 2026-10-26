import axios from "axios";
import { useAuthStore } from "../stores/authStore";
import type { components, paths } from "../api-types";

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError<components["schemas"]["Error"]>(error)) return error.response?.data?.error?.message ?? error.message;
  return error instanceof Error ? error.message : "Không thực hiện được thao tác";
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "",
  withCredentials: true,
});

apiClient.interceptors.request.use((cfg) => {
  const tok = useAuthStore.getState().accessToken;
  if (tok) cfg.headers.Authorization = `Bearer ${tok}`;
  return cfg;
});

let refreshRequest: Promise<string> | null = null;
let logoutRequest: Promise<void> | null = null;

export function refreshSession() {
  if (logoutRequest) return Promise.reject(new Error("Phiên đăng nhập đã kết thúc."));
  if (!refreshRequest) {
    const previousToken = useAuthStore.getState().accessToken;
    refreshRequest = axios.post<paths["/api/auth/refresh"]["post"]["responses"][200]["content"]["application/json"]>(
      `${apiClient.defaults.baseURL}/api/auth/refresh`, {}, { withCredentials: true, timeout: 10_000 },
    ).then(({ data }) => {
      if (!data.access_token) throw new Error("Phiên đăng nhập không hợp lệ.");
      if (useAuthStore.getState().accessToken !== previousToken) throw new Error("Phiên đăng nhập đã thay đổi.");
      useAuthStore.getState().setToken(data.access_token);
      return data.access_token;
    }).finally(() => { refreshRequest = null; });
  }
  return refreshRequest;
}

export function logoutSession() {
  if (!logoutRequest) {
    localStorage.setItem("cms-signed-out", "1");
    const pendingRefresh = refreshRequest;
    logoutRequest = (async () => {
      try {
        if (pendingRefresh) await pendingRefresh.catch(() => {});
        await apiClient.post("/api/auth/logout", {}, { timeout: 10_000 });
      } finally {
        useAuthStore.getState().logout();
        logoutRequest = null;
      }
    })();
  }
  return logoutRequest;
}

export async function loginSession(credentials: paths["/api/auth/login"]["post"]["requestBody"]["content"]["application/json"]) {
  if (logoutRequest) await logoutRequest.catch(() => {});
  if (refreshRequest) await refreshRequest.catch(() => {});
  const { data } = await apiClient.post<components["schemas"]["AuthResponse"]>("/api/auth/login", credentials, { timeout: 10_000 });
  if (!data.access_token || !data.user?.id || !data.user.role) throw new Error("Phản hồi đăng nhập không hợp lệ.");
  if (data.user.role !== "admin" && data.user.role !== "editor") {
    await apiClient.post("/api/auth/logout", {}, { headers: { Authorization: `Bearer ${data.access_token}` }, timeout: 10_000 }).catch(() => {});
    throw new Error("Tài khoản này không có quyền truy cập CMS.");
  }
  return { access_token: data.access_token, user: data.user };
}

apiClient.interceptors.response.use(
  (r) => r,
  async (err) => {
    const orig = err.config;
    if (err.response?.status === 401 && orig?._retry && orig.headers.Authorization === `Bearer ${useAuthStore.getState().accessToken}`) {
      useAuthStore.getState().logout();
    }
    if (err.response?.status === 401 && orig && !orig._retry && !orig.url?.startsWith("/api/auth/")) {
      orig._retry = true;
      const previousToken = useAuthStore.getState().accessToken;
      if (!previousToken) return Promise.reject(err);
      try {
        const token = previousToken && orig.headers.Authorization !== `Bearer ${previousToken}`
          ? previousToken : await refreshSession();
        orig.headers.Authorization = `Bearer ${token}`;
        return apiClient(orig);
      } catch (e) {
        if (useAuthStore.getState().accessToken === previousToken) useAuthStore.getState().logout();
        return Promise.reject(e);
      }
    }
    // unwrap error envelope
    const data = err.response?.data;
    if (data?.error) err.apiError = data.error;
    return Promise.reject(err);
  },
);

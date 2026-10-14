import axios from "axios";
import { useAuthStore } from "../stores/authStore";
import type { components } from "../api-types";

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

let isRefreshing = false;
let queue: Array<(t: string | null) => void> = [];

apiClient.interceptors.response.use(
  (r) => r,
  async (err) => {
    const orig = err.config;
    if (err.response?.status === 401 && orig && !orig._retry && !orig.url?.startsWith("/api/auth/")) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          queue.push((t) => {
            if (t) {
              orig.headers.Authorization = `Bearer ${t}`;
              resolve(apiClient(orig));
            } else reject(err);
          });
        });
      }
      orig._retry = true;
      isRefreshing = true;
      try {
        const res = await axios.post(
          `${import.meta.env.VITE_API_BASE || ""}/api/auth/refresh`,
          {},
          { withCredentials: true },
        );
        const tok = res.data.access_token as string;
        useAuthStore.getState().setToken(tok);
        queue.forEach((cb) => cb(tok));
        queue = [];
        orig.headers.Authorization = `Bearer ${tok}`;
        return apiClient(orig);
      } catch (e) {
        queue.forEach((cb) => cb(null));
        queue = [];
        useAuthStore.getState().logout();
        window.location.href = "/login";
        return Promise.reject(e);
      } finally {
        isRefreshing = false;
      }
    }
    // unwrap error envelope
    const data = err.response?.data;
    if (data?.error) err.apiError = data.error;
    return Promise.reject(err);
  },
);

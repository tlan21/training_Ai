import axios from "axios";
import { useAuthStore } from "@/stores/authStore";
export const apiClient = axios.create({ baseURL: process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000", withCredentials: true });
apiClient.interceptors.request.use((cfg) => {
  const t = useAuthStore.getState().accessToken;
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});
let refreshing = false;
let queue: Array<(t: string | null) => void> = [];
apiClient.interceptors.response.use(
  (r) => r,
  async (err) => {
    const orig = err.config;
    if (err.response?.status === 401 && !orig._retry) {
      if (refreshing) return new Promise((res, rej) => { queue.push((t) => t ? (orig.headers.Authorization = `Bearer ${t}`, res(apiClient(orig))) : rej(err)); });
      orig._retry = true; refreshing = true;
      try {
        const r = await axios.post(`${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}/api/auth/refresh`, {}, { withCredentials: true });
        const tok = r.data.access_token;
        useAuthStore.getState().setToken(tok);
        queue.forEach((cb) => cb(tok)); queue = [];
        orig.headers.Authorization = `Bearer ${tok}`;
        return apiClient(orig);
      } catch (e) { queue.forEach((cb) => cb(null)); queue = []; useAuthStore.getState().logout(); if (typeof window !== "undefined") window.location.href = "/login"; return Promise.reject(e); }
      finally { refreshing = false; }
    }
    return Promise.reject(err);
  },
);

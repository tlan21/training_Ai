import { useMutation, useQuery } from "@tanstack/react-query";
import { apiClient } from "../lib/apiClient";
import { useAuthStore } from "../stores/authStore";
import { qk } from "../lib/queryKeys";

export function useLogin() {
  return useMutation({
    mutationFn: async (p: { email: string; password: string }) => {
      const r = await apiClient.post("/api/auth/login", p);
      return r.data as { access_token: string; user: { id: string; username: string; email: string; role: string } };
    },
    onSuccess: (d) => useAuthStore.getState().setAuth({ accessToken: d.access_token, user: d.user }),
  });
}
export function useMe(enabled = true) {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => (await apiClient.get("/api/users/me")).data,
    enabled,
  });
}
export function useLogout() {
  return useMutation({
    mutationFn: async () => apiClient.post("/api/auth/logout"),
    onSettled: () => useAuthStore.getState().logout(),
  });
}
export function useVideos(params: { status?: string; page?: number }) {
  return useQuery({
    queryKey: qk.videos(params),
    queryFn: async () => (await apiClient.get("/api/cms/videos", { params })).data,
  });
}
export function useJobs(params: { status?: string }) {
  return useQuery({
    queryKey: qk.jobs(params),
    queryFn: async () => (await apiClient.get("/api/cms/jobs", { params })).data,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  });
}
export function useSystemHealth() {
  return useQuery({
    queryKey: qk.health(),
    queryFn: async () => (await apiClient.get("/api/cms/system/health")).data,
    refetchInterval: 5000,
  });
}

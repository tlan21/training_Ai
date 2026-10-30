import { useMutation, useQuery } from "@tanstack/react-query";
import { apiClient, loginSession, logoutSession } from "../lib/apiClient";
import { useAuthStore } from "../stores/authStore";
import { qk } from "../lib/queryKeys";
import type { components } from "../api-types";
import { queryClient } from "../lib/queryClient";

export function useLogin() {
  return useMutation({
    mutationFn: loginSession,
    onSuccess: (d) => { queryClient.removeQueries(); useAuthStore.getState().setAuth({ accessToken: d.access_token, user: d.user }); },
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
    mutationFn: logoutSession,
  });
}
export function useSystemHealth(params: Parameters<typeof qk.health>[0] = {}) {
  return useQuery({
    queryKey: qk.health(params),
    queryFn: async () => (await apiClient.get<components["schemas"]["SystemHealth"]>("/api/cms/system/health", { params })).data,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  });
}

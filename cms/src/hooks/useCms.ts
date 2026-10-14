import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../lib/apiClient";
import { qk } from "../lib/queryKeys";
import type { components, paths } from "../api-types";
import { useUploadStore } from "../stores/uploadStore";

export function useCmsVideos(p: { status?: string; page?: number }) {
  return useQuery({ queryKey: qk.videos(p), queryFn: async () => (await apiClient.get<components["schemas"]["VideoTablePage"]>("/api/cms/videos", { params: p })).data });
}
export function useCmsVideo(id: string) {
  return useQuery({ queryKey: qk.video(id), queryFn: async () => (await apiClient.get<components["schemas"]["VideoDetail"]>(`/api/cms/videos/${id}`)).data, enabled: !!id });
}
export function useCmsAnalysis(id: string) {
  return useQuery({ queryKey: qk.analysis(id), queryFn: async () => (await apiClient.get<components["schemas"]["CmsAnalysis"]>(`/api/cms/videos/${id}/analysis`)).data, enabled: !!id });
}
export function useSubtitles(id: string) {
  return useQuery({ queryKey: qk.subtitles(id), queryFn: async () => (await apiClient.get<components["schemas"]["Subtitles"]>(`/api/videos/${id}/subtitles`)).data, enabled: !!id });
}
export function useCmsJobs(p: { status?: string } = {}) {
  return useQuery({ queryKey: qk.jobs(p), queryFn: async () => (await apiClient.get<components["schemas"]["Job"][]>("/api/cms/jobs", { params: p })).data, refetchInterval: 5000, refetchIntervalInBackground: false });
}
let _jobsHasProcessing = false;
export function useJobsPollingAware(p: { status?: string } = {}) {
  // keep polling only when needed — caller decides; helper for visibility-aware
  return useCmsJobs(p);
}
export function useCmsJob(id: string) {
  return useQuery({ queryKey: qk.job(id), queryFn: async () => (await apiClient.get<components["schemas"]["Job"]>(`/api/cms/jobs/${id}`)).data, enabled: !!id });
}
export function useUploadVideo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (form: FormData) => {
      const upload = useUploadStore.getState();
      return (await apiClient.post("/api/cms/videos", form, { signal: upload.controller?.signal, onUploadProgress: (event) => useUploadStore.getState().progress(event.loaded, event.total ?? upload.total) })).data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["videos"] }); qc.invalidateQueries({ queryKey: ["jobs"] }); },
  });
}
export function useClips(p: { video_id?: string; status?: string } = {}) {
  return useQuery({ queryKey: qk.clips(p), queryFn: async () => (await apiClient.get<components["schemas"]["Clip"][]>("/api/cms/clips", { params: p })).data, refetchInterval: (query) => query.state.data?.some((clip) => clip.status === "processing") ? 3000 : false });
}
export function useCreateClip() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async (b: paths["/api/cms/clips"]["post"]["requestBody"]["content"]["application/json"]) => (await apiClient.post<components["schemas"]["Clip"]>("/api/cms/clips", b)).data, onSuccess: () => qc.invalidateQueries({ queryKey: ["clips"] }) });
}
export function usePublishClip() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async (id: string) => (await apiClient.post(`/api/cms/clips/${id}/publish`)).data, onSuccess: () => qc.invalidateQueries({ queryKey: ["clips"] }) });
}
export function useDeleteClip() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async (id: string) => (await apiClient.delete(`/api/cms/clips/${id}`)).data, onSuccess: () => qc.invalidateQueries({ queryKey: ["clips"] }) });
}
export function useCategories() {
  return useQuery({ queryKey: qk.categories(), queryFn: async () => (await apiClient.get<components["schemas"]["Category"][]>("/api/cms/categories")).data });
}
export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async (b: paths["/api/cms/categories"]["post"]["requestBody"]["content"]["application/json"]) => (await apiClient.post("/api/cms/categories", b)).data, onSuccess: () => qc.invalidateQueries({ queryKey: qk.categories() }) });
}
export function useUpdateCategory() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async ({ id, name }: { id: string; name: string }) => (await apiClient.put(`/api/cms/categories/${id}`, { name })).data, onSuccess: () => qc.invalidateQueries({ queryKey: qk.categories() }) });
}
export function useDeleteCategory() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async (id: string) => (await apiClient.delete(`/api/cms/categories/${id}`)).data, onSuccess: () => qc.invalidateQueries({ queryKey: qk.categories() }) });
}
export function useCmsUsers(page = 1) {
  return useQuery({ queryKey: qk.users({ page }), queryFn: async () => (await apiClient.get<paths["/api/cms/users"]["get"]["responses"][200]["content"]["application/json"]>("/api/cms/users", { params: { page } })).data });
}
export function useUpdateRole() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async ({ id, role }: { id: string; role: string }) => (await apiClient.put(`/api/cms/users/${id}/role`, { role })).data, onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }) });
}
export function useSettings(enabled = true) {
  return useQuery({ queryKey: qk.settings(), queryFn: async () => (await apiClient.get<components["schemas"]["Settings"]>("/api/cms/settings")).data, enabled });
}
export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async (b: components["schemas"]["SettingsUpdate"]) => (await apiClient.put("/api/cms/settings", b)).data, onSuccess: () => qc.invalidateQueries({ queryKey: qk.settings() }) });
}

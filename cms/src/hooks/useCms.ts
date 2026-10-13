import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../lib/apiClient";
import { qk } from "../lib/queryKeys";

export function useCmsVideos(p: { status?: string; page?: number }) {
  return useQuery({ queryKey: qk.videos(p), queryFn: async () => (await apiClient.get("/api/cms/videos", { params: p })).data });
}
export function useCmsVideo(id: string) {
  return useQuery({ queryKey: qk.video(id), queryFn: async () => (await apiClient.get(`/api/cms/videos/${id}`)).data, enabled: !!id });
}
export function useCmsAnalysis(id: string) {
  return useQuery({ queryKey: qk.analysis(id), queryFn: async () => (await apiClient.get(`/api/cms/videos/${id}/analysis`)).data, enabled: !!id });
}
export function useSubtitles(id: string) {
  return useQuery({ queryKey: qk.subtitles(id), queryFn: async () => (await apiClient.get(`/api/videos/${id}/subtitles`)).data, enabled: !!id });
}
export function useCmsJobs(p: { status?: string } = {}) {
  return useQuery({ queryKey: qk.jobs(p), queryFn: async () => (await apiClient.get("/api/cms/jobs", { params: p })).data, refetchInterval: 5000, refetchIntervalInBackground: false });
}
export function useCmsJob(id: string) {
  return useQuery({ queryKey: qk.job(id), queryFn: async () => (await apiClient.get(`/api/cms/jobs/${id}`)).data, enabled: !!id });
}
export function useUploadVideo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (form: FormData) => (await apiClient.post("/api/cms/videos", form, { headers: { "Content-Type": "multipart/form-data" } })).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["videos"] }); qc.invalidateQueries({ queryKey: ["jobs"] }); },
  });
}
export function useClips(p: { video_id?: string; status?: string } = {}) {
  return useQuery({ queryKey: qk.clips(p), queryFn: async () => (await apiClient.get("/api/cms/clips", { params: p })).data });
}
export function useCreateClip() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async (b: any) => (await apiClient.post("/api/cms/clips", b)).data, onSuccess: () => qc.invalidateQueries({ queryKey: ["clips"] }) });
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
  return useQuery({ queryKey: qk.categories(), queryFn: async () => (await apiClient.get("/api/cms/categories")).data });
}
export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async (b: any) => (await apiClient.post("/api/cms/categories", b)).data, onSuccess: () => qc.invalidateQueries({ queryKey: qk.categories() }) });
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
  return useQuery({ queryKey: qk.users({ page }), queryFn: async () => (await apiClient.get("/api/cms/users", { params: { page } })).data });
}
export function useUpdateRole() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async ({ id, role }: { id: string; role: string }) => (await apiClient.put(`/api/cms/users/${id}/role`, { role })).data, onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }) });
}
export function useSettings() {
  return useQuery({ queryKey: qk.settings(), queryFn: async () => (await apiClient.get("/api/cms/settings")).data });
}
export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async (b: any) => (await apiClient.put("/api/cms/settings", b)).data, onSuccess: () => qc.invalidateQueries({ queryKey: qk.settings() }) });
}

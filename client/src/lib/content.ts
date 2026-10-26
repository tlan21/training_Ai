import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import type { components, paths } from "@/api-types";
import { apiClient } from "@/lib/apiClient";
import { useAuthStore } from "@/stores/authStore";
export type RecommendationMode = components["schemas"]["FeedPage"]["recommendation_mode"];
export function recommendationLabel(mode?: RecommendationMode) {
    return mode === "personalized" ? "Dành cho bạn" : mode === "popularity" ? "Phổ biến" : mode === "fallback" ? "Phổ biến (dự phòng)" : "Đề xuất";
}
export type Clip = components["schemas"]["Clip"];
export type Video = components["schemas"]["Video"];
export type HistoryPage = paths["/api/users/me/history"]["get"]["responses"][200]["content"]["application/json"];
export type VideoPage = paths["/api/videos"]["get"]["responses"][200]["content"]["application/json"];
export type VisualResults = paths["/api/search/visual"]["post"]["responses"][200]["content"]["application/json"];
export type TextResults = paths["/api/search"]["get"]["responses"][200]["content"]["application/json"];
export function useCategories() {
    return useQuery({ queryKey: ["categories"], queryFn: async () => (await apiClient.get<components["schemas"]["Category"][]>("/api/categories")).data });
}
export function useClipPage(endpoint: "/api/feed" | "/api/users/me/likes") {
    const ready = useAuthStore(s => s.ready);
    return useInfiniteQuery({ queryKey: [endpoint], enabled: ready, initialPageParam: null as string | null,
        queryFn: async ({ pageParam }) => (await apiClient.get<components["schemas"]["ClipPage"] & Partial<components["schemas"]["FeedPage"]>>(endpoint, { params: { cursor: pageParam || undefined, limit: 10 } })).data,
        getNextPageParam: page => page.next_cursor || undefined });
}
export function useHistory() {
    const ready = useAuthStore(s => s.ready);
    return useInfiniteQuery({ queryKey: ["history"], enabled: ready, initialPageParam: null as string | null,
        queryFn: async ({ pageParam }) => (await apiClient.get<HistoryPage>("/api/users/me/history", { params: { cursor: pageParam || undefined, limit: 10 } })).data,
        getNextPageParam: page => page.next_cursor || undefined });
}
export function useVideos(categoryId: string, sort: "newest" | "trending") {
    const ready = useAuthStore(s => s.ready);
    return useInfiniteQuery({ queryKey: ["videos", categoryId, sort], enabled: ready, initialPageParam: null as string | null,
        queryFn: async ({ pageParam }) => (await apiClient.get<VideoPage>("/api/videos", { params: { category_id: categoryId || undefined, sort, cursor: pageParam || undefined, limit: 10 } })).data,
        getNextPageParam: page => page.next_cursor || undefined });
}
export function formatTime(seconds = 0) {
    const n = Math.floor(Number.isFinite(seconds) ? Math.max(0, seconds) : 0);
    return `${String(Math.floor(n / 60)).padStart(2, "0")}:${String(n % 60).padStart(2, "0")}`;
}
export function formatDate(date?: string) {
    return date ? new Date(date).toLocaleDateString("vi-VN") : "—";
}
export type Interaction = paths["/api/interactions"]["post"]["requestBody"]["content"]["application/json"];
export function track(body: Interaction) { void apiClient.post("/api/interactions", body).catch(() => { }); }
export async function shareVideo(videoId: string, clipId?: string) {
    const url = `${window.location.origin}/videos/${videoId}${clipId ? `?clip=${clipId}` : ""}`;
    if (navigator.share)
        await navigator.share({ title: "VidsAI", url });
    else
        await navigator.clipboard.writeText(url);
    track({ video_id: videoId, clip_id: clipId, interaction_type: "share" });
}

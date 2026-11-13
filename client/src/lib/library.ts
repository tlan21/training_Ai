import axios from "axios";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import type { components } from "@/api-types";
import { apiClient, errorMessage } from "@/lib/apiClient";
import { useAuthStore } from "@/stores/authStore";

// INT-61 (API 0.13.0): like / watch-later state, user lists and history hiding. The server logs the like/save
// interaction itself on the first like/save, so callers must not also track() these.
type ClipState = components["schemas"]["ClipState"];
type UserList = components["schemas"]["UserList"];
type ClipPage = components["schemas"]["ClipPage"];

// ponytail: one request per tick for every clip id asked in that tick (≤50 per request, the API limit).
let pending = new Map<string, ((s: ClipState) => void)[]>();
let timer: ReturnType<typeof setTimeout> | null = null;
function flush() {
    const batch = pending;
    pending = new Map();
    timer = null;
    const ids = [...batch.keys()];
    for (let i = 0; i < ids.length; i += 50) {
        const chunk = ids.slice(i, i + 50);
        const fail = (id: string) => batch.get(id)?.forEach(done => done({ clip_id: id, liked: false, saved: false, list_ids: [] }));
        apiClient.get<{ items: ClipState[] }>("/api/users/me/clip-states", { params: { clip_ids: chunk.join(",") } }).then(({ data }) => {
            const byId = new Map(data.items.map(s => [s.clip_id, s]));
            chunk.forEach(id => { const s = byId.get(id); if (s) batch.get(id)?.forEach(done => done(s)); else fail(id); });
        }).catch(() => chunk.forEach(fail));
    }
}
function fetchState(id: string) {
    return new Promise<ClipState>(resolve => {
        pending.set(id, [...(pending.get(id) || []), resolve]);
        timer ??= setTimeout(flush, 0);
    });
}
const stateKey = (id: string) => ["clip-state", id];

export function useClipState(clipId?: string | null) {
    const ready = useAuthStore(s => s.ready && !!s.accessToken);
    return useQuery({ queryKey: stateKey(clipId || ""), enabled: ready && !!clipId, queryFn: () => fetchState(clipId!), staleTime: 60_000 });
}

function patchState(qc: QueryClient, id: string, patch: (s: ClipState) => ClipState) {
    const before = qc.getQueryData<ClipState>(stateKey(id));
    qc.setQueryData<ClipState>(stateKey(id), patch(before || { clip_id: id, liked: false, saved: false, list_ids: [] }));
    return before;
}

/** Toggle like ("likes") or watch-later ("saved") with an optimistic button state and rollback on error. */
export function useToggleMark(kind: "likes" | "saved") {
    const qc = useQueryClient();
    const field = kind === "likes" ? "liked" : "saved";
    return useMutation({
        mutationFn: async ({ clipId, on }: { clipId: string; on: boolean }) => {
            await (on ? apiClient.put : apiClient.delete)(`/api/users/me/${kind}/${clipId}`);
        },
        onMutate: async ({ clipId, on }) => {
            await qc.cancelQueries({ queryKey: stateKey(clipId) });
            return { before: patchState(qc, clipId, s => ({ ...s, [field]: on })) };
        },
        onError: (_e, { clipId }, ctx) => qc.setQueryData(stateKey(clipId), ctx?.before),
        onSettled: (_d, _e, { clipId }) => {
            void qc.invalidateQueries({ queryKey: stateKey(clipId) });
            void qc.invalidateQueries({ queryKey: [`/api/users/me/${kind}`] });
        },
    });
}

export function useLists() {
    const ready = useAuthStore(s => s.ready);
    return useQuery({ queryKey: ["lists"], enabled: ready, queryFn: async () => (await apiClient.get<{ items: UserList[] }>("/api/users/me/lists")).data.items });
}

export function useListItems(listId?: string | null) {
    const ready = useAuthStore(s => s.ready);
    return useInfiniteQuery({ queryKey: ["list-items", listId], enabled: ready && !!listId, initialPageParam: null as string | null,
        queryFn: async ({ pageParam }) => (await apiClient.get<ClipPage>(`/api/users/me/lists/${listId}/items`, { params: { cursor: pageParam || undefined, limit: 10 } })).data,
        getNextPageParam: page => page.next_cursor || undefined });
}

/** Lists CRUD + membership. Every call invalidates what it can change; errors are thrown for the caller to show. */
export function useListActions() {
    const qc = useQueryClient();
    const refresh = (listId?: string) => {
        void qc.invalidateQueries({ queryKey: ["lists"] });
        if (listId) void qc.invalidateQueries({ queryKey: ["list-items", listId] });
    };
    return {
        create: async (name: string) => { const { data } = await apiClient.post<UserList>("/api/users/me/lists", { name: name.trim() }); refresh(); return data; },
        rename: async (listId: string, name: string) => { await apiClient.patch(`/api/users/me/lists/${listId}`, { name: name.trim() }); refresh(); },
        remove: async (listId: string) => {
            await apiClient.delete(`/api/users/me/lists/${listId}`);
            refresh(listId);
            void qc.invalidateQueries({ queryKey: ["clip-state"] });
        },
        setMember: async (listId: string, clipId: string, on: boolean) => {
            const before = patchState(qc, clipId, s => ({ ...s, list_ids: on ? [...new Set([...s.list_ids, listId])] : s.list_ids.filter(id => id !== listId) }));
            try {
                await (on ? apiClient.put : apiClient.delete)(`/api/users/me/lists/${listId}/items/${clipId}`);
            }
            catch (e) {
                qc.setQueryData(stateKey(clipId), before);
                throw e;
            }
            finally {
                refresh(listId);
            }
        },
    };
}

export function useHistoryActions() {
    const qc = useQueryClient();
    const done = () => qc.invalidateQueries({ queryKey: ["history"] });
    return {
        remove: async (clipId: string) => { await apiClient.delete(`/api/users/me/history/${clipId}`); await done(); },
        clear: async () => { await apiClient.delete("/api/users/me/history"); await done(); },
    };
}

/** Vietnamese message for list errors (409 duplicate name / limits, 422 bad name); otherwise the server message. */
export function listErrorMessage(e: unknown) {
    const status = axios.isAxiosError(e) ? e.response?.status : undefined;
    if (status === 409)
        return "Tên danh sách đã tồn tại hoặc đã đạt giới hạn (50 danh sách, 500 clip mỗi danh sách).";
    if (status === 422)
        return "Tên danh sách phải có từ 1 đến 60 ký tự.";
    if (status === 404)
        return "Danh sách hoặc clip không còn tồn tại.";
    return errorMessage(e);
}

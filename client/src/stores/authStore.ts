"use client";
import { create } from "zustand";
import type { components } from "@/api-types";
type State = {
    accessToken: string | null;
    user: components["schemas"]["UserMe"] | null;
    ready: boolean;
    setAuth: (p: {
        accessToken: string;
        user: components["schemas"]["UserMe"];
    }) => void;
    setToken: (t: string) => void;
    setReady: () => void;
    logout: () => void;
};
export const useAuthStore = create<State>((set) => ({
    accessToken: null, user: null, ready: false,
    setAuth: ({ accessToken, user }) => set({ accessToken, user, ready: true }),
    setToken: (accessToken) => set({ accessToken }), setReady: () => set({ ready: true }),
    logout: () => set({ accessToken: null, user: null, ready: true }),
}));

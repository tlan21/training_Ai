"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";
type User = { id: string; username: string; email: string; role: string; preferences?: string[] };
type S = { accessToken: string | null; user: User | null; setAuth: (p: { accessToken: string; user: User }) => void; setToken: (t: string) => void; logout: () => void; };
export const useAuthStore = create<S>()(persist((set) => ({
  accessToken: null, user: null,
  setAuth: ({ accessToken, user }) => set({ accessToken, user }),
  setToken: (accessToken) => set({ accessToken }),
  logout: () => set({ accessToken: null, user: null }),
}), { name: "client-auth", partialize: (s) => ({ accessToken: s.accessToken, user: s.user }) }));

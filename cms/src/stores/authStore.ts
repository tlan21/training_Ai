import { create } from "zustand";
import { persist } from "zustand/middleware";
import { apiClient } from "../lib/apiClient";

type User = { id: string; username: string; email: string; role: string };
type State = {
  accessToken: string | null;
  user: User | null;
  setAuth: (p: { accessToken: string; user: User }) => void;
  setToken: (t: string) => void;
  setUser: (u: User | null) => void;
  logout: () => void;
};
export const useAuthStore = create<State>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      setAuth: ({ accessToken, user }) => set({ accessToken, user }),
      setToken: (accessToken) => set({ accessToken }),
      setUser: (user) => set({ user }),
      logout: () => {
        apiClient.post("/api/auth/logout").catch(() => {});
        set({ accessToken: null, user: null });
      },
    }),
    { name: "cms-auth", partialize: (s) => ({ accessToken: s.accessToken, user: s.user }) },
  ),
);

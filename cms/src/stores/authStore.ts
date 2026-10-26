import { create } from "zustand";
import type { components } from "../api-types";
import { queryClient } from "../lib/queryClient";

type User = components["schemas"]["User"];
type State = {
  accessToken: string | null;
  user: User | null;
  ready: boolean;
  setAuth: (p: { accessToken: string; user: User }) => void;
  setToken: (t: string) => void;
  setReady: () => void;
  logout: () => void;
};

localStorage.removeItem("cms-auth");
sessionStorage.removeItem("cms-auth");

export const useAuthStore = create<State>((set) => ({
  accessToken: null, user: null, ready: false,
  setAuth: ({ accessToken, user }) => {
    localStorage.removeItem("cms-signed-out");
    sessionStorage.setItem("cms-session-active", "1");
    set({ accessToken, user, ready: true });
  },
  setToken: (accessToken) => set({ accessToken }),
  setReady: () => set({ ready: true }),
  logout: () => {
    localStorage.setItem("cms-signed-out", "1");
    sessionStorage.removeItem("cms-session-active");
    set({ accessToken: null, user: null, ready: true });
    queryClient.clear();
  },
}));

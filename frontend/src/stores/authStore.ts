import { create } from "zustand";
import { api } from "@/services/api";

export interface User {
  id: string;
  username: string;
  email: string;
  role: "admin" | "member" | "viewer";
  allowed_repos: string[];
  allowed_channels: string[];
  allowed_db_tables: string[];
  is_active: boolean;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;

  signup: (username: string, email: string, password: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loadFromStorage: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isLoading: false,
  error: null,

  signup: async (username, email, password) => {
    set({ isLoading: true, error: null });
    try {
      const data = await api<{ access_token: string; user: User }>(
        "/api/auth/signup",
        { method: "POST", body: { username, email, password } }
      );
      localStorage.setItem("token", data.access_token);
      set({ user: data.user, token: data.access_token, isLoading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Signup failed",
        isLoading: false,
      });
      throw err;
    }
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const data = await api<{ access_token: string; user: User }>(
        "/api/auth/login",
        { method: "POST", body: { email, password } }
      );
      localStorage.setItem("token", data.access_token);
      set({ user: data.user, token: data.access_token, isLoading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Login failed",
        isLoading: false,
      });
      throw err;
    }
  },

  logout: () => {
    localStorage.removeItem("token");
    set({ user: null, token: null, error: null });
  },

  loadFromStorage: async () => {
    const token = localStorage.getItem("token");
    if (!token) return;

    set({ isLoading: true });
    try {
      const user = await api<User>("/api/auth/me", { token });
      set({ user, token, isLoading: false });
    } catch {
      localStorage.removeItem("token");
      set({ user: null, token: null, isLoading: false });
    }
  },
}));

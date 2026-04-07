import { create } from "zustand";
import { api } from "@/services/api";

export interface User {
  id: string;
  username: string;
  email: string;
  role: "admin" | "member" | "viewer";
  status: "pending" | "active" | "rejected";
  allowed_repos: string[];
  allowed_channels: string[];
  allowed_db_tables: string[];
  is_active: boolean;
}

interface AuthState {
  user: User | null;
  token: string | null;
  pendingToken: string | null;
  isLoading: boolean;
  error: string | null;

  signup: (username: string, email: string, password: string, teamCode: string) => Promise<"active" | "pending">;
  login: (email: string, password: string) => Promise<"active" | "pending">;
  logout: () => void;
  loadFromStorage: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  pendingToken: null,
  isLoading: false,
  error: null,

  signup: async (username, email, password, teamCode) => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/auth/signup`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, email, password, team_code: teamCode }),
        }
      );
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.message || "Signup failed");
      }

      // Check if pending (team mode) or active (solo mode)
      if (data.status === "pending") {
        localStorage.setItem("pendingToken", data.pending_token);
        set({ pendingToken: data.pending_token, isLoading: false });
        return "pending";
      }

      // Active — normal login
      localStorage.setItem("token", data.access_token);
      set({ user: data.user, token: data.access_token, isLoading: false });
      return "active";
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Signup failed", isLoading: false });
      throw err;
    }
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/auth/login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        }
      );
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.message || "Login failed");
      }

      // Check if pending
      if (data.status === "pending") {
        localStorage.setItem("pendingToken", data.pending_token);
        set({ pendingToken: data.pending_token, isLoading: false });
        return "pending";
      }

      localStorage.setItem("token", data.access_token);
      set({ user: data.user, token: data.access_token, isLoading: false });
      return "active";
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Login failed", isLoading: false });
      throw err;
    }
  },

  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("pendingToken");
    set({ user: null, token: null, pendingToken: null, error: null });
  },

  loadFromStorage: async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      const pending = localStorage.getItem("pendingToken");
      if (pending) set({ pendingToken: pending });
      return;
    }

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

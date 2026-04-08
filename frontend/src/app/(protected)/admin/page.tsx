"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Bot } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import AdminPanel from "@/components/admin/AdminPanel";

export default function AdminPage() {
  const router = useRouter();
  const { user, token, loadFromStorage } = useAuthStore();

  useEffect(() => {
    if (!token) {
      loadFromStorage().then(() => {
        const state = useAuthStore.getState();
        if (!state.token) router.push("/login");
        else if (state.user?.role !== "admin") router.push("/chat");
      });
    } else if (user && user.role !== "admin") {
      router.push("/chat");
    }
  }, [token, user, loadFromStorage, router]);

  if (!user || user.role !== "admin") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-pulse flex items-center gap-2 text-text-muted">
          <Bot className="w-5 h-5" />
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-background">
      <AdminPanel />
    </div>
  );
}

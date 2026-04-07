"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bot, LogOut, Shield, Plus } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useChatStore } from "@/stores/chatStore";
import ModelBadge from "@/components/model/ModelBadge";

export default function Header() {
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const newConversation = useChatStore((s) => s.newConversation);
  const selectedModelId = useChatStore((s) => s.selectedModelId);

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  return (
    <header className="h-14 border-b border-border bg-panel/50 backdrop-blur-xl flex items-center px-4 gap-3 shrink-0">
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2 mr-2">
        <div className="w-7 h-7 rounded-lg bg-cta/20 flex items-center justify-center">
          <Bot className="w-4 h-4 text-cta" />
        </div>
        <span className="text-sm font-semibold hidden sm:block">ContextAI</span>
      </Link>

      {/* New conversation */}
      <button
        onClick={() => newConversation()}
        className="p-1.5 rounded-lg hover:bg-panel-secondary/50 text-text-muted hover:text-foreground transition-colors cursor-pointer"
        title="New conversation"
      >
        <Plus className="w-4 h-4" />
      </button>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Model badge */}
      {selectedModelId && <ModelBadge />}

      {/* Admin link */}
      {user?.role === "admin" && (
        <Link
          href="/admin"
          className="p-1.5 rounded-lg hover:bg-panel-secondary/50 text-text-muted hover:text-foreground transition-colors"
          title="Admin panel"
        >
          <Shield className="w-4 h-4" />
        </Link>
      )}

      {/* User info + logout */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-muted hidden sm:block">
          {user?.username}
          <span className="ml-1 text-cta/70">({user?.role})</span>
        </span>
        <button
          onClick={handleLogout}
          className="p-1.5 rounded-lg hover:bg-panel-secondary/50 text-text-muted hover:text-foreground transition-colors cursor-pointer"
          title="Log out"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}

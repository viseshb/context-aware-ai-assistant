"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Bot, ChevronLeft, ChevronRight, LayoutDashboard, LogOut, MessageSquare, Shield } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useChatStore } from "@/stores/chatStore";

type NavItem = {
  label: string;
  href: string;
  icon: typeof MessageSquare;
  onClick?: () => void;
  active?: boolean;
};

export default function ProtectedSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const { messages, isStreaming, newConversation } = useChatStore();
  const [collapsed, setCollapsed] = useState(false);
  const [confirmHome, setConfirmHome] = useState(false);
  const hasActiveSession = messages.length > 0 || isStreaming;

  useEffect(() => {
    const stored = window.localStorage.getItem("contextai.sidebar.collapsed");
    if (stored) {
      setCollapsed(stored === "true");
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem("contextai.sidebar.collapsed", String(collapsed));
  }, [collapsed]);

  const handleHome = () => {
    if (hasActiveSession) {
      setConfirmHome(true);
      return;
    }
    newConversation();
    router.push("/chat");
  };

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  const navItems: NavItem[] = [
    {
      label: "Chat",
      href: "/chat",
      icon: MessageSquare,
      onClick: handleHome,
      active: pathname === "/chat",
    },
    {
      label: "Dashboard",
      href: "/dashboard",
      icon: LayoutDashboard,
      active: pathname === "/dashboard",
    },
  ];

  if (user?.role === "admin") {
    navItems.push({
      label: "Admin",
      href: "/admin",
      icon: Shield,
      active: pathname === "/admin",
    });
  }

  return (
    <>
      <aside
        className={`relative flex h-screen shrink-0 flex-col border-r border-border bg-panel/60 backdrop-blur-xl transition-[width] duration-300 ${
          collapsed ? "w-24" : "w-72"
        }`}
      >
        <div className="absolute inset-y-0 right-0 w-px bg-gradient-to-b from-transparent via-cta/20 to-transparent" />

        <div className={`flex ${collapsed ? "flex-col items-center gap-4 px-0 py-5" : "items-center gap-3 px-4 py-4"}`}>
          <Link href="/" className={`flex ${collapsed ? "items-center justify-center" : "min-w-0 items-center gap-3"}`}>
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-cta/15 shadow-[0_0_30px_rgba(34,197,94,0.14)]">
              <Bot className="h-5 w-5 text-cta" />
            </div>
            {!collapsed && (
              <div className="min-w-0">
                <div className="text-sm font-semibold text-foreground">ContextAI</div>
                <div className="text-xs text-text-muted">Workspace navigation</div>
              </div>
            )}
          </Link>

          <button
            onClick={() => setCollapsed((value) => !value)}
            className={`flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-panel-secondary/30 text-text-muted transition-colors hover:text-foreground ${
              collapsed ? "" : "ml-auto"
            }`}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        {!collapsed && (
          <div className="mx-4 mb-4 rounded-2xl border border-border bg-background/30 p-4">
            <div className="text-[11px] uppercase tracking-[0.24em] text-text-muted">Current user</div>
            <div className="mt-2 text-sm font-semibold text-foreground">{user?.username}</div>
            <div className="mt-1 inline-flex rounded-full bg-cta/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-cta">
              {user?.role}
            </div>
          </div>
        )}

        <nav className={`flex-1 space-y-2 ${collapsed ? "px-0 py-2" : "px-3"}`}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const buttonClass = `group flex items-center rounded-2xl text-sm transition-colors ${
              collapsed ? "mx-auto h-12 w-12 justify-center px-0 py-0" : "w-full gap-3 px-3 py-3"
            } ${
              item.active
                ? "bg-cta/12 text-foreground shadow-[inset_0_0_0_1px_rgba(34,197,94,0.18)]"
                : "text-text-muted hover:bg-panel-secondary/35 hover:text-foreground"
            }`;

            if (item.onClick) {
              return (
                <button key={item.label} onClick={item.onClick} className={buttonClass}>
                  <Icon className={`h-4 w-4 shrink-0 ${item.active ? "text-cta" : ""}`} />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </button>
              );
            }

            return (
              <Link key={item.label} href={item.href} className={buttonClass}>
                <Icon className={`h-4 w-4 shrink-0 ${item.active ? "text-cta" : ""}`} />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        <div className={`mt-auto ${collapsed ? "px-0 py-4" : "p-3"}`}>
          <button
            onClick={handleLogout}
            className={`flex items-center rounded-2xl border border-border bg-panel-secondary/20 text-sm text-text-muted transition-colors hover:text-foreground ${
              collapsed ? "mx-auto h-12 w-12 justify-center px-0 py-0" : "w-full gap-3 px-3 py-3"
            }`}
          >
            <LogOut className="h-4 w-4 shrink-0" />
            {!collapsed && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {confirmHome && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 px-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-3xl border border-border bg-panel/95 p-6 shadow-[0_30px_120px_rgba(2,6,23,0.45)]">
            <div className="text-lg font-semibold text-foreground">Leave the current chat?</div>
            <p className="mt-2 text-sm leading-relaxed text-text-muted">
              Going home will clear the active session and take you back to the chat home screen.
            </p>
            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => setConfirmHome(false)}
                className="rounded-xl border border-border px-4 py-2 text-sm text-text-muted transition-colors hover:text-foreground"
              >
                No
              </button>
              <button
                onClick={() => {
                  setConfirmHome(false);
                  newConversation();
                  router.push("/chat");
                }}
                className="rounded-xl bg-cta px-4 py-2 text-sm font-medium text-background transition-colors hover:bg-cta-hover"
              >
                Yes
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

"use client";

import { useState, useEffect } from "react";
import { Users, ScrollText, Activity, Shield } from "lucide-react";
import { useAuthStore, type User } from "@/stores/authStore";
import { api } from "@/services/api";

interface AuditLog {
  id: number;
  timestamp: string;
  event_type: string;
  username: string;
  tool_name: string;
  details: string;
}

export default function AdminPanel() {
  const token = useAuthStore((s) => s.token);
  const [tab, setTab] = useState<"users" | "audit" | "status">("users");
  const [users, setUsers] = useState<User[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [stats, setStats] = useState<Record<string, unknown>>({});
  const [status, setStatus] = useState<Record<string, unknown>>({});

  useEffect(() => {
    if (!token) return;
    loadUsers();
    loadAudit();
    loadStatus();
  }, [token]);

  const loadUsers = async () => {
    try {
      const data = await api<User[]>("/api/admin/users", { token: token! });
      setUsers(data);
    } catch {}
  };

  const loadAudit = async () => {
    try {
      const data = await api<{ logs: AuditLog[]; stats: Record<string, unknown> }>(
        "/api/admin/audit-logs",
        { token: token! }
      );
      setLogs(data.logs);
      setStats(data.stats);
    } catch {}
  };

  const loadStatus = async () => {
    try {
      const data = await api<Record<string, unknown>>("/api/admin/status", { token: token! });
      setStatus(data);
    } catch {}
  };

  const updateUser = async (userId: string, updates: Partial<User>) => {
    try {
      await api(`/api/admin/users/${userId}`, {
        method: "PUT", body: updates, token: token!,
      });
      loadUsers();
    } catch {}
  };

  const TABS = [
    { id: "users" as const, label: "Users", icon: Users },
    { id: "audit" as const, label: "Audit Log", icon: ScrollText },
    { id: "status" as const, label: "System", icon: Activity },
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Shield className="w-6 h-6 text-cta" />
        <h1 className="text-2xl font-bold">Admin Panel</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 p-1 glass rounded-xl w-fit">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
              tab === id ? "bg-cta text-background" : "text-text-muted hover:text-foreground"
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "users" && (
        <div className="space-y-3">
          {users.map((user) => (
            <div key={user.id} className="glass rounded-xl p-4 flex flex-col sm:flex-row sm:items-center gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{user.username}</span>
                  <span className="text-xs text-text-muted">{user.email}</span>
                </div>
                <div className="flex flex-wrap gap-2 mt-2">
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    user.role === "admin" ? "bg-cta/20 text-cta" :
                    user.role === "member" ? "bg-blue-500/20 text-blue-400" :
                    "bg-panel-secondary text-text-muted"
                  }`}>
                    {user.role}
                  </span>
                  {user.allowed_repos.length > 0 && (
                    <span className="text-xs text-text-muted">
                      Repos: {user.allowed_repos.join(", ")}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                {user.role !== "admin" && (
                  <select
                    value={user.role}
                    onChange={(e) => updateUser(user.id, { role: e.target.value } as Partial<User>)}
                    className="text-xs bg-panel-secondary border border-border rounded px-2 py-1 text-foreground cursor-pointer"
                  >
                    <option value="viewer">Viewer</option>
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                  </select>
                )}
              </div>
            </div>
          ))}
          {users.length === 0 && (
            <p className="text-text-muted text-center py-8">No users found</p>
          )}
        </div>
      )}

      {tab === "audit" && (
        <div>
          {/* Stats */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            {Object.entries(stats).map(([key, value]) => (
              <div key={key} className="glass rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-cta">{String(value)}</div>
                <div className="text-xs text-text-muted mt-1">{key.replace(/_/g, " ")}</div>
              </div>
            ))}
          </div>

          {/* Log entries */}
          <div className="glass rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-3 py-2 text-left text-xs text-text-muted">Time</th>
                    <th className="px-3 py-2 text-left text-xs text-text-muted">Event</th>
                    <th className="px-3 py-2 text-left text-xs text-text-muted">User</th>
                    <th className="px-3 py-2 text-left text-xs text-text-muted">Tool</th>
                    <th className="px-3 py-2 text-left text-xs text-text-muted">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id} className="border-b border-border/50 hover:bg-panel-secondary/20">
                      <td className="px-3 py-2 text-xs text-text-muted font-mono">
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        <span className="px-1.5 py-0.5 rounded bg-panel-secondary text-foreground">
                          {log.event_type}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-xs">{log.username}</td>
                      <td className="px-3 py-2 text-xs font-mono text-cta">{log.tool_name}</td>
                      <td className="px-3 py-2 text-xs text-text-muted max-w-xs truncate">
                        {log.details}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {logs.length === 0 && (
              <p className="text-text-muted text-center py-8">No audit events yet</p>
            )}
          </div>
        </div>
      )}

      {tab === "status" && (
        <div className="space-y-4">
          {Object.entries(status).map(([section, data]) => (
            <div key={section} className="glass rounded-xl p-4">
              <h3 className="font-semibold mb-3 capitalize">{section}</h3>
              <pre className="text-xs text-text-muted font-mono bg-background rounded p-3 overflow-x-auto">
                {JSON.stringify(data, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

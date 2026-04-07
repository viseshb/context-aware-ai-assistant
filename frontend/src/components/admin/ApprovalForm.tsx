"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { UserCheck, UserX, Loader2, CheckCircle, AlertCircle, Bot } from "lucide-react";

interface PendingUser {
  user_id: string;
  username: string;
  email: string;
  created_at: string;
  action: string;
}

export default function ApprovalForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const action = searchParams.get("action") || "approve";

  const [user, setUser] = useState<PendingUser | null>(null);
  const [role, setRole] = useState("member");
  const [repos, setRepos] = useState("*");
  const [channels, setChannels] = useState("*");
  const [tables, setTables] = useState("*");
  const [reason, setReason] = useState("");
  const [status, setStatus] = useState<"loading" | "ready" | "submitting" | "done" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("No approval token provided");
      return;
    }
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/admin/approve/verify?token=${token}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.error) {
          setStatus("error");
          setMessage(data.message || "Invalid token");
        } else {
          setUser(data);
          setStatus("ready");
        }
      })
      .catch(() => {
        setStatus("error");
        setMessage("Failed to verify token");
      });
  }, [token]);

  const handleApprove = async () => {
    setStatus("submitting");
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/admin/approve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            token,
            role,
            allowed_repos: repos.split(",").map((s) => s.trim()),
            allowed_channels: channels.split(",").map((s) => s.trim()),
            allowed_db_tables: tables.split(",").map((s) => s.trim()),
          }),
        }
      );
      const data = await res.json();
      setStatus("done");
      setMessage(data.message || "User approved!");
    } catch {
      setStatus("error");
      setMessage("Failed to approve user");
    }
  };

  const handleReject = async () => {
    setStatus("submitting");
    try {
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/admin/reject`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, reason }),
        }
      );
      setStatus("done");
      setMessage("User rejected.");
    } catch {
      setStatus("error");
      setMessage("Failed to reject user");
    }
  };

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-6 h-6 text-cta animate-spin" />
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <div className="glass rounded-2xl p-8 max-w-md text-center">
          <AlertCircle className="w-12 h-12 text-error mx-auto mb-4" />
          <h1 className="text-xl font-bold mb-2">Error</h1>
          <p className="text-text-muted">{message}</p>
        </div>
      </div>
    );
  }

  if (status === "done") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <div className="glass rounded-2xl p-8 max-w-md text-center">
          <CheckCircle className="w-12 h-12 text-cta mx-auto mb-4" />
          <h1 className="text-xl font-bold mb-2">Done</h1>
          <p className="text-text-muted">{message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-2xl p-8 w-full max-w-lg"
      >
        <div className="text-center mb-6">
          <Bot className="w-8 h-8 text-cta mx-auto mb-3" />
          <h1 className="text-2xl font-bold">
            {action === "reject" ? "Reject User" : "Approve User"}
          </h1>
        </div>

        {/* User info */}
        <div className="glass rounded-xl p-4 mb-6">
          <div className="text-sm space-y-1">
            <p><span className="text-text-muted">Username:</span> <span className="font-semibold">{user?.username}</span></p>
            <p><span className="text-text-muted">Email:</span> {user?.email}</p>
            <p><span className="text-text-muted">Signed up:</span> {user?.created_at ? new Date(user.created_at).toLocaleString() : "Unknown"}</p>
          </div>
        </div>

        {action === "reject" ? (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Reason (optional)</label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 bg-panel-secondary/30 border border-border rounded-lg text-foreground placeholder:text-text-muted/50 focus:outline-none focus:border-error/50 resize-none"
                placeholder="Why are you rejecting this request?"
              />
            </div>
            <button
              onClick={handleReject}
              disabled={status === "submitting"}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-error hover:bg-error/80 text-white font-semibold rounded-lg transition-colors cursor-pointer"
            >
              {status === "submitting" ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserX className="w-4 h-4" />}
              Reject User
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full px-3 py-2.5 bg-panel-secondary/30 border border-border rounded-lg text-foreground focus:outline-none focus:border-cta/50 cursor-pointer"
              >
                <option value="member">Member</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">GitHub Repos (comma-separated, * = all)</label>
              <input
                value={repos}
                onChange={(e) => setRepos(e.target.value)}
                className="w-full px-3 py-2 bg-panel-secondary/30 border border-border rounded-lg text-foreground font-mono text-sm focus:outline-none focus:border-cta/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Slack Channels</label>
              <input
                value={channels}
                onChange={(e) => setChannels(e.target.value)}
                className="w-full px-3 py-2 bg-panel-secondary/30 border border-border rounded-lg text-foreground font-mono text-sm focus:outline-none focus:border-cta/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">DB Tables</label>
              <input
                value={tables}
                onChange={(e) => setTables(e.target.value)}
                className="w-full px-3 py-2 bg-panel-secondary/30 border border-border rounded-lg text-foreground font-mono text-sm focus:outline-none focus:border-cta/50"
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleApprove}
                disabled={status === "submitting"}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-cta hover:bg-cta-hover text-background font-semibold rounded-lg transition-colors cursor-pointer"
              >
                {status === "submitting" ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserCheck className="w-4 h-4" />}
                Approve
              </button>
              <button
                onClick={() => {
                  const url = new URL(window.location.href);
                  url.searchParams.set("action", "reject");
                  window.location.href = url.toString();
                }}
                className="px-4 py-2.5 border border-error/30 text-error hover:bg-error/10 rounded-lg transition-colors cursor-pointer"
              >
                Reject
              </button>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}

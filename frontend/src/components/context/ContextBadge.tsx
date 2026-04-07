"use client";

import { GitBranch, MessageSquare, Database } from "lucide-react";

const SOURCE_CONFIG: Record<string, { icon: typeof GitBranch; color: string; label: string }> = {
  github: { icon: GitBranch, color: "text-gray-400 bg-gray-500/10", label: "GitHub" },
  slack: { icon: MessageSquare, color: "text-purple-400 bg-purple-500/10", label: "Slack" },
  db: { icon: Database, color: "text-blue-400 bg-blue-500/10", label: "Database" },
  postgres: { icon: Database, color: "text-blue-400 bg-blue-500/10", label: "Database" },
};

interface ContextBadgeProps {
  type: string;
  detail?: string;
}

export default function ContextBadge({ type, detail }: ContextBadgeProps) {
  const config = SOURCE_CONFIG[type] || SOURCE_CONFIG.github;
  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${config.color}`}
    >
      <Icon className="w-3 h-3" />
      via {config.label}
      {detail && <span className="opacity-70">({detail})</span>}
    </span>
  );
}

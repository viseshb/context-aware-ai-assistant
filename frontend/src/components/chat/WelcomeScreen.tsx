"use client";

import { Bot, ArrowRight, GitBranch, MessageSquare, Database, CheckCircle, AlertTriangle, XCircle } from "lucide-react";

interface SourceCard {
  type: string;
  label: string;
  connected: boolean;
  user_tools: number;
  total_tools: number;
  detail: string;
}

interface WelcomeScreenProps {
  onContinue: () => void;
  sources?: SourceCard[];
}

const SOURCE_META: Record<string, { icon: typeof GitBranch; tone: string; iconBg: string; description: string }> = {
  github: {
    icon: GitBranch,
    tone: "text-gray-300",
    iconBg: "bg-gray-500/10",
    description: "Search repos, read files, trace commits, and inspect issues or PRs with live GitHub context.",
  },
  slack: {
    icon: MessageSquare,
    tone: "text-purple-400",
    iconBg: "bg-purple-500/10",
    description: "Pull channel history, search messages, and recover thread context from team conversations.",
  },
  postgres: {
    icon: Database,
    tone: "text-blue-400",
    iconBg: "bg-blue-500/10",
    description: "Inspect schemas and run read-only queries against PostgreSQL for metrics and operational data.",
  },
};

export default function WelcomeScreen({ onContinue, sources = [] }: WelcomeScreenProps) {
  const cards = ["github", "slack", "postgres"].map((type) => {
    const source = sources.find((item) => item.type === type);
    const meta = SOURCE_META[type];
    return {
      type,
      ...meta,
      label: source?.label || (type === "postgres" ? "PostgreSQL" : type[0].toUpperCase() + type.slice(1)),
      connected: source?.connected ?? false,
      userTools: source?.user_tools ?? 0,
      totalTools: source?.total_tools ?? 0,
      detail: source?.detail || "Source details will appear here once loaded.",
    };
  });

  return (
    <div className="flex-1 overflow-y-auto px-4 py-8 sm:py-10">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="glass rounded-2xl p-6 sm:p-8">
          <div className="w-14 h-14 rounded-2xl bg-cta/15 flex items-center justify-center mb-5">
            <Bot className="w-7 h-7 text-cta" />
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold mb-3">Context-aware answers across your tools</h1>
          <p className="text-sm sm:text-base text-text-muted leading-relaxed max-w-3xl">
            This assistant routes questions to GitHub, Slack, and PostgreSQL through live tool calls, then
            brings the answer back into one chat. Continue to open the chat workspace, then choose a model
            directly from the composer whenever you want to switch.
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-3 text-xs text-text-muted">
            <span className="px-2.5 py-1 rounded-full bg-panel-secondary/40 border border-border">
              Live GitHub, Slack, and database context
            </span>
            <span className="px-2.5 py-1 rounded-full bg-panel-secondary/40 border border-border">
              Role-aware access control
            </span>
            <span className="px-2.5 py-1 rounded-full bg-panel-secondary/40 border border-border">
              Model switching inside the chat composer
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {cards.map((card) => {
            const Icon = card.icon;
            const StatusIcon = !card.connected ? XCircle : card.userTools > 0 ? CheckCircle : AlertTriangle;
            const statusTone = !card.connected
              ? "text-text-muted/50"
              : card.userTools > 0
                ? "text-cta"
                : "text-warning";

            return (
              <div key={card.type} className="glass rounded-2xl p-5">
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div className={`w-11 h-11 rounded-xl ${card.iconBg} flex items-center justify-center`}>
                    <Icon className={`w-5 h-5 ${card.tone}`} />
                  </div>
                  <StatusIcon className={`w-4 h-4 mt-1 shrink-0 ${statusTone}`} />
                </div>

                <h2 className="text-base font-semibold mb-2">{card.label}</h2>
                <p className="text-sm text-text-muted leading-relaxed mb-4">{card.description}</p>

                <div className="text-xs text-text-muted space-y-1.5">
                  <div>{card.connected ? `${card.userTools}/${card.totalTools} tools accessible` : "Not configured"}</div>
                  <div className="text-text-muted/80">{card.detail}</div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="glass rounded-2xl p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold mb-1">Open the chat workspace</h2>
            <p className="text-sm text-text-muted">
              Continue to the main chat, pick a model from the input area, and start asking about code,
              conversations, or database context.
            </p>
          </div>

          <button
            onClick={onContinue}
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-cta text-background font-medium hover:bg-cta-hover transition-colors cursor-pointer"
          >
            Continue
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

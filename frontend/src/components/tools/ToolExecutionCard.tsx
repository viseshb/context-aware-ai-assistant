"use client";

import { useState } from "react";
import { Wrench, ChevronDown, ChevronUp, CheckCircle } from "lucide-react";

interface ToolExecutionCardProps {
  name: string;
  args: Record<string, unknown>;
  result?: string;
  durationMs?: number;
  status: "running" | "success" | "error";
}

export default function ToolExecutionCard({
  name,
  args,
  result,
  durationMs,
  status,
}: ToolExecutionCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="glass rounded-lg overflow-hidden text-xs">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-panel-secondary/30 transition-colors cursor-pointer"
      >
        {status === "running" ? (
          <span className="relative flex h-3.5 w-3.5 shrink-0 items-center justify-center">
            <span className="absolute inset-0 rounded-full border border-cta/25 animate-pulse" />
            <span className="h-2 w-2 rounded-full bg-cta shadow-[0_0_12px_rgba(34,197,94,0.4)]" />
          </span>
        ) : (
          <CheckCircle className="w-3.5 h-3.5 text-cta shrink-0" />
        )}
        <Wrench className="w-3 h-3 text-text-muted shrink-0" />
        <span className="font-mono text-cta">{name}</span>
        {durationMs !== undefined && (
          <span className="text-text-muted ml-auto mr-1">{durationMs}ms</span>
        )}
        {expanded ? (
          <ChevronUp className="w-3 h-3 text-text-muted" />
        ) : (
          <ChevronDown className="w-3 h-3 text-text-muted" />
        )}
      </button>

      {expanded && (
        <div className="px-3 pb-2 space-y-2 border-t border-border">
          <div className="pt-2">
            <span className="text-text-muted">Args: </span>
            <code className="text-foreground">{JSON.stringify(args)}</code>
          </div>
          {result && (
            <div>
              <span className="text-text-muted">Result: </span>
              <pre className="mt-1 p-2 bg-background rounded text-foreground overflow-x-auto max-h-40 overflow-y-auto">
                {result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

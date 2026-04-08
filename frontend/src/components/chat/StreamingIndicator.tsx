"use client";

import { Bot } from "lucide-react";
import { useChatStore } from "@/stores/chatStore";

export default function StreamingIndicator() {
  const streamingContent = useChatStore((s) => s.streamingContent);
  const streamingToolName = useChatStore((s) => s.streamingToolName);
  const title = streamingToolName || (streamingContent.trim() ? "Composing the answer" : "Thinking through your request");
  const subtitle = streamingToolName
    ? "Pulling live context and grounding the response."
    : streamingContent.trim()
      ? "Finalizing the response from the gathered results."
      : "Preparing the next response.";

  return (
    <div className="flex gap-3 justify-start">
      <div className="shrink-0 mt-1 relative w-8 h-8 flex items-center justify-center">
        <div className="absolute inset-0 rounded-lg bg-cta/12 border border-cta/20" />
        <div className="absolute inset-[7px] rounded-full bg-cta shadow-[0_0_20px_rgba(34,197,94,0.35)]" />
        <div className="absolute inset-[3px] rounded-full border border-cta/25 animate-pulse" />
        <Bot className="relative z-10 w-3.5 h-3.5 text-cta" />
      </div>
      <div className="max-w-[75%] px-4 py-3 bg-panel/80 border border-cta/15 rounded-2xl rounded-bl-md text-sm text-foreground shadow-[0_0_0_1px_rgba(34,197,94,0.03)]">
        <div className="flex items-center gap-2">
          <span className="font-medium text-foreground">{title}</span>
          <span className="rounded-full border border-cta/20 bg-cta/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-cta/85">
            live
          </span>
        </div>
        <p className="mt-1 text-xs leading-relaxed text-text-muted">{subtitle}</p>

        {streamingContent && (
          <div className="mt-3 whitespace-pre-wrap rounded-xl border border-border/80 bg-background/30 px-3 py-2.5 text-sm leading-relaxed text-foreground">
            {streamingContent}
          </div>
        )}

        <div className="mt-3 flex items-center gap-1.5">
          {[0, 1, 2].map((index) => (
            <span
              key={index}
              className="h-2 w-2 rounded-full bg-cta/80 animate-pulse"
              style={{ animationDelay: `${index * 180}ms` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

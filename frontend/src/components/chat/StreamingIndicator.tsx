"use client";

import { Bot } from "lucide-react";
import { useChatStore } from "@/stores/chatStore";

export default function StreamingIndicator() {
  const streamingContent = useChatStore((s) => s.streamingContent);

  return (
    <div className="flex gap-3 justify-start">
      <div className="shrink-0 w-8 h-8 rounded-lg bg-cta/15 flex items-center justify-center mt-1">
        <Bot className="w-4 h-4 text-cta animate-pulse" />
      </div>
      <div className="max-w-[75%] px-4 py-3 bg-panel/80 border border-border rounded-2xl rounded-bl-md text-sm leading-relaxed whitespace-pre-wrap text-foreground">
        {streamingContent}
        <span className="inline-block w-2 h-4 bg-cta/60 ml-0.5 animate-pulse rounded-sm" />
      </div>
    </div>
  );
}

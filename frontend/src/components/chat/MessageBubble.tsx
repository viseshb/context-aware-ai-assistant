"use client";

import { Bot, User } from "lucide-react";
import type { ChatMessage } from "@/stores/chatStore";
import MarkdownRenderer from "@/components/rich/MarkdownRenderer";
import ContextBadge from "@/components/context/ContextBadge";

interface MessageBubbleProps {
  message: ChatMessage;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {/* Avatar (assistant) */}
      {!isUser && (
        <div className="shrink-0 w-8 h-8 rounded-lg bg-cta/15 flex items-center justify-center mt-1">
          <Bot className="w-4 h-4 text-cta" />
        </div>
      )}

      <div className={`max-w-[75%] ${isUser ? "" : ""}`}>
        {/* Message content */}
        <div
          className={`px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-cta/10 border border-cta/20 rounded-2xl rounded-br-md"
              : "bg-panel/80 border border-border rounded-2xl rounded-bl-md"
          }`}
        >
          {isUser ? (
            <span className="whitespace-pre-wrap">{message.content}</span>
          ) : (
            <MarkdownRenderer content={message.content} />
          )}
        </div>

        {/* Context badges */}
        {message.contextSources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1.5 ml-1">
            {message.contextSources.map((src, i) => (
              <ContextBadge key={i} type={src.type} detail={src.detail} />
            ))}
          </div>
        )}
      </div>

      {/* Avatar (user) */}
      {isUser && (
        <div className="shrink-0 w-8 h-8 rounded-lg bg-panel-secondary/50 flex items-center justify-center mt-1">
          <User className="w-4 h-4 text-text-muted" />
        </div>
      )}
    </div>
  );
}

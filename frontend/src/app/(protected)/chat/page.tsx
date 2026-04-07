"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Bot, AlertTriangle, GitBranch, MessageSquare, Database, CheckCircle, XCircle } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useChatStore } from "@/stores/chatStore";
import { ChatWebSocket, type WSMessage } from "@/services/websocket";
import { api } from "@/services/api";
import Header from "@/components/layout/Header";
import WelcomeScreen from "@/components/chat/WelcomeScreen";
import ChatArea from "@/components/chat/ChatArea";
import InputBar from "@/components/chat/InputBar";

interface ContextSource {
  type: string;
  label: string;
  connected: boolean;
  user_tools: number;
  total_tools: number;
  status: string;
  detail: string;
}

interface ContextStatus {
  sources: ContextSource[];
  role: string;
  role_message: string;
  total_tools: number;
  user_accessible_tools: number;
}

const SOURCE_ICONS: Record<string, typeof GitBranch> = {
  github: GitBranch,
  slack: MessageSquare,
  postgres: Database,
};

export default function ChatPage() {
  const router = useRouter();
  const { user, token, isLoading, loadFromStorage } = useAuthStore();
  const {
    selectedModelId,
    conversationId,
    isStreaming,
    messages,
    addUserMessage,
    startStreaming,
    appendStreamChunk,
    finishStreaming,
    setStreamError,
  } = useChatStore();

  const wsRef = useRef<ChatWebSocket | null>(null);
  const [contextStatus, setContextStatus] = useState<ContextStatus | null>(null);

  // Auth guard
  useEffect(() => {
    if (!token && !isLoading) {
      loadFromStorage().then(() => {
        const s = useAuthStore.getState();
        if (!s.token) router.push("/login");
      });
    }
  }, [token, isLoading, loadFromStorage, router]);

  // Fetch context sources
  useEffect(() => {
    if (!token) return;
    api<ContextStatus>("/api/context/sources", { token })
      .then(setContextStatus)
      .catch(() => {});
  }, [token]);

  // WebSocket connection
  useEffect(() => {
    if (!token) return;

    const ws = new ChatWebSocket(token);
    wsRef.current = ws;

    const unsub = ws.onMessage((msg: WSMessage) => {
      switch (msg.type) {
        case "stream_start":
          startStreaming();
          break;
        case "stream_chunk":
          if (msg.content) appendStreamChunk(msg.content);
          break;
        case "stream_end":
          finishStreaming(msg.context_sources || [], selectedModelId || "");
          break;
        case "error":
          setStreamError(msg.message || "Unknown error");
          break;
      }
    });

    ws.connect();

    return () => {
      unsub();
      ws.disconnect();
    };
  }, [token, selectedModelId, startStreaming, appendStreamChunk, finishStreaming, setStreamError]);

  const handleSend = useCallback(
    (message: string) => {
      if (!selectedModelId || !wsRef.current) return;
      addUserMessage(message);
      wsRef.current.sendChatMessage(selectedModelId, message, conversationId);
    },
    [selectedModelId, conversationId, addUserMessage]
  );

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-pulse flex items-center gap-2 text-text-muted">
          <Bot className="w-5 h-5" />
          Loading...
        </div>
      </div>
    );
  }

  const showWelcome = !selectedModelId;

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />

      {/* Role/access banner */}
      {contextStatus?.role_message && (
        <div className="bg-warning/10 border-b border-warning/20 px-4 py-2.5 flex items-center gap-2 text-sm text-warning">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {contextStatus.role_message}
        </div>
      )}

      {/* Data source status bar */}
      {contextStatus && !showWelcome && (
        <div className="border-b border-border px-4 py-2 flex items-center gap-4 text-xs">
          <span className="text-text-muted">Sources:</span>
          {contextStatus.sources.map((src) => {
            const Icon = SOURCE_ICONS[src.type] || Database;
            return (
              <div key={src.type} className="flex items-center gap-1.5">
                {src.connected && src.user_tools > 0 ? (
                  <CheckCircle className="w-3 h-3 text-cta" />
                ) : src.connected ? (
                  <AlertTriangle className="w-3 h-3 text-warning" />
                ) : (
                  <XCircle className="w-3 h-3 text-text-muted/50" />
                )}
                <Icon className="w-3 h-3 text-text-muted" />
                <span className={src.connected && src.user_tools > 0 ? "text-foreground" : "text-text-muted/50"}>
                  {src.label}
                </span>
                {src.connected && (
                  <span className="text-text-muted">({src.user_tools}/{src.total_tools})</span>
                )}
              </div>
            );
          })}
          <span className="ml-auto text-text-muted">
            Role: <span className="text-cta">{contextStatus.role}</span>
          </span>
        </div>
      )}

      {showWelcome ? (
        <WelcomeScreen />
      ) : (
        <>
          {messages.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-text-muted text-sm">
              Start a conversation with {selectedModelId}
            </div>
          ) : (
            <ChatArea />
          )}
          <InputBar onSend={handleSend} disabled={isStreaming} />
        </>
      )}
    </div>
  );
}

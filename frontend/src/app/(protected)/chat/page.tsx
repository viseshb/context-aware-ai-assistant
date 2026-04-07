"use client";

import { useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Bot } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useChatStore } from "@/stores/chatStore";
import { ChatWebSocket, type WSMessage } from "@/services/websocket";
import Header from "@/components/layout/Header";
import WelcomeScreen from "@/components/chat/WelcomeScreen";
import ChatArea from "@/components/chat/ChatArea";
import InputBar from "@/components/chat/InputBar";

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

  // Auth guard
  useEffect(() => {
    if (!token && !isLoading) {
      loadFromStorage().then(() => {
        const s = useAuthStore.getState();
        if (!s.token) router.push("/login");
      });
    }
  }, [token, isLoading, loadFromStorage, router]);

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
          finishStreaming(
            msg.context_sources || [],
            selectedModelId || ""
          );
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

  // Send message handler
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

"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Bot, AlertTriangle, GitBranch, MessageSquare, Database, CheckCircle, XCircle } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useChatStore } from "@/stores/chatStore";
import { ChatWebSocket, type WSMessage } from "@/services/websocket";
import { api } from "@/services/api";
import WelcomeScreen from "@/components/chat/WelcomeScreen";
import ChatArea from "@/components/chat/ChatArea";
import InputBar from "@/components/chat/InputBar";
import { ALL_MODELS, type ModelMeta } from "@/config/models";
import type { ToolCall, ChatMetrics } from "@/stores/chatStore";

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

interface ApiModel {
  id: string;
  name: string;
  provider: string;
  tier: "free" | "paid";
  available: boolean;
  supports_tools: boolean;
  supports_streaming: boolean;
}

interface ModelsResponse {
  models: ApiModel[];
}

const SOURCE_ICONS: Record<string, typeof GitBranch> = {
  github: GitBranch,
  slack: MessageSquare,
  postgres: Database,
};

function mapAvailableModels(models: ApiModel[]): ModelMeta[] {
  return models
    .filter((model) => model.available)
    .map((model) => {
      const existing = ALL_MODELS.find((candidate) => candidate.id === model.id);
      if (existing) {
        return existing;
      }

      return {
        id: model.id,
        name: model.name,
        provider: model.provider,
        providerLabel: model.provider.charAt(0).toUpperCase() + model.provider.slice(1),
        tier: model.tier,
        responseTime: model.supports_streaming ? "~streaming" : "~response",
        color: "#94A3B8",
      };
    });
}

function getToolPhase(toolName?: string): string {
  if (!toolName) return "Composing the answer";
  if (toolName.startsWith("github_")) return "Checking GitHub";
  if (toolName.startsWith("slack_")) return "Checking Slack";
  if (toolName.startsWith("db_")) return "Checking PostgreSQL";
  return "Working through your request";
}

function normalizeToolCalls(payload?: WSMessage["tool_calls"]): ToolCall[] {
  return (payload || []).map((tool) => ({
    ...tool,
    status:
      tool.status === "running" || tool.status === "error" || tool.status === "success"
        ? tool.status
        : "success",
  }));
}

function normalizeMetrics(payload?: WSMessage["metrics"]): ChatMetrics | null {
  if (!payload) return null;
  return {
    model_id: payload.model_id || "",
    ttft_ms: payload.ttft_ms ?? null,
    total_time_ms: payload.total_time_ms ?? 0,
    tool_time_ms: payload.tool_time_ms ?? 0,
    tool_call_count: payload.tool_call_count ?? 0,
    input_tokens: payload.input_tokens ?? null,
    output_tokens: payload.output_tokens ?? null,
    cost_usd: payload.cost_usd ?? null,
    provider_model: payload.provider_model || "",
    response_chars: payload.response_chars ?? 0,
  };
}

export default function ChatPage() {
  const router = useRouter();
  const { user, token, isLoading, loadFromStorage } = useAuthStore();
  const {
    selectedModelId,
    conversationId,
    isStreaming,
    messages,
    hasEnteredChat,
    addUserMessage,
    startStreaming,
    appendStreamChunk,
    setStreamingToolName,
    finishStreaming,
    setStreamError,
    setSelectedModel,
    setHasEnteredChat,
  } = useChatStore();

  const wsRef = useRef<ChatWebSocket | null>(null);
  const [contextStatus, setContextStatus] = useState<ContextStatus | null>(null);
  const [availableModels, setAvailableModels] = useState<ModelMeta[]>([]);
  const [modelsLoaded, setModelsLoaded] = useState(false);

  useEffect(() => {
    if (!token && !isLoading) {
      loadFromStorage().then(() => {
        const state = useAuthStore.getState();
        if (!state.token) router.push("/login");
      });
    }
  }, [token, isLoading, loadFromStorage, router]);

  useEffect(() => {
    if (!token) return;
    api<ContextStatus>("/api/context/sources", { token })
      .then(setContextStatus)
      .catch(() => {});
  }, [token]);

  useEffect(() => {
    if (!token) return;
    api<ModelsResponse>("/api/models", { token })
      .then((data) => {
        const nextModels = mapAvailableModels(data.models);
        setModelsLoaded(true);
        setAvailableModels(nextModels);

        if (nextModels.length === 0) {
          setSelectedModel("");
          return;
        }

        const selectedStillValid = selectedModelId && nextModels.some((model) => model.id === selectedModelId);
        if (!selectedStillValid) {
          setSelectedModel(nextModels[0].id);
        }
      })
      .catch(() => {
        setModelsLoaded(true);
        setAvailableModels(ALL_MODELS);
        if (!selectedModelId && ALL_MODELS.length > 0) {
          setSelectedModel(ALL_MODELS[0].id);
        }
      });
  }, [token, setSelectedModel]);

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
        case "tool_call_start":
          setStreamingToolName(getToolPhase(msg.tool?.name));
          break;
        case "tool_call_result":
          setStreamingToolName("Composing the answer");
          break;
        case "stream_end":
          finishStreaming(
            msg.context_sources || [],
            selectedModelId || "",
            normalizeToolCalls(msg.tool_calls),
            normalizeMetrics(msg.metrics),
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
  }, [token, selectedModelId, startStreaming, appendStreamChunk, setStreamingToolName, finishStreaming, setStreamError]);

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

  const showIntro = !hasEnteredChat && messages.length === 0;
  const currentModel = availableModels.find((model) => model.id === selectedModelId) || null;

  return (
    <div className="flex h-full min-h-0 flex-col bg-background">

      {contextStatus?.role_message && (
        <div className="bg-warning/10 border-b border-warning/20 px-4 py-2.5 flex items-center gap-2 text-sm text-warning">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {contextStatus.role_message}
        </div>
      )}

      {showIntro ? (
        <WelcomeScreen
          onContinue={() => setHasEnteredChat(true)}
          sources={contextStatus?.sources}
        />
      ) : (
        <>
          {contextStatus && (
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

          {messages.length === 0 ? (
            <div className="flex-1 px-4 py-6">
              <div className="max-w-4xl mx-auto h-full flex items-center justify-center">
                <div className="glass rounded-2xl p-6 sm:p-8 text-center max-w-2xl">
                  <h2 className="text-xl font-semibold mb-2">Ready to start a conversation</h2>
                  <p className="text-sm text-text-muted leading-relaxed">
                    Ask about repositories, Slack discussions, or PostgreSQL data. Choose a model from the composer below,
                    then send your first prompt.
                  </p>
                  <div className="mt-4 text-xs text-text-muted">
                    {!modelsLoaded
                      ? "Loading available models..."
                      : currentModel
                        ? `Current model: ${currentModel.name}`
                        : "No model is currently available."}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <ChatArea />
          )}

          <InputBar
            onSend={handleSend}
            disabled={isStreaming}
            models={availableModels}
            modelsLoaded={modelsLoaded}
            selectedModelId={selectedModelId}
            onModelChange={setSelectedModel}
          />
        </>
      )}
    </div>
  );
}

import { create } from "zustand";

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
  duration_ms?: number;
  status: "running" | "success" | "error";
}

export interface ContextSource {
  type: string;
  detail: string;
}

export interface ChatMetrics {
  model_id: string;
  ttft_ms: number | null;
  total_time_ms: number;
  tool_time_ms: number;
  tool_call_count: number;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  provider_model: string;
  response_chars: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls: ToolCall[];
  contextSources: ContextSource[];
  timestamp: number;
  modelId?: string;
  metrics?: ChatMetrics | null;
}

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingContent: string;
  streamingToolName: string | null;
  conversationId: string;
  selectedModelId: string | null;
  hasEnteredChat: boolean;

  addUserMessage: (content: string) => void;
  startStreaming: () => void;
  appendStreamChunk: (chunk: string) => void;
  setStreamingToolName: (toolName: string | null) => void;
  addToolCall: (tool: ToolCall) => void;
  finishStreaming: (
    contextSources: ContextSource[],
    modelId: string,
    toolCalls?: ToolCall[],
    metrics?: ChatMetrics | null,
  ) => void;
  setStreamError: (error: string) => void;
  setSelectedModel: (modelId: string) => void;
  setHasEnteredChat: (value: boolean) => void;
  clearMessages: () => void;
  newConversation: () => void;
}

let msgCounter = 0;

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isStreaming: false,
  streamingContent: "",
  streamingToolName: null,
  conversationId: crypto.randomUUID(),
  selectedModelId: null,
  hasEnteredChat: false,

  addUserMessage: (content) => {
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: `msg-${++msgCounter}`,
          role: "user",
          content,
          toolCalls: [],
          contextSources: [],
          timestamp: Date.now(),
          metrics: null,
        },
      ],
    }));
  },

  startStreaming: () => {
    set({ isStreaming: true, streamingContent: "", streamingToolName: null });
  },

  appendStreamChunk: (chunk) => {
    set((state) => ({
      streamingContent: state.streamingContent + chunk,
    }));
  },

  setStreamingToolName: (toolName) => set({ streamingToolName: toolName }),

  addToolCall: (_tool) => {
    // Tool calls are accumulated during streaming and attached to the final message
    set((state) => ({
      streamingContent: state.streamingContent, // no change, just trigger re-render
    }));
  },

  finishStreaming: (contextSources, modelId, toolCalls = [], metrics = null) => {
    const { streamingContent } = get();
    set((state) => ({
      isStreaming: false,
      streamingContent: "",
      streamingToolName: null,
      messages: [
        ...state.messages,
        {
          id: `msg-${++msgCounter}`,
          role: "assistant",
          content: streamingContent,
          toolCalls,
          contextSources,
          timestamp: Date.now(),
          modelId,
          metrics,
        },
      ],
    }));
  },

  setStreamError: (error) => {
    set((state) => ({
      isStreaming: false,
      streamingContent: "",
      streamingToolName: null,
      messages: [
        ...state.messages,
        {
          id: `msg-${++msgCounter}`,
          role: "assistant",
          content: `Error: ${error}`,
          toolCalls: [],
          contextSources: [],
          timestamp: Date.now(),
          metrics: null,
        },
      ],
    }));
  },

  setSelectedModel: (modelId) => set({ selectedModelId: modelId }),
  setHasEnteredChat: (value) => set({ hasEnteredChat: value }),

  clearMessages: () => set({ messages: [], streamingContent: "", streamingToolName: null, hasEnteredChat: false }),

  newConversation: () =>
    set({
      messages: [],
      streamingContent: "",
      streamingToolName: null,
      conversationId: crypto.randomUUID(),
      hasEnteredChat: false,
    }),
}));

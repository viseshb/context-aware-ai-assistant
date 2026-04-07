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

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls: ToolCall[];
  contextSources: ContextSource[];
  timestamp: number;
  modelId?: string;
}

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingContent: string;
  conversationId: string;
  selectedModelId: string | null;

  addUserMessage: (content: string) => void;
  startStreaming: () => void;
  appendStreamChunk: (chunk: string) => void;
  addToolCall: (tool: ToolCall) => void;
  finishStreaming: (contextSources: ContextSource[], modelId: string) => void;
  setStreamError: (error: string) => void;
  setSelectedModel: (modelId: string) => void;
  clearMessages: () => void;
  newConversation: () => void;
}

let msgCounter = 0;

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isStreaming: false,
  streamingContent: "",
  conversationId: crypto.randomUUID(),
  selectedModelId: null,

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
        },
      ],
    }));
  },

  startStreaming: () => {
    set({ isStreaming: true, streamingContent: "" });
  },

  appendStreamChunk: (chunk) => {
    set((state) => ({
      streamingContent: state.streamingContent + chunk,
    }));
  },

  addToolCall: (_tool) => {
    // Tool calls are accumulated during streaming and attached to the final message
    set((state) => ({
      streamingContent: state.streamingContent, // no change, just trigger re-render
    }));
  },

  finishStreaming: (contextSources, modelId) => {
    const { streamingContent } = get();
    set((state) => ({
      isStreaming: false,
      streamingContent: "",
      messages: [
        ...state.messages,
        {
          id: `msg-${++msgCounter}`,
          role: "assistant",
          content: streamingContent,
          toolCalls: [],
          contextSources,
          timestamp: Date.now(),
          modelId,
        },
      ],
    }));
  },

  setStreamError: (error) => {
    set((state) => ({
      isStreaming: false,
      streamingContent: "",
      messages: [
        ...state.messages,
        {
          id: `msg-${++msgCounter}`,
          role: "assistant",
          content: `Error: ${error}`,
          toolCalls: [],
          contextSources: [],
          timestamp: Date.now(),
        },
      ],
    }));
  },

  setSelectedModel: (modelId) => set({ selectedModelId: modelId }),

  clearMessages: () => set({ messages: [], streamingContent: "" }),

  newConversation: () =>
    set({
      messages: [],
      streamingContent: "",
      conversationId: crypto.randomUUID(),
    }),
}));

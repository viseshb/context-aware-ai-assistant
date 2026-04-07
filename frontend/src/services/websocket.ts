const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export type WSMessageType =
  | "connected"
  | "authenticated"
  | "stream_start"
  | "stream_chunk"
  | "tool_call_start"
  | "tool_call_result"
  | "stream_end"
  | "error";

export interface WSMessage {
  type: WSMessageType;
  content?: string;
  conversation_id?: string;
  session_id?: string;
  message?: string;
  code?: string;
  tool?: { name: string; args: Record<string, unknown>; result?: unknown; duration_ms?: number };
  context_sources?: { type: string; detail: string }[];
  summary?: string | null;
  user?: { id: string; username: string; role: string };
}

type MessageHandler = (msg: WSMessage) => void;

export class ChatWebSocket {
  private ws: WebSocket | null = null;
  private handlers: MessageHandler[] = [];
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private token: string;

  constructor(token: string) {
    this.token = token;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(`${WS_URL}/api/ws/chat`);

    this.ws.onopen = () => {
      // Authenticate immediately
      this.ws?.send(JSON.stringify({ type: "auth", token: this.token }));
    };

    this.ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        this.handlers.forEach((h) => h(msg));
      } catch {
        // ignore non-JSON messages
      }
    };

    this.ws.onclose = () => {
      // Auto-reconnect after 3 seconds
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.push(handler);
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler);
    };
  }

  sendChatMessage(modelId: string, message: string, conversationId: string): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    this.ws.send(
      JSON.stringify({
        type: "chat_message",
        model_id: modelId,
        message,
        conversation_id: conversationId,
      })
    );
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

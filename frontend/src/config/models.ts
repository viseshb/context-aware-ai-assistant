export interface ModelMeta {
  id: string;
  name: string;
  provider: string;
  providerLabel: string;
  tier: "free" | "paid";
  responseTime: string;
  color: string;
}

export const ALL_MODELS: ModelMeta[] = [
  {
    id: "gemini-2.5-flash-lite",
    name: "Gemini 2.5 Flash Lite",
    provider: "google",
    providerLabel: "Google",
    tier: "free",
    responseTime: "~3s",
    color: "#4285F4",
  },
  {
    id: "nvidia/llama-4-maverick",
    name: "Llama 4 Maverick",
    provider: "nvidia",
    providerLabel: "NVIDIA",
    tier: "free",
    responseTime: "~7s",
    color: "#76B900",
  },
  {
    id: "nvidia/ministral-14b",
    name: "Ministral 14B",
    provider: "nvidia",
    providerLabel: "NVIDIA",
    tier: "free",
    responseTime: "~22s",
    color: "#76B900",
  },
  {
    id: "gemini-2.5-flash",
    name: "Gemini 2.5 Flash",
    provider: "google",
    providerLabel: "Google",
    tier: "free",
    responseTime: "~10s",
    color: "#4285F4",
  },
  {
    id: "nvidia/kimi-k2",
    name: "Kimi K2",
    provider: "nvidia",
    providerLabel: "NVIDIA",
    tier: "free",
    responseTime: "~22s",
    color: "#76B900",
  },
  {
    id: "claude-cli",
    name: "Claude CLI",
    provider: "claude-cli",
    providerLabel: "Anthropic",
    tier: "free",
    responseTime: "~24s",
    color: "#D97706",
  },
  {
    id: "gemini-3.1-flash-lite",
    name: "Gemini 3.1 Flash Lite",
    provider: "google",
    providerLabel: "Google",
    tier: "free",
    responseTime: "~25s",
    color: "#4285F4",
  },
  {
    id: "gemini-3-flash",
    name: "Gemini 3 Flash",
    provider: "google",
    providerLabel: "Google",
    tier: "free",
    responseTime: "~6s",
    color: "#4285F4",
  },
  {
    id: "claude-api",
    name: "Claude API",
    provider: "anthropic",
    providerLabel: "Anthropic",
    tier: "paid",
    responseTime: "~3s",
    color: "#D97706",
  },
  {
    id: "gpt-4.1-mini",
    name: "OpenAI GPT-4.1 Mini",
    provider: "openai",
    providerLabel: "OpenAI",
    tier: "paid",
    responseTime: "~3s",
    color: "#10A37F",
  },
];

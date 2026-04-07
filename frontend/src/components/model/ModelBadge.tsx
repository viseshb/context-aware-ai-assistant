"use client";

import { ALL_MODELS } from "@/config/models";
import { useChatStore } from "@/stores/chatStore";

export default function ModelBadge() {
  const selectedModelId = useChatStore((s) => s.selectedModelId);
  const setSelectedModel = useChatStore((s) => s.setSelectedModel);

  const model = ALL_MODELS.find((m) => m.id === selectedModelId);
  if (!model) return null;

  return (
    <button
      onClick={() => setSelectedModel("")}
      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-panel-secondary/30 border border-border hover:border-panel-secondary transition-colors cursor-pointer text-sm"
      title="Click to change model"
    >
      <div
        className="w-2 h-2 rounded-full"
        style={{ backgroundColor: model.color }}
      />
      <span className="text-text-muted">{model.name}</span>
    </button>
  );
}

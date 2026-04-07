"use client";

import { motion } from "framer-motion";
import { Zap, CreditCard, Clock } from "lucide-react";
import { ALL_MODELS, type ModelMeta } from "@/config/models";
import { useChatStore } from "@/stores/chatStore";

export default function ModelSelector() {
  const { selectedModelId, setSelectedModel } = useChatStore();

  return (
    <div className="w-full max-w-4xl mx-auto">
      <h2 className="text-xl font-semibold mb-2 text-center">
        Select a Model
      </h2>
      <p className="text-text-muted text-sm text-center mb-6">
        Choose an LLM provider to power your conversations
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {ALL_MODELS.map((model, i) => (
          <ModelCard
            key={model.id}
            model={model}
            selected={selectedModelId === model.id}
            onSelect={() => setSelectedModel(model.id)}
            index={i}
          />
        ))}
      </div>
    </div>
  );
}

function ModelCard({
  model,
  selected,
  onSelect,
  index,
}: {
  model: ModelMeta;
  selected: boolean;
  onSelect: () => void;
  index: number;
}) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.03 }}
      onClick={onSelect}
      className={`relative glass rounded-xl p-4 text-left transition-all duration-200 cursor-pointer group ${
        selected
          ? "border-cta/60 bg-cta/5 shadow-lg shadow-cta/10"
          : "hover:border-panel-secondary/60"
      }`}
    >
      {/* Provider dot + name */}
      <div className="flex items-center gap-2 mb-2">
        <div
          className="w-2.5 h-2.5 rounded-full"
          style={{ backgroundColor: model.color }}
        />
        <span className="text-xs text-text-muted font-medium">
          {model.providerLabel}
        </span>
        <div className="ml-auto">
          {model.tier === "free" ? (
            <span className="flex items-center gap-1 text-xs text-cta bg-cta/10 px-1.5 py-0.5 rounded">
              <Zap className="w-3 h-3" />
              Free
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-warning bg-warning/10 px-1.5 py-0.5 rounded">
              <CreditCard className="w-3 h-3" />
              Paid
            </span>
          )}
        </div>
      </div>

      <h3 className="font-semibold text-sm mb-1">{model.name}</h3>

      <div className="flex items-center gap-1 text-xs text-text-muted">
        <Clock className="w-3 h-3" />
        {model.responseTime}
      </div>

      {/* Selected indicator */}
      {selected && (
        <motion.div
          layoutId="model-selected"
          className="absolute inset-0 rounded-xl border-2 border-cta pointer-events-none"
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
        />
      )}
    </motion.button>
  );
}

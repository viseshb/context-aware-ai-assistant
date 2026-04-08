"use client";

import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, CreditCard, Send, Zap } from "lucide-react";
import type { ModelMeta } from "@/config/models";

const MAX_MESSAGE_LENGTH = 10000;

interface InputBarProps {
  onSend: (message: string) => void;
  models: ModelMeta[];
  modelsLoaded: boolean;
  selectedModelId: string | null;
  onModelChange: (modelId: string) => void;
  disabled?: boolean;
}

export default function InputBar({
  onSend,
  models,
  modelsLoaded,
  selectedModelId,
  onModelChange,
  disabled,
}: InputBarProps) {
  const [input, setInput] = useState("");
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const modelMenuRef = useRef<HTMLDivElement>(null);
  const selectedModel = models.find((model) => model.id === selectedModelId) || null;
  const modelSelectorDisabled = disabled || !modelsLoaded || models.length === 0;

  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
    }
  }, [input]);

  useEffect(() => {
    if (!modelMenuOpen) return;

    const handlePointerDown = (event: MouseEvent) => {
      if (!modelMenuRef.current?.contains(event.target as Node)) {
        setModelMenuOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setModelMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [modelMenuOpen]);

  useEffect(() => {
    if (modelSelectorDisabled) {
      setModelMenuOpen(false);
    }
  }, [modelSelectorDisabled]);

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled || !selectedModelId) return;
    onSend(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-border p-4">
      <div className="mx-auto flex max-w-4xl items-end gap-3">
        <div className="glass flex-1 rounded-xl p-3">
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
              <div ref={modelMenuRef} className="relative sm:w-72">
                <button
                  type="button"
                  onClick={() => {
                    if (modelSelectorDisabled) return;
                    setModelMenuOpen((open) => !open);
                  }}
                  disabled={modelSelectorDisabled}
                  className="flex w-full items-center gap-3 rounded-lg border border-border bg-panel-secondary/30 px-3 py-2 text-left text-sm text-foreground transition-colors focus:outline-none focus:border-cta/50 disabled:opacity-60"
                >
                  {selectedModel ? (
                    <>
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: selectedModel.color }}
                      />
                      <span className="min-w-0 flex-1 truncate">
                        {selectedModel.name} - {selectedModel.providerLabel}
                      </span>
                    </>
                  ) : (
                    <span className="text-text-muted">
                      {!modelsLoaded
                        ? "Loading models..."
                        : models.length === 0
                          ? "No models available"
                          : "Select a model"}
                    </span>
                  )}

                  <ChevronDown
                    className={`ml-auto h-4 w-4 shrink-0 text-text-muted transition-transform ${
                      modelMenuOpen ? "rotate-180" : ""
                    }`}
                  />
                </button>

                {modelMenuOpen && !modelSelectorDisabled && (
                  <div className="absolute bottom-[calc(100%+0.5rem)] left-0 right-0 z-30 overflow-hidden rounded-xl border border-border bg-panel shadow-[0_20px_50px_rgba(2,6,23,0.45)]">
                    <div className="max-h-80 overflow-y-auto p-2">
                      {models.map((model) => {
                        const isSelected = model.id === selectedModelId;

                        return (
                          <button
                            key={model.id}
                            type="button"
                            onClick={() => {
                              onModelChange(model.id);
                              setModelMenuOpen(false);
                            }}
                            className={`flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition-colors ${
                              isSelected
                                ? "bg-cta/10 text-foreground"
                                : "text-foreground hover:bg-panel-secondary/35"
                            }`}
                          >
                            <span
                              className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full"
                              style={{ backgroundColor: model.color }}
                            />

                            <span className="min-w-0 flex-1">
                              <span className="flex items-center gap-2">
                                <span className="truncate text-sm font-medium">{model.name}</span>
                                <span
                                  className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.12em] ${
                                    model.tier === "free"
                                      ? "bg-cta/10 text-cta"
                                      : "bg-warning/10 text-warning"
                                  }`}
                                >
                                  {model.tier === "free" ? (
                                    <Zap className="h-3 w-3" />
                                  ) : (
                                    <CreditCard className="h-3 w-3" />
                                  )}
                                  {model.tier}
                                </span>
                              </span>

                              <span className="mt-1 block text-xs text-text-muted">
                                {model.providerLabel} - {model.responseTime}
                              </span>
                            </span>

                            {isSelected && <Check className="mt-0.5 h-4 w-4 shrink-0 text-cta" />}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              <div className="min-h-4 text-xs text-text-muted">
                {!modelsLoaded ? (
                  <span>Loading the model list from the backend...</span>
                ) : selectedModel ? (
                  <span>
                    {selectedModel.providerLabel} -{" "}
                    {selectedModel.tier === "free" ? "Free tier" : "Paid tier"} -{" "}
                    {selectedModel.responseTime}
                  </span>
                ) : models.length === 0 ? (
                  <span>No chat models are currently available for this session.</span>
                ) : (
                  <span>Choose a model here, then send your message.</span>
                )}
              </div>
            </div>

            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value.slice(0, MAX_MESSAGE_LENGTH))}
              onKeyDown={handleKeyDown}
              placeholder={
                !modelsLoaded
                  ? "Loading available models..."
                  : selectedModel
                    ? `Message ${selectedModel.name}... (Shift+Enter for new line)`
                    : models.length === 0
                      ? "No models available right now."
                      : "Select a model, then type your message... (Shift+Enter for new line)"
              }
              rows={1}
              maxLength={MAX_MESSAGE_LENGTH}
              disabled={disabled || !modelsLoaded || models.length === 0}
              className="w-full resize-none bg-transparent text-sm leading-relaxed text-foreground placeholder:text-text-muted/50 focus:outline-none"
            />

            <div className="flex items-center justify-end text-xs text-text-muted">
              {input.length}/{MAX_MESSAGE_LENGTH}
            </div>
          </div>
        </div>

        <button
          onClick={handleSubmit}
          disabled={disabled || !modelsLoaded || !selectedModelId || !input.trim()}
          className="flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-xl bg-cta transition-colors hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-30"
          aria-label="Send message"
        >
          <Send className="h-4 w-4 text-background" />
        </button>
      </div>
    </div>
  );
}

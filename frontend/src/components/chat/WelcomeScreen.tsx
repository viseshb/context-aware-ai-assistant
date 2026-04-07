"use client";

import { Bot } from "lucide-react";
import ModelSelector from "@/components/model/ModelSelector";

export default function WelcomeScreen() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 py-12">
      <div className="w-16 h-16 rounded-2xl bg-cta/15 flex items-center justify-center mb-6">
        <Bot className="w-8 h-8 text-cta" />
      </div>
      <h1 className="text-2xl font-bold mb-2">Context-Aware AI Assistant</h1>
      <p className="text-text-muted text-sm mb-8 text-center max-w-md">
        Select a model below to start chatting. Ask questions about your GitHub
        repos, Slack conversations, or database.
      </p>
      <ModelSelector />
    </div>
  );
}

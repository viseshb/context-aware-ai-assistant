"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, GitBranch, MessageSquare, Database } from "lucide-react";

const DEMO_LINES = [
  { type: "user" as const, text: "Show me open issues in the backend repo" },
  {
    type: "tool" as const,
    text: "github_get_issues",
    detail: "repo: org/backend • 5 results",
  },
  {
    type: "assistant" as const,
    text: "Found 5 open issues. The highest priority is #142: Fix auth timeout...",
  },
];

export default function HeroSection() {
  const [visibleLines, setVisibleLines] = useState(0);

  useEffect(() => {
    if (visibleLines < DEMO_LINES.length) {
      const timer = setTimeout(
        () => setVisibleLines((v) => v + 1),
        visibleLines === 0 ? 800 : 1200
      );
      return () => clearTimeout(timer);
    }
    // Reset after showing all lines
    const reset = setTimeout(() => setVisibleLines(0), 4000);
    return () => clearTimeout(reset);
  }, [visibleLines]);

  return (
    <section className="relative min-h-screen flex items-center justify-center pt-16 overflow-hidden">
      {/* Gradient background effects */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cta/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 right-1/4 w-80 h-80 bg-blue-500/5 rounded-full blur-3xl" />
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left: Text content */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cta/10 border border-cta/20 text-cta text-xs font-medium mb-6">
              <span className="w-1.5 h-1.5 rounded-full bg-cta animate-pulse" />
              Powered by MCP + 10 LLM Providers
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6">
              Query Your Entire Stack{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cta to-emerald-300">
                with Natural Language
              </span>
            </h1>

            <p className="text-lg text-text-muted leading-relaxed mb-8 max-w-lg">
              Connect GitHub, Slack, and PostgreSQL. Ask questions in plain
              English. Get synthesized answers with full context — powered by
              Model Context Protocol.
            </p>

            {/* Source icons */}
            <div className="flex items-center gap-4 mb-8">
              {[
                { Icon: GitBranch, label: "GitHub", color: "text-gray-400" },
                { Icon: MessageSquare, label: "Slack", color: "text-purple-400" },
                { Icon: Database, label: "PostgreSQL", color: "text-blue-400" },
              ].map(({ Icon, label, color }) => (
                <div key={label} className="flex items-center gap-2">
                  <Icon className={`w-5 h-5 ${color}`} />
                  <span className="text-sm text-text-muted">{label}</span>
                </div>
              ))}
            </div>

            {/* CTA — Solo / Team */}
            <div className="flex flex-col sm:flex-row gap-3">
              <Link
                href="/login"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-cta hover:bg-cta-hover text-background font-semibold rounded-xl transition-all duration-200 hover:shadow-lg hover:shadow-cta/25 cursor-pointer"
              >
                For You
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/signup?mode=team"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 border border-border hover:border-panel-secondary text-foreground font-medium rounded-xl transition-colors cursor-pointer"
              >
                For Your Team
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </motion.div>

          {/* Right: Animated chat preview */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="relative"
          >
            <div className="glass rounded-2xl p-1 shadow-2xl shadow-black/30">
              {/* Terminal header */}
              <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/80" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                  <div className="w-3 h-3 rounded-full bg-green-500/80" />
                </div>
                <span className="text-xs text-text-muted ml-2">
                  ContextAI — Gemini 2.5 Flash
                </span>
              </div>

              {/* Chat messages */}
              <div className="p-4 space-y-3 min-h-[240px]">
                {DEMO_LINES.slice(0, visibleLines).map((line, i) => (
                  <motion.div
                    key={`${line.type}-${i}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    {line.type === "user" && (
                      <div className="flex justify-end">
                        <div className="bg-cta/15 text-foreground px-4 py-2 rounded-xl rounded-br-sm text-sm max-w-[80%]">
                          {line.text}
                        </div>
                      </div>
                    )}
                    {line.type === "tool" && (
                      <div className="flex justify-start">
                        <div className="bg-panel-secondary/50 border border-border px-3 py-1.5 rounded-lg text-xs flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-cta animate-pulse" />
                          <span className="text-cta font-mono">{line.text}</span>
                          <span className="text-text-muted">• {line.detail}</span>
                        </div>
                      </div>
                    )}
                    {line.type === "assistant" && (
                      <div className="flex justify-start">
                        <div className="bg-panel/80 border border-border px-4 py-2 rounded-xl rounded-bl-sm text-sm max-w-[85%] text-text-muted">
                          {line.text}
                        </div>
                      </div>
                    )}
                  </motion.div>
                ))}

                {/* Typing indicator */}
                {visibleLines > 0 && visibleLines < DEMO_LINES.length && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex gap-1 px-4 py-2"
                  >
                    {[0, 1, 2].map((dot) => (
                      <div
                        key={dot}
                        className="w-1.5 h-1.5 rounded-full bg-text-muted animate-bounce"
                        style={{ animationDelay: `${dot * 0.15}s` }}
                      />
                    ))}
                  </motion.div>
                )}
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

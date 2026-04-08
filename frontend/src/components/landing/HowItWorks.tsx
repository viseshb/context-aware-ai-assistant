"use client";

import { motion } from "framer-motion";
import { MessageCircle, Cpu, Zap } from "lucide-react";

const STEPS = [
  {
    step: "01",
    title: "Ask a Question",
    description:
      "Type your question in natural language. No query syntax, no API knowledge needed.",
    icon: MessageCircle,
    example: '"What are the recent incidents in #ops-alerts?"',
  },
  {
    step: "02",
    title: "AI Processes via MCP",
    description:
      "The LLM identifies which tools to call, fetches real data from GitHub, Slack, or your database.",
    icon: Cpu,
    example: "slack_search_messages -> github_get_issues -> db_query",
  },
  {
    step: "03",
    title: "Get a Synthesized Answer",
    description:
      "Receive a context-rich response with source attribution, tool execution details, and inline visualizations.",
    icon: Zap,
    example: "3 incidents linked to deploy #891, 2 open issues tracked",
  },
];

export default function HowItWorks() {
  return (
    <section className="relative px-4 py-24 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false, amount: 0.35 }}
          transition={{ duration: 0.5 }}
          className="mb-16 text-center"
        >
          <h2 className="mb-4 text-3xl font-bold sm:text-4xl">How It Works</h2>
          <p className="text-lg text-text-muted">
            From question to answer in seconds, not hours.
          </p>
        </motion.div>

        <div className="relative grid gap-8 md:grid-cols-3">
          {STEPS.map((step, index) => (
            <motion.div
              key={step.step}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: false, amount: 0.3 }}
              transition={{ duration: 0.5, delay: index * 0.15 }}
              className="relative px-2 text-center"
            >
              {index < STEPS.length - 1 && (
                <div
                  aria-hidden="true"
                  className="pointer-events-none absolute top-8 z-0 hidden h-px w-[calc(100%-2rem)] -translate-y-1/2 bg-gradient-to-r from-cta/40 via-cta/20 to-cta/40 md:block"
                  style={{ left: "calc(50% + 2rem)" }}
                />
              )}

              <div className="relative z-10 inline-flex h-16 w-16 items-center justify-center rounded-2xl border border-cta/20 bg-cta/10">
                <step.icon className="h-7 w-7 text-cta" />
              </div>

              <div className="mt-6 mb-2 text-xs font-semibold tracking-widest text-cta">
                STEP {step.step}
              </div>
              <h3 className="mb-3 text-xl font-semibold">{step.title}</h3>
              <p className="mb-4 text-sm leading-relaxed text-text-muted">
                {step.description}
              </p>

              <div className="glass rounded-lg px-3 py-2 text-xs font-mono text-text-muted">
                {step.example}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

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
    example: "slack_search_messages → github_get_issues → db_query",
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
    <section className="py-24 px-4 sm:px-6 lg:px-8 relative">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            How It Works
          </h2>
          <p className="text-text-muted text-lg">
            From question to answer in seconds, not hours.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8 relative">
          {/* Connecting line (desktop) */}
          <div className="hidden md:block absolute top-16 left-[16.5%] right-[16.5%] h-px bg-gradient-to-r from-cta/40 via-cta/20 to-cta/40" />

          {STEPS.map((step, index) => (
            <motion.div
              key={step.step}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.15 }}
              className="text-center relative"
            >
              {/* Step circle */}
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-cta/10 border border-cta/20 mb-6 relative z-10">
                <step.icon className="w-7 h-7 text-cta" />
              </div>

              <div className="text-xs font-semibold text-cta tracking-widest mb-2">
                STEP {step.step}
              </div>
              <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
              <p className="text-text-muted text-sm leading-relaxed mb-4">
                {step.description}
              </p>

              {/* Example */}
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

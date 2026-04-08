"use client";

import { motion } from "framer-motion";
import {
  GitBranch,
  MessageSquare,
  Database,
  Search,
  FileCode,
  GitPullRequest,
  Hash,
  Clock,
  Table2,
} from "lucide-react";

const FEATURES = [
  {
    title: "GitHub Integration",
    description:
      "Search code, browse issues and PRs, read files across your repositories — all through natural language.",
    icon: GitBranch,
    color: "text-gray-300",
    bgColor: "bg-gray-500/10",
    tools: [
      { icon: Search, label: "Search code" },
      { icon: GitPullRequest, label: "Issues & PRs" },
      { icon: FileCode, label: "Read files" },
    ],
  },
  {
    title: "Slack Integration",
    description:
      "Search conversations, retrieve thread context, and explore channel history to find team knowledge fast.",
    icon: MessageSquare,
    color: "text-purple-400",
    bgColor: "bg-purple-500/10",
    tools: [
      { icon: Search, label: "Search messages" },
      { icon: Hash, label: "Channels" },
      { icon: Clock, label: "Thread context" },
    ],
  },
  {
    title: "PostgreSQL Integration",
    description:
      "Query your database, inspect schemas, and analyze metrics — safely, with read-only enforcement.",
    icon: Database,
    color: "text-blue-400",
    bgColor: "bg-blue-500/10",
    tools: [
      { icon: Table2, label: "Schema explorer" },
      { icon: Search, label: "SQL queries" },
      { icon: FileCode, label: "Explain plans" },
    ],
  },
];

export default function FeaturesGrid() {
  return (
    <section className="py-24 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false, amount: 0.35 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            Three Data Sources.{" "}
            <span className="text-cta">One Conversation.</span>
          </h2>
          <p className="text-text-muted text-lg max-w-2xl mx-auto">
            Connect your tools and query them all through a single AI-powered
            chat interface with full context awareness.
          </p>
        </motion.div>

        {/* Bento grid */}
        <div className="grid md:grid-cols-3 gap-6">
          {FEATURES.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: false, amount: 0.25 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="glass rounded-2xl p-6 hover:border-panel-secondary/50 transition-all duration-300 group cursor-pointer"
            >
              {/* Icon */}
              <div
                className={`w-12 h-12 rounded-xl ${feature.bgColor} flex items-center justify-center mb-4`}
              >
                <feature.icon className={`w-6 h-6 ${feature.color}`} />
              </div>

              <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
              <p className="text-text-muted text-sm leading-relaxed mb-5">
                {feature.description}
              </p>

              {/* Tool pills */}
              <div className="flex flex-wrap gap-2">
                {feature.tools.map((tool) => (
                  <div
                    key={tool.label}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-panel-secondary/30 text-xs text-text-muted"
                  >
                    <tool.icon className="w-3 h-3" />
                    {tool.label}
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

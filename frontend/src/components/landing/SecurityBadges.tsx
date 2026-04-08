"use client";

import { motion } from "framer-motion";
import {
  Shield,
  Lock,
  Eye,
  ScrollText,
  UserCheck,
  Gauge,
  ShieldCheck,
  FileWarning,
} from "lucide-react";

const LAYERS = [
  {
    icon: Lock,
    title: "Authentication",
    desc: "JWT tokens + bcrypt hashing",
  },
  {
    icon: UserCheck,
    title: "RBAC",
    desc: "Role-based access per user",
  },
  {
    icon: Gauge,
    title: "Rate Limiting",
    desc: "Brute force protection",
  },
  {
    icon: ShieldCheck,
    title: "Input Validation",
    desc: "Schema-enforced payloads",
  },
  {
    icon: Shield,
    title: "Allowlists",
    desc: "Per-user resource scoping",
  },
  {
    icon: FileWarning,
    title: "Read-Only",
    desc: "SQL mutation blocking",
  },
  {
    icon: Eye,
    title: "PII Filtering",
    desc: "Auto-redact sensitive data",
  },
  {
    icon: ScrollText,
    title: "Audit Logging",
    desc: "Full activity traceability",
  },
];

export default function SecurityBadges() {
  return (
    <section className="py-24 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false, amount: 0.35 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cta/10 border border-cta/20 text-cta text-xs font-medium mb-4">
            <Shield className="w-3 h-3" />
            Enterprise-Grade Security
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            8 Layers of Defense
          </h2>
          <p className="text-text-muted text-lg max-w-xl mx-auto">
            Every request passes through multiple security checkpoints before
            any data is accessed or returned.
          </p>
        </motion.div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {LAYERS.map((layer, i) => (
            <motion.div
              key={layer.title}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: false, amount: 0.25 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
              className="glass rounded-xl p-4 text-center hover:border-cta/20 transition-colors cursor-pointer group"
            >
              <div className="w-10 h-10 rounded-lg bg-cta/10 flex items-center justify-center mx-auto mb-3 group-hover:bg-cta/20 transition-colors">
                <layer.icon className="w-5 h-5 text-cta" />
              </div>
              <h4 className="text-sm font-semibold mb-1">{layer.title}</h4>
              <p className="text-xs text-text-muted">{layer.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

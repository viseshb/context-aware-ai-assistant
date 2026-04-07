"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";

export default function CTAFooter() {
  return (
    <section className="py-24 px-4 sm:px-6 lg:px-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="max-w-3xl mx-auto text-center"
      >
        <div className="glass rounded-3xl p-10 sm:p-14 relative overflow-hidden">
          {/* Background glow */}
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-32 bg-cta/10 rounded-full blur-3xl" />
          </div>

          <div className="relative">
            <Sparkles className="w-8 h-8 text-cta mx-auto mb-4" />
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Start Querying Your Data
            </h2>
            <p className="text-text-muted text-lg mb-8 max-w-md mx-auto">
              Connect your GitHub, Slack, and database. Get answers in seconds
              instead of searching for hours.
            </p>
            <Link
              href="/signup"
              className="inline-flex items-center gap-2 px-8 py-3.5 bg-cta hover:bg-cta-hover text-background font-semibold rounded-xl transition-all duration-200 hover:shadow-lg hover:shadow-cta/25 text-lg cursor-pointer"
            >
              Sign Up Free
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </motion.div>
    </section>
  );
}

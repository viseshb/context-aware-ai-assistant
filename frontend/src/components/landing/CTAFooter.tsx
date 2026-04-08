"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles, User, Users } from "lucide-react";

export default function CTAFooter() {
  return (
    <section className="py-24 px-4 sm:px-6 lg:px-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: false, amount: 0.35 }}
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
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Link
                href="/login"
                className="inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-cta hover:bg-cta-hover text-background font-semibold rounded-xl transition-all duration-200 hover:shadow-lg hover:shadow-cta/25 text-lg cursor-pointer"
              >
                <User className="w-5 h-5" />
                For You
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/signup?mode=team"
                className="inline-flex items-center justify-center gap-2 px-8 py-3.5 border border-border hover:border-panel-secondary text-foreground font-semibold rounded-xl transition-all duration-200 text-lg cursor-pointer"
              >
                <Users className="w-5 h-5" />
                For Your Team
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}

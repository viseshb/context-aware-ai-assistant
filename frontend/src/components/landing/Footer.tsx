"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Bot } from "lucide-react";
import ContactModal from "./ContactModal";

export default function Footer() {
  const [contactOpen, setContactOpen] = useState(false);

  return (
    <>
      <motion.footer
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: false, amount: 0.6 }}
        transition={{ duration: 0.35 }}
        className="border-t border-border py-8 px-4 sm:px-6 lg:px-8"
      >
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-text-muted text-sm">
            <Bot className="w-4 h-4 text-cta" />
            <a
              href="https://viseshb.github.io/My-Portfolio/"
              target="_blank"
              rel="noreferrer"
              className="hover:text-cta transition-colors"
            >
              Created by Visesh Bentula
            </a>
          </div>

          <button
            onClick={() => setContactOpen(true)}
            className="text-sm text-text-muted hover:text-cta transition-colors cursor-pointer"
          >
            Contact Us
          </button>
        </div>
      </motion.footer>

      <ContactModal open={contactOpen} onClose={() => setContactOpen(false)} />
    </>
  );
}

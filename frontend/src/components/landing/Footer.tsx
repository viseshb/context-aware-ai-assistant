"use client";

import { useState } from "react";
import { Bot } from "lucide-react";
import ContactModal from "./ContactModal";

export default function Footer() {
  const [contactOpen, setContactOpen] = useState(false);

  return (
    <>
      <footer className="border-t border-border py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-text-muted text-sm">
            <Bot className="w-4 h-4 text-cta" />
            <span>Created by Visesh Bentula</span>
          </div>

          <button
            onClick={() => setContactOpen(true)}
            className="text-sm text-text-muted hover:text-cta transition-colors cursor-pointer"
          >
            Contact Us
          </button>
        </div>
      </footer>

      <ContactModal open={contactOpen} onClose={() => setContactOpen(false)} />
    </>
  );
}

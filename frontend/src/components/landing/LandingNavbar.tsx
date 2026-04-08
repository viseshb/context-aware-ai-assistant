"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Bot, Menu, X } from "lucide-react";

export default function LandingNavbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-panel/80 backdrop-blur-xl shadow-lg shadow-black/20"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-cta/20 flex items-center justify-center group-hover:bg-cta/30 transition-colors">
              <Bot className="w-5 h-5 text-cta" />
            </div>
            <span className="text-lg font-semibold hidden sm:block">
              ContextAI
            </span>
          </Link>

          {/* Desktop actions */}
          <div className="hidden sm:flex items-center gap-3">
            <Link
              href="/login"
              className="px-4 py-2 text-sm font-medium text-text-muted hover:text-foreground transition-colors cursor-pointer"
            >
              For You
            </Link>
            <Link
              href="/signup?mode=team"
              className="px-5 py-2 text-sm font-semibold bg-cta hover:bg-cta-hover text-background rounded-lg transition-colors cursor-pointer"
            >
              For Your Team
            </Link>
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="sm:hidden p-2 text-text-muted hover:text-foreground cursor-pointer"
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="sm:hidden glass border-t border-border">
          <div className="px-4 py-4 space-y-3">
            <Link
              href="/login"
              className="block px-4 py-2 text-sm font-medium text-text-muted hover:text-foreground"
              onClick={() => setMobileOpen(false)}
            >
              For You
            </Link>
            <Link
              href="/signup?mode=team"
              className="block px-4 py-2 text-sm font-semibold bg-cta hover:bg-cta-hover text-background rounded-lg text-center"
              onClick={() => setMobileOpen(false)}
            >
              For Your Team
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}

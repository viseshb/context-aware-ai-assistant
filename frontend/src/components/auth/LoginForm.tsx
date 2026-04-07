"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Bot, LogIn, Loader2, AlertCircle, Eye, EyeOff } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";

export default function LoginForm() {
  const router = useRouter();
  const { login, isLoading } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    try {
      await login(email, password);
      router.push("/chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-background">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="glass rounded-2xl p-8 w-full max-w-md"
      >
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 mb-4">
            <div className="w-10 h-10 rounded-xl bg-cta/20 flex items-center justify-center">
              <Bot className="w-6 h-6 text-cta" />
            </div>
          </Link>
          <h1 className="text-2xl font-bold">Welcome back</h1>
          <p className="text-text-muted text-sm mt-1">Log in to your account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="login-email" className="block text-sm font-medium text-text-muted mb-1">
              Email
            </label>
            <input
              id="login-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2.5 bg-panel-secondary/30 border border-border rounded-lg text-foreground placeholder:text-text-muted/50 focus:outline-none focus:border-cta/50 transition-colors"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label htmlFor="login-password" className="block text-sm font-medium text-text-muted mb-1">
              Password
            </label>
            <div className="relative">
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2.5 pr-10 bg-panel-secondary/30 border border-border rounded-lg text-foreground placeholder:text-text-muted/50 focus:outline-none focus:border-cta/50 transition-colors"
                placeholder="Enter your password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-foreground transition-colors cursor-pointer"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-error text-sm">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-cta hover:bg-cta-hover disabled:opacity-50 text-background font-semibold rounded-lg transition-colors cursor-pointer"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <LogIn className="w-4 h-4" />}
            {isLoading ? "Logging in..." : "Log in"}
          </button>
        </form>

        <p className="text-center text-sm text-text-muted mt-6">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="text-cta hover:underline">Sign up</Link>
        </p>
      </motion.div>
    </div>
  );
}

"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Bot, UserPlus, Loader2, AlertCircle, Eye, EyeOff, KeyRound } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";

export default function SignupForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const mode = searchParams.get("mode") || "team";
  const { signup, isLoading } = useAuthStore();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [teamCode, setTeamCode] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  // Solo mode — no signup, redirect to login
  if (mode === "solo") {
    router.push("/login");
    return null;
  }

  const handleSubmit = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    try {
      const result = await signup(username, email, password, teamCode);
      if (result === "pending") {
        router.push("/pending");
      } else {
        router.push("/chat");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
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
          <h1 className="text-2xl font-bold">Join your team</h1>
          <p className="text-text-muted text-sm mt-1">
            Enter the team code from your admin to get started
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Team Code */}
          <div>
            <label htmlFor="signup-teamcode" className="block text-sm font-medium text-text-muted mb-1">
              Team Code
            </label>
            <div className="relative">
              <input
                id="signup-teamcode"
                type="text"
                required
                value={teamCode}
                onChange={(e) => setTeamCode(e.target.value)}
                className="w-full px-3 py-2.5 pl-10 bg-panel-secondary/30 border border-border rounded-lg text-foreground placeholder:text-text-muted/50 focus:outline-none focus:border-cta/50 transition-colors font-mono tracking-wider"
                placeholder="ACME-2026"
              />
              <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            </div>
          </div>

          <div>
            <label htmlFor="signup-username" className="block text-sm font-medium text-text-muted mb-1">
              Username
            </label>
            <input
              id="signup-username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2.5 bg-panel-secondary/30 border border-border rounded-lg text-foreground placeholder:text-text-muted/50 focus:outline-none focus:border-cta/50 transition-colors"
              placeholder="Your username"
            />
          </div>

          <div>
            <label htmlFor="signup-email" className="block text-sm font-medium text-text-muted mb-1">
              Email
            </label>
            <input
              id="signup-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2.5 bg-panel-secondary/30 border border-border rounded-lg text-foreground placeholder:text-text-muted/50 focus:outline-none focus:border-cta/50 transition-colors"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label htmlFor="signup-password" className="block text-sm font-medium text-text-muted mb-1">
              Password
            </label>
            <div className="relative">
              <input
                id="signup-password"
                type={showPassword ? "text" : "password"}
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2.5 pr-10 bg-panel-secondary/30 border border-border rounded-lg text-foreground placeholder:text-text-muted/50 focus:outline-none focus:border-cta/50 transition-colors"
                placeholder="Min 8 chars, 1 uppercase, 1 number"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-foreground transition-colors cursor-pointer"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div>
            <label htmlFor="signup-confirm" className="block text-sm font-medium text-text-muted mb-1">
              Confirm Password
            </label>
            <input
              id="signup-confirm"
              type="password"
              required
              minLength={8}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={`w-full px-3 py-2.5 bg-panel-secondary/30 border rounded-lg text-foreground placeholder:text-text-muted/50 focus:outline-none transition-colors ${
                confirmPassword && confirmPassword !== password
                  ? "border-error/50 focus:border-error"
                  : "border-border focus:border-cta/50"
              }`}
              placeholder="Re-enter your password"
            />
            {confirmPassword && confirmPassword !== password && (
              <p className="text-error text-xs mt-1">Passwords do not match</p>
            )}
          </div>

          {error && (
            <div className="flex items-center gap-2 text-error text-sm">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || (!!confirmPassword && confirmPassword !== password)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-cta hover:bg-cta-hover disabled:opacity-50 text-background font-semibold rounded-lg transition-colors cursor-pointer"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
            {isLoading ? "Sending request..." : "Request to Join"}
          </button>
        </form>

        <div className="text-center text-sm text-text-muted mt-6 space-y-2">
          <p>
            Already have an account?{" "}
            <Link href="/login" className="text-cta hover:underline">Log in</Link>
          </p>
          <p>
            <Link href="/" className="text-text-muted hover:text-foreground transition-colors">&larr; Back to home</Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}

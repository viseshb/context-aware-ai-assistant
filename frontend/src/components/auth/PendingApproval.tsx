"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Clock, CheckCircle, XCircle } from "lucide-react";
import confetti from "canvas-confetti";
import { useAuthStore } from "@/stores/authStore";

type ApprovalStatus = "pending" | "active" | "rejected" | "timeout" | "error";

export default function PendingApproval() {
  const router = useRouter();
  const { pendingToken, logout } = useAuthStore();
  const [status, setStatus] = useState<ApprovalStatus>("pending");
  const [role, setRole] = useState("");
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!pendingToken) {
      router.push("/login");
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    // Poll every 5 seconds (SSE doesn't support auth headers natively)
    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`${apiUrl}/api/auth/approval-status`, {
          headers: { Authorization: `Bearer ${pendingToken}` },
        });
        const text = await res.text();
        // Parse SSE data lines
        const lines = text.split("\n").filter((l) => l.startsWith("data: "));
        for (const line of lines) {
          const data = JSON.parse(line.replace("data: ", ""));
          if (data.status === "active") {
            setStatus("active");
            setRole(data.role || "member");
            clearInterval(pollInterval);
            return;
          }
          if (data.status === "rejected") {
            setStatus("rejected");
            clearInterval(pollInterval);
            return;
          }
        }
      } catch {
        // Keep polling
      }
    }, 5000);

    return () => {
      clearInterval(pollInterval);
      eventSourceRef.current?.close();
    };
  }, [pendingToken, router]);

  // Confetti on approval
  useEffect(() => {
    if (status !== "active") return;

    // Fire confetti
    const duration = 3000;
    const end = Date.now() + duration;

    const frame = () => {
      confetti({
        particleCount: 3,
        angle: 60,
        spread: 55,
        origin: { x: 0, y: 0.7 },
        colors: ["#22C55E", "#16A34A", "#4ADE80"],
      });
      confetti({
        particleCount: 3,
        angle: 120,
        spread: 55,
        origin: { x: 1, y: 0.7 },
        colors: ["#22C55E", "#16A34A", "#4ADE80"],
      });

      if (Date.now() < end) requestAnimationFrame(frame);
    };
    frame();

    // Redirect after 3 seconds
    const timer = setTimeout(() => {
      localStorage.removeItem("pendingToken");
      router.push("/login");
    }, 3500);

    return () => clearTimeout(timer);
  }, [status, router]);

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-background">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-2xl p-10 max-w-md text-center"
      >
        {status === "pending" && (
          <>
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              className="w-20 h-20 rounded-2xl bg-cta/15 flex items-center justify-center mx-auto mb-6"
            >
              <Clock className="w-10 h-10 text-cta" />
            </motion.div>
            <h1 className="text-2xl font-bold mb-3">Waiting for Approval</h1>
            <p className="text-text-muted mb-2">
              Your signup request has been sent to the admin.
            </p>
            <p className="text-text-muted text-sm">
              You&apos;ll be redirected automatically once approved.
            </p>
            <div className="flex justify-center gap-1.5 mt-6">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-2 h-2 rounded-full bg-cta"
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.3 }}
                />
              ))}
            </div>
            <button
              onClick={() => { logout(); router.push("/"); }}
              className="mt-6 text-sm text-text-muted hover:text-foreground transition-colors cursor-pointer"
            >
              &larr; Back to home
            </button>
          </>
        )}

        {status === "active" && (
          <>
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 200 }}
              className="w-20 h-20 rounded-2xl bg-cta/20 flex items-center justify-center mx-auto mb-6"
            >
              <CheckCircle className="w-10 h-10 text-cta" />
            </motion.div>
            <h1 className="text-2xl font-bold mb-2 text-cta">You&apos;re Approved!</h1>
            <p className="text-text-muted mb-1">
              Role: <span className="text-foreground font-semibold">{role}</span>
            </p>
            <p className="text-text-muted text-sm">Redirecting to login...</p>
          </>
        )}

        {status === "rejected" && (
          <>
            <div className="w-20 h-20 rounded-2xl bg-error/15 flex items-center justify-center mx-auto mb-6">
              <XCircle className="w-10 h-10 text-error" />
            </div>
            <h1 className="text-2xl font-bold mb-2 text-error">Request Denied</h1>
            <p className="text-text-muted mb-4">
              Your signup request was not approved. Contact the admin for more information.
            </p>
            <button
              onClick={() => { logout(); router.push("/"); }}
              className="px-4 py-2 bg-panel-secondary hover:bg-panel-secondary/80 rounded-lg text-sm transition-colors cursor-pointer"
            >
              Back to Home
            </button>
          </>
        )}
      </motion.div>
    </div>
  );
}

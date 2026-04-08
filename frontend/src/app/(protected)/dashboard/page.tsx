"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Activity, Bot, Coins, Gauge, TimerReset, Wrench } from "lucide-react";
import { ALL_MODELS } from "@/config/models";
import { useAuthStore } from "@/stores/authStore";
import { api } from "@/services/api";

function formatMs(value: number | null | undefined): string {
  if (value == null) return "--";
  if (value < 1000) return `${value} ms`;
  return `${(value / 1000).toFixed(2)} s`;
}

function formatNumber(value: number | null | undefined): string {
  if (value == null) return "--";
  return new Intl.NumberFormat().format(value);
}

function formatMoney(value: number | null | undefined): string {
  if (value == null) return "--";
  return `$${value.toFixed(4)}`;
}

interface DashboardMetricRow {
  id: string;
  conversation_id: string;
  model_id: string;
  provider_model: string;
  ttft_ms: number | null;
  total_time_ms: number;
  tool_time_ms: number;
  tool_call_count: number;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  response_chars: number;
  tool_calls: { name: string; status: string; duration_ms: number }[];
  context_sources: { type: string; detail: string }[];
  created_at: string;
}

interface DashboardSummary {
  total_turns: number;
  avg_ttft_ms: number | null;
  total_tool_calls: number;
  total_time_ms: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  last_turn_at: string | null;
}

interface DashboardResponse {
  rows: DashboardMetricRow[];
  summary: DashboardSummary;
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, token, loadFromStorage } = useAuthStore();
  const [rows, setRows] = useState<DashboardMetricRow[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(true);

  useEffect(() => {
    if (!token) {
      loadFromStorage().then(() => {
        const state = useAuthStore.getState();
        if (!state.token) {
          router.push("/login");
        }
      });
    }
  }, [token, loadFromStorage, router]);

  useEffect(() => {
    if (!token) return;

    setIsLoadingMetrics(true);
    api<DashboardResponse>("/api/chat/metrics?limit=200", { token })
      .then((payload) => {
        setRows(payload.rows || []);
        setSummary(payload.summary || null);
      })
      .catch(() => {
        setRows([]);
        setSummary(null);
      })
      .finally(() => setIsLoadingMetrics(false));
  }, [token]);

  const assistantRows = useMemo(
    () =>
      rows.map((row) => ({
        ...row,
        modelLabel: ALL_MODELS.find((model) => model.id === row.model_id)?.name || row.model_id || "Unknown model",
      })),
    [rows],
  );

  const resolvedSummary = useMemo(
    () =>
      summary || {
        total_turns: assistantRows.length,
        avg_ttft_ms: assistantRows.length
          ? Math.round(assistantRows.reduce((sum, row) => sum + (row.ttft_ms || 0), 0) / assistantRows.length)
          : null,
        total_tool_calls: assistantRows.reduce((sum, row) => sum + (row.tool_call_count || 0), 0),
        total_time_ms: assistantRows.reduce((sum, row) => sum + (row.total_time_ms || 0), 0),
        total_input_tokens: assistantRows.reduce((sum, row) => sum + (row.input_tokens || 0), 0),
        total_output_tokens: assistantRows.reduce((sum, row) => sum + (row.output_tokens || 0), 0),
        total_cost_usd: assistantRows.reduce((sum, row) => sum + (row.cost_usd || 0), 0),
        last_turn_at: assistantRows[0]?.created_at || null,
      },
    [assistantRows, summary],
  );

  if (!user) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="flex items-center gap-2 text-text-muted">
          <Bot className="h-5 w-5" />
          Loading dashboard...
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-background">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="flex flex-col gap-2">
          <div className="text-[11px] uppercase tracking-[0.26em] text-text-muted">Saved telemetry</div>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-foreground">Chat performance overview</h1>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-text-muted">
                Persisted turn metrics from SQLite for your signed-in account. Token and cost fields only appear when the selected provider exposes them.
              </p>
            </div>
            <div className="rounded-2xl border border-border bg-panel-secondary/20 px-4 py-3 text-sm text-text-muted">
              Logged in as <span className="font-medium text-foreground">{user.username}</span>
              {resolvedSummary.last_turn_at ? (
                <div className="mt-1 text-xs text-text-muted">
                  Last saved turn {new Date(resolvedSummary.last_turn_at).toLocaleString()}
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[
            { label: "Tracked turns", value: formatNumber(resolvedSummary.total_turns), icon: Activity },
            { label: "Average TTFT", value: formatMs(resolvedSummary.avg_ttft_ms), icon: Gauge },
            { label: "Tool calls", value: formatNumber(resolvedSummary.total_tool_calls), icon: Wrench },
            { label: "Observed cost", value: formatMoney(resolvedSummary.total_cost_usd ?? null), icon: Coins },
          ].map((card) => {
            const Icon = card.icon;
            return (
              <div key={card.label} className="glass rounded-3xl p-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase tracking-[0.18em] text-text-muted">{card.label}</span>
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-cta/10">
                    <Icon className="h-4 w-4 text-cta" />
                  </div>
                </div>
                <div className="mt-4 text-3xl font-semibold text-foreground">{card.value}</div>
              </div>
            );
          })}
        </div>

        <div className="mt-8 glass overflow-hidden rounded-3xl">
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <div>
              <div className="text-lg font-semibold text-foreground">Turn telemetry</div>
              <div className="text-sm text-text-muted">Per-response metrics saved to the backend database.</div>
            </div>
            <div className="rounded-full border border-cta/20 bg-cta/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-cta">
              Persisted
            </div>
          </div>

          {isLoadingMetrics ? (
            <div className="px-6 py-16 text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-3xl bg-cta/10">
                <Bot className="h-6 w-6 animate-pulse text-cta" />
              </div>
              <h2 className="mt-5 text-xl font-semibold text-foreground">Loading saved telemetry</h2>
              <p className="mt-2 text-sm text-text-muted">
                Pulling historical chat metrics from the database.
              </p>
            </div>
          ) : assistantRows.length === 0 ? (
            <div className="px-6 py-16 text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-3xl bg-cta/10">
                <TimerReset className="h-6 w-6 text-cta" />
              </div>
              <h2 className="mt-5 text-xl font-semibold text-foreground">No telemetry yet</h2>
              <p className="mt-2 text-sm text-text-muted">
                Send a few chat turns and this dashboard will fill with timing, tool, token, and cost details.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-background/20 text-left text-[11px] uppercase tracking-[0.16em] text-text-muted">
                    <th className="px-5 py-3">Time</th>
                    <th className="px-5 py-3">Model</th>
                    <th className="px-5 py-3">Input</th>
                    <th className="px-5 py-3">Output</th>
                    <th className="px-5 py-3">TTFT</th>
                    <th className="px-5 py-3">Total</th>
                    <th className="px-5 py-3">Tools</th>
                    <th className="px-5 py-3">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {assistantRows.map((row) => (
                    <tr key={row.id} className="border-b border-border/60 align-top hover:bg-panel-secondary/10">
                      <td className="px-5 py-4 text-xs text-text-muted">{new Date(row.created_at).toLocaleString()}</td>
                      <td className="px-5 py-4">
                        <div className="font-medium text-foreground">{row.modelLabel}</div>
                        <div className="mt-1 text-xs text-text-muted">{row.provider_model || row.model_id || "--"}</div>
                      </td>
                      <td className="px-5 py-4 text-foreground">{formatNumber(row.input_tokens)}</td>
                      <td className="px-5 py-4 text-foreground">{formatNumber(row.output_tokens)}</td>
                      <td className="px-5 py-4 text-foreground">{formatMs(row.ttft_ms)}</td>
                      <td className="px-5 py-4">
                        <div className="text-foreground">{formatMs(row.total_time_ms)}</div>
                        <div className="mt-1 text-xs text-text-muted">
                          Tool time {formatMs(row.tool_time_ms)}
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <div className="text-foreground">{formatNumber(row.tool_call_count)}</div>
                        <div className="mt-1 text-xs text-text-muted">
                          {row.tool_calls.length > 0
                            ? row.tool_calls.map((tool) => tool.name).slice(0, 2).join(", ")
                            : "No tools used"}
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <div className="font-medium text-foreground">{formatMoney(row.cost_usd)}</div>
                        <div className="mt-1 text-xs text-text-muted">{formatNumber(row.response_chars)} chars</div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

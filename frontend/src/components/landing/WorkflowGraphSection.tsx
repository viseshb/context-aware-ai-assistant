"use client";

import { useRef } from "react";
import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
  type MotionValue,
} from "framer-motion";
import {
  Bot,
  Cpu,
  Database,
  GitBranch,
  MessageSquare,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";

const FLOW_STEPS = [
  {
    icon: MessageSquare,
    title: "User Prompt",
    description:
      "A natural-language question enters the system exactly as typed by the user.",
    detail: '"What changed after deploy #891 and who discussed it?"',
  },
  {
    icon: ScrollText,
    title: "Context + Policy Layer",
    description:
      "The backend injects time, role, follow-up history, tool rules, and app context before inference.",
    detail: "time + role + history + tool schema + safety rules",
  },
  {
    icon: Cpu,
    title: "Model Decision",
    description:
      "The selected model decides whether to answer directly or call MCP tools for live data.",
    detail: "plan -> infer params -> call the fewest tools needed",
  },
  {
    icon: ShieldCheck,
    title: "Security Gate",
    description:
      "RBAC, allowlists, read-only checks, and redaction run before results are exposed.",
    detail: "RBAC | allowlists | read-only SQL | secret redaction",
  },
  {
    icon: Sparkles,
    title: "Synthesized Answer",
    description:
      "Tool results are merged into one response with context, guardrails, and source-aware output.",
    detail: "Deploy #891 touched auth timeout. Sources: GitHub, Slack.",
  },
];

const TOOL_SOURCES = [
  {
    icon: GitBranch,
    title: "GitHub",
    description: "Repos, files, issues, PRs, commits",
    tone: "text-gray-300",
    bg: "bg-gray-500/10",
  },
  {
    icon: MessageSquare,
    title: "Slack",
    description: "Channels, messages, and threads",
    tone: "text-purple-400",
    bg: "bg-purple-500/10",
  },
  {
    icon: Database,
    title: "PostgreSQL",
    description: "Schema inspection and read-only SQL",
    tone: "text-blue-400",
    bg: "bg-blue-500/10",
  },
];

const FLOW_TIMELINE = {
  user: 0.05,
  connector1Start: 0.1,
  connector1End: 0.18,
  context: 0.18,
  connector2Start: 0.24,
  connector2End: 0.32,
  model: 0.32,
  connector3Start: 0.38,
  connector3End: 0.46,
  hub: 0.46,
  sources: 0.5,
  branchStart: 0.56,
  branchEnd: 0.7,
  connector4Start: 0.72,
  connector4End: 0.8,
  security: 0.78,
  connector5Start: 0.86,
  connector5End: 0.94,
  answer: 0.92,
} as const;

function VerticalConnector({
  height,
  progress,
  start,
  end,
  showMarker,
}: {
  height: number;
  progress: MotionValue<number>;
  start: number;
  end: number;
  showMarker: boolean;
}) {
  const revealStart = Math.max(0, start - 0.08);
  const lineOpacity = useTransform(progress, [revealStart, start, 1], [0, 0.95, 0.95]);
  const markerY = useTransform(progress, [start, end], [0, Math.max(height - 14, 0)]);
  const markerOpacity = useTransform(
    progress,
    [Math.max(0, start - 0.015), start, end, Math.min(1, end + 0.015)],
    [0, 1, 1, 0]
  );

  return (
    <div className="relative mx-auto" style={{ height, width: 24 }}>
      <motion.div
        className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-gradient-to-b from-cta/10 via-cta/55 to-cta/10"
        style={{ opacity: lineOpacity }}
      />
      {showMarker && (
        <motion.div
          className="absolute left-1/2 top-0 z-20 h-4 w-4 -translate-x-1/2 rounded-full border border-white/20 bg-cta shadow-[0_0_0_5px_rgba(34,197,94,0.16),0_0_24px_rgba(34,197,94,0.9)]"
          style={{ y: markerY, opacity: markerOpacity }}
        />
      )}
    </div>
  );
}

function FlowNode({
  icon: Icon,
  title,
  description,
  detail,
  accent = false,
  progress,
  revealStart,
}: {
  icon: typeof MessageSquare;
  title: string;
  description: string;
  detail: string;
  accent?: boolean;
  progress: MotionValue<number>;
  revealStart: number;
}) {
  const revealFrom = Math.max(0, revealStart - 0.08);
  const opacity = useTransform(progress, [revealFrom, revealStart, 1], [0, 1, 1]);
  const y = useTransform(progress, [revealFrom, revealStart, 1], [28, 0, 0]);

  return (
    <motion.div
      style={{ opacity, y }}
      className="relative mx-auto w-full max-w-3xl rounded-2xl border border-border bg-panel/35 p-5 sm:p-6 shadow-[0_22px_60px_rgba(2,6,23,0.28)] backdrop-blur-xl"
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-start">
        <div
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border ${
            accent ? "border-cta/30 bg-cta/12" : "border-border bg-panel-secondary/25"
          }`}
        >
          <Icon className={`h-5 w-5 ${accent ? "text-cta" : "text-foreground"}`} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-semibold sm:text-xl">{title}</h3>
            {accent && (
              <span className="rounded-full border border-cta/20 bg-cta/10 px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.18em] text-cta">
                Live Flow
              </span>
            )}
          </div>
          <p className="text-sm leading-relaxed text-text-muted sm:text-[15px]">{description}</p>
          <div className="mt-4 rounded-xl border border-border bg-panel-secondary/25 px-3 py-2.5 font-mono text-xs text-text-muted">
            {detail}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function ToolSourceCard({
  source,
  index,
  progress,
  revealStart,
}: {
  source: (typeof TOOL_SOURCES)[number];
  index: number;
  progress: MotionValue<number>;
  revealStart: number;
}) {
  const stepReveal = revealStart + index * 0.03;
  const revealFrom = Math.max(0, stepReveal - 0.08);
  const opacity = useTransform(progress, [revealFrom, stepReveal, 1], [0, 1, 1]);
  const y = useTransform(progress, [revealFrom, stepReveal, 1], [24, 0, 0]);

  return (
    <motion.div
      style={{ opacity, y }}
      className="rounded-2xl border border-border bg-panel-secondary/20 p-4"
    >
      <div className="mb-3 flex items-center gap-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${source.bg}`}>
          <source.icon className={`h-5 w-5 ${source.tone}`} />
        </div>
        <div>
          <div className="font-semibold">{source.title}</div>
          <div className="text-xs text-text-muted">Connected MCP source</div>
        </div>
      </div>
      <p className="text-sm text-text-muted">{source.description}</p>
    </motion.div>
  );
}

function BranchConnector({
  progress,
  start,
  end,
  showMarker,
}: {
  progress: MotionValue<number>;
  start: number;
  end: number;
  showMarker: boolean;
}) {
  const revealStart = Math.max(0, start - 0.08);
  const lineOpacity = useTransform(progress, [revealStart, start, 1], [0, 0.95, 0.95]);
  const span = end - start;
  const splitStart = start + span * 0.18;
  const spreadEnd = start + span * 0.4;
  const holdEnd = start + span * 0.68;
  const fadeEnd = start + span * 0.84;
  const entryOpacity = useTransform(
    progress,
    [Math.max(0, start - 0.015), start, splitStart, Math.min(1, splitStart + 0.02)],
    [0, 1, 1, 0]
  );
  const entryTop = useTransform(progress, [start, splitStart], ["0rem", "2rem"]);
  const branchOpacity = useTransform(
    progress,
    [Math.max(0, splitStart - 0.01), splitStart, holdEnd, fadeEnd, end],
    [0, 1, 1, 0.35, 0]
  );
  const branchScale = useTransform(
    progress,
    [splitStart, spreadEnd, end],
    [0.92, 1, 1]
  );
  const leftMarker = useTransform(
    progress,
    [splitStart, spreadEnd, end],
    ["50%", "16.666%", "16.666%"]
  );
  const centerMarker = useTransform(
    progress,
    [splitStart, spreadEnd, end],
    ["50%", "50%", "50%"]
  );
  const rightMarker = useTransform(
    progress,
    [splitStart, spreadEnd, end],
    ["50%", "83.333%", "83.333%"]
  );
  const branchTop = useTransform(
    progress,
    [splitStart, spreadEnd, end],
    ["2rem", "2rem", "2rem"]
  );

  return (
    <div className="mt-8 hidden md:block">
      <div className="relative h-16">
        <motion.div
          className="absolute left-1/2 top-0 h-8 w-px -translate-x-1/2 bg-gradient-to-b from-cta/40 to-cta/15"
          style={{ opacity: lineOpacity }}
        />
        <motion.div
          className="absolute left-[16.666%] right-[16.666%] top-8 h-px bg-gradient-to-r from-cta/25 via-cta/45 to-cta/25"
          style={{ opacity: lineOpacity }}
        />
        {[16.666, 50, 83.333].map((left) => (
          <motion.div
            key={left}
            className="absolute top-8 h-8 w-px bg-gradient-to-b from-cta/45 to-cta/10"
            style={{ left: `${left}%`, opacity: lineOpacity }}
          />
        ))}
        {showMarker && (
          <>
            <motion.div
              className="absolute z-20 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/20 bg-cta shadow-[0_0_0_5px_rgba(34,197,94,0.16),0_0_24px_rgba(34,197,94,0.9)]"
              style={{ left: "50%", top: entryTop, opacity: entryOpacity }}
            />
            {[leftMarker, centerMarker, rightMarker].map((markerLeft, index) => (
              <motion.div
                key={index}
                className="absolute z-20 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/20 bg-cta shadow-[0_0_0_5px_rgba(34,197,94,0.16),0_0_24px_rgba(34,197,94,0.9)]"
                style={{
                  left: markerLeft,
                  top: branchTop,
                  opacity: branchOpacity,
                  scale: branchScale,
                }}
              />
            ))}
          </>
        )}
      </div>
    </div>
  );
}

export default function WorkflowGraphSection() {
  const reduceMotion = useReducedMotion();
  const flowRef = useRef<HTMLDivElement | null>(null);
  const { scrollYProgress } = useScroll({
    target: flowRef,
    offset: ["start 84%", "end 18%"],
  });
  const hubRevealStart = FLOW_TIMELINE.hub;
  const hubRevealFrom = hubRevealStart - 0.08;
  const hubOpacity = useTransform(scrollYProgress, [hubRevealFrom, hubRevealStart, 1], [0, 1, 1]);
  const hubY = useTransform(scrollYProgress, [hubRevealFrom, hubRevealStart, 1], [28, 0, 0]);

  return (
    <section className="relative px-4 py-24 sm:px-6 lg:px-8">
      <div className="relative mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false, amount: 0.35 }}
          transition={{ duration: 0.5 }}
          className="mb-14 text-center"
        >
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cta/20 bg-cta/10 px-3 py-1 text-xs font-medium text-cta">
            <Workflow className="h-3.5 w-3.5" />
            End-to-End Execution Graph
          </div>
          <h2 className="mb-4 text-3xl font-bold sm:text-4xl">
            Watch A Question Move Through The Stack
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-text-muted">
            From raw user text to a grounded answer, every hop is visible: prompt
            assembly, model routing, MCP tool execution, security checks, and
            final synthesis.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false, amount: 0.2 }}
          transition={{ duration: 0.55 }}
          className="glass relative overflow-hidden rounded-[2rem] p-6 sm:p-8 lg:p-10"
        >
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute left-8 top-10 h-40 w-40 rounded-full bg-cta/6 blur-3xl" />
            <div className="absolute right-10 top-1/3 h-48 w-48 rounded-full bg-blue-500/6 blur-3xl" />
            <div className="absolute bottom-8 left-1/2 h-44 w-44 -translate-x-1/2 rounded-full bg-emerald-400/6 blur-3xl" />
          </div>

          <div ref={flowRef} className="relative mx-auto max-w-4xl">
            <FlowNode
              {...FLOW_STEPS[0]}
              accent
              progress={scrollYProgress}
              revealStart={FLOW_TIMELINE.user}
            />
            <VerticalConnector
              height={72}
              progress={scrollYProgress}
              start={FLOW_TIMELINE.connector1Start}
              end={FLOW_TIMELINE.connector1End}
              showMarker={!reduceMotion}
            />

            <FlowNode
              {...FLOW_STEPS[1]}
              progress={scrollYProgress}
              revealStart={FLOW_TIMELINE.context}
            />
            <VerticalConnector
              height={72}
              progress={scrollYProgress}
              start={FLOW_TIMELINE.connector2Start}
              end={FLOW_TIMELINE.connector2End}
              showMarker={!reduceMotion}
            />

            <FlowNode
              {...FLOW_STEPS[2]}
              progress={scrollYProgress}
              revealStart={FLOW_TIMELINE.model}
            />
            <VerticalConnector
              height={68}
              progress={scrollYProgress}
              start={FLOW_TIMELINE.connector3Start}
              end={FLOW_TIMELINE.connector3End}
              showMarker={!reduceMotion}
            />

            <motion.div
              style={{ opacity: hubOpacity, y: hubY }}
              className="relative mx-auto max-w-4xl"
            >
              <div className="rounded-2xl border border-border bg-panel/35 p-5 sm:p-6 shadow-[0_22px_60px_rgba(2,6,23,0.28)] backdrop-blur-xl">
                <div className="flex flex-col gap-4 md:flex-row md:items-start">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-cta/20 bg-cta/10">
                    <Bot className="h-5 w-5 text-cta" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold sm:text-xl">MCP Tool Hub</h3>
                      <span className="rounded-full border border-border bg-panel-secondary/30 px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.18em] text-text-muted">
                        Live APIs
                      </span>
                    </div>
                    <p className="text-sm leading-relaxed text-text-muted sm:text-[15px]">
                      The orchestrator dispatches tool calls to the right external
                      system, collects results, and passes them back to the model.
                    </p>
                    <div className="mt-4 rounded-xl border border-border bg-panel-secondary/25 px-3 py-2.5 font-mono text-xs text-text-muted">
                      {"github_search_code -> slack_search_messages -> db_query"}
                    </div>
                  </div>
                </div>
              </div>

              <BranchConnector
                progress={scrollYProgress}
                start={FLOW_TIMELINE.branchStart}
                end={FLOW_TIMELINE.branchEnd}
                showMarker={!reduceMotion}
              />

              <div className="mt-5 grid gap-3 md:grid-cols-3">
                {TOOL_SOURCES.map((source, index) => (
                  <ToolSourceCard
                    key={source.title}
                    source={source}
                    index={index}
                    progress={scrollYProgress}
                    revealStart={FLOW_TIMELINE.sources}
                  />
                ))}
              </div>
            </motion.div>

            <VerticalConnector
              height={84}
              progress={scrollYProgress}
              start={FLOW_TIMELINE.connector4Start}
              end={FLOW_TIMELINE.connector4End}
              showMarker={!reduceMotion}
            />
            <FlowNode
              {...FLOW_STEPS[3]}
              progress={scrollYProgress}
              revealStart={FLOW_TIMELINE.security}
            />
            <VerticalConnector
              height={72}
              progress={scrollYProgress}
              start={FLOW_TIMELINE.connector5Start}
              end={FLOW_TIMELINE.connector5End}
              showMarker={!reduceMotion}
            />
            <FlowNode
              {...FLOW_STEPS[4]}
              progress={scrollYProgress}
              revealStart={FLOW_TIMELINE.answer}
            />
          </div>
        </motion.div>
      </div>
    </section>
  );
}

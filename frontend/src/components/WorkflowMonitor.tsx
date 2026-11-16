import { ReactNode, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  Check,
  ChevronRight,
  CircleDot,
  FileSearch,
  GitBranch,
  LockKeyhole,
  Network,
  PenLine,
  Radio,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  WandSparkles,
  X,
} from "lucide-react";
import type { WorkflowEvent, WorkflowRun } from "../hooks/useWorkflow";
import { useAudio } from "../context/AudioContext";
import { Pill } from "./UI";

const stages = [
  {
    id: "deterministic",
    label: "Document check",
    short: "Check",
    Icon: FileSearch,
    description: "Lock received items and identify the gaps.",
  },
  {
    id: "orchestrator",
    label: "Orchestrator",
    short: "Plan",
    Icon: GitBranch,
    description: "Plan a single consolidated chase.",
  },
  {
    id: "drafter",
    label: "Drafter",
    short: "Draft",
    Icon: PenLine,
    description: "Write one email for every missing item.",
  },
  {
    id: "toner",
    label: "Toner",
    short: "Refine",
    Icon: WandSparkles,
    description: "Calibrate tone and jurisdiction wording.",
  },
  {
    id: "critique",
    label: "Critique QA",
    short: "Verify",
    Icon: ShieldCheck,
    description: "Check all four rules before RM review.",
  },
];

function stageState(id: string, events: WorkflowEvent[], active: boolean) {
  const latest = [...events]
    .reverse()
    .find(
      (e) =>
        e.data.node === id &&
        ["node_started", "node_completed", "node_failed"].includes(e.kind),
    );
  if (!latest) return "waiting";
  const rewrite = [...events].reverse().find((e) => e.kind === "revision");
  if (id !== "deterministic" && rewrite && latest.id < rewrite.id)
    return "waiting";
  if (latest.kind === "node_started") return active ? "working" : "stopped";
  if (latest.kind === "node_failed") return "stopped";
  if (id === "critique" && !latest.data.scorecard?.passed) return "revision";
  return "complete";
}

export default function WorkflowMonitor({
  run,
  events,
  reconnecting = false,
  drafter,
  onGenerate,
  hasDraft = false,
  generationDisabled = false,
  initialView,
  guidance,
}: {
  run: WorkflowRun | null;
  events: WorkflowEvent[];
  reconnecting?: boolean;
  drafter?: ReactNode;
  onGenerate?: () => void;
  hasDraft?: boolean;
  generationDisabled?: boolean;
  initialView?: "drafter" | "activity";
  guidance?: ReactNode;
}) {
  const [graph, setGraph] = useState(() =>
    initialView
      ? initialView === "activity"
      : localStorage.getItem("northgate-workflow-view") === "graph",
  );
  const { play } = useAudio();
  const drafterFace = useRef<HTMLDivElement>(null);
  const graphFace = useRef<HTMLDivElement>(null);
  const [faceHeight, setFaceHeight] = useState(320);
  useLayoutEffect(() => {
    const measure = () => {
      const selected = graph ? graphFace.current : drafterFace.current;
      if (selected) setFaceHeight(selected.offsetHeight);
    };
    measure();
    const observer = new ResizeObserver(measure);
    if (drafterFace.current) observer.observe(drafterFace.current);
    if (graphFace.current) observer.observe(graphFace.current);
    return () => observer.disconnect();
  }, [graph]);
  const active = run?.status === "RUNNING";
  const activity = events.filter(
    (e) =>
      !["draft_preview", "preview_reset", "provider_active"].includes(e.kind),
  );
  const feed = useRef<HTMLDivElement>(null);
  const [clock, setClock] = useState(Date.now());
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [active]);
  useEffect(() => {
    if (feed.current) feed.current.scrollTop = feed.current.scrollHeight;
  }, [activity.length]);
  const elapsed = run
    ? Math.max(
        0,
        Math.floor(
          ((run.finished_at ? Date.parse(run.finished_at) : clock) -
            Date.parse(run.started_at)) /
            1000,
        ),
      )
    : 0;
  const lastRevision = [...events].reverse().find((e) => e.kind === "revision");
  const completedDraft = [...events]
    .reverse()
    .find((e) => e.kind === "run_completed")?.data.draft;
  const passed = run?.status === "COMPLETED";
  const statusText = reconnecting
    ? "Reconnecting to live events"
    : active
      ? "Live execution"
      : passed
        ? "Ready for RM review"
        : run
          ? run.status === "BLOCKED"
            ? "QA blocked"
            : "Run stopped"
          : "Ready when you are";

  function switchView() {
    setGraph(!graph);
    localStorage.setItem(
      "northgate-workflow-view",
      graph ? "drafter" : "graph",
    );
    play("flip");
  }
  return (
    <section
      className={"workflow-monitor panel " + (active ? "is-running" : "")}
      aria-label="Live agent workflow"
    >
      <div className="workflow-top">
        <div>
          <div className="eyebrow">
            <Radio size={12} />
            AGENTS IN MOTION
          </div>
          <h2>Your AI team, in the open.</h2>
          <p>Follow the handoffs. Watch the wording take shape.</p>
        </div>
        <div className="workflow-controls">
          {onGenerate && (
            <button
              type="button"
              className="primary workflow-generate"
              disabled={generationDisabled || active}
              onClick={onGenerate}
            >
              <Sparkles size={14} />
              {active ? "Drafting…" : hasDraft ? "Redraft" : "Draft"}
            </button>
          )}
          <button
            className="workflow-view-toggle"
            type="button"
            onClick={switchView}
            data-sound="custom"
            aria-label="Switch workflow visualization"
            aria-pressed={graph}
          >
            <span className={!graph ? "selected" : ""}>
              <PenLine size={14} />
              Drafter
            </span>
            <span className={graph ? "selected" : ""}>
              <Network size={14} />
              AI workflow
            </span>
            <RotateCcw size={13} className="flip-hint" />
          </button>
        </div>
      </div>
      <div className="workflow-status">
        <Pill
          tone={active ? "purple" : passed ? "green" : run ? "amber" : "muted"}
        >
          <span className={"live-indicator " + (active ? "pulsing" : "")} />
          {statusText}
        </Pill>
        <span className="mono">
          {run
            ? `${run.case_id} · ${elapsed}s`
            : "5 stages · Human-reviewed outreach"}
        </span>
        {lastRevision && (
          <span className="revision-counter">
            <RotateCcw size={12} />
            Revision {(lastRevision.data.iteration || 2) - 1} / 3
          </span>
        )}
      </div>
      <div className={"workflow-flip-scene " + (graph ? "show-graph" : "")}>
        <div className="workflow-flip-card" style={{ height: faceHeight }}>
          <div
            className="workflow-face drafter-face"
            ref={drafterFace}
            aria-hidden={graph}
            inert={graph}
          >
            {drafter ||
              (active ? (
                <StreamingDraftPreview events={events} active />
              ) : completedDraft ? (
                <div className="draft-read-preview">
                  <div className="streaming-heading">
                    <span>
                      <PenLine size={13} />
                      CONSOLIDATED DRAFT
                    </span>
                    <Pill
                      tone={completedDraft.scorecard.passed ? "green" : "amber"}
                    >
                      {completedDraft.status}
                    </Pill>
                  </div>
                  <div className="streaming-subject">
                    <span>SUBJECT</span>
                    <strong>{completedDraft.subject}</strong>
                  </div>
                  <div className="streaming-body">{completedDraft.body}</div>
                  <div className="streaming-footnote">
                    <ShieldCheck size={13} />
                    Inspecting this run’s draft. Review and approve it in the
                    case workspace.
                  </div>
                </div>
              ) : (
                <div className="empty">
                  <PenLine size={30} />
                  <h3>Your draft will appear here.</h3>
                  <p>
                    Choose Draft to start the agents. Flip to AI workflow at any
                    point to follow their progress.
                  </p>
                </div>
              ))}
          </div>
          <div
            className="workflow-face graph-face"
            ref={graphFace}
            aria-hidden={!graph}
            inert={!graph}
          >
            <div className="agent-canvas">
              <svg
                className="agent-connections"
                viewBox="0 0 1000 280"
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                {stages.slice(0, 4).map((s, i) => {
                  const state = stageState(s.id, events, !!active);
                  return (
                    <g key={s.id} className={"agent-edge " + state}>
                      <path d={`M ${100 + i * 200} 88 L ${300 + i * 200} 88`} />
                      <circle r="3">
                        <animateMotion
                          dur="2s"
                          repeatCount="indefinite"
                          path={`M ${100 + i * 200} 88 L ${300 + i * 200} 88`}
                        />
                      </circle>
                    </g>
                  );
                })}
                <path
                  className={
                    "return-edge " + (lastRevision ? "has-revision" : "")
                  }
                  d="M 900 110 L 900 239 Q 900 250 885 250 L 315 250 Q 300 250 300 236 L 300 112"
                />
                {lastRevision && (
                  <circle r="3" className="revision-particle">
                    <animateMotion
                      dur="3s"
                      repeatCount="indefinite"
                      path="M 900 110 L 900 239 Q 900 250 885 250 L 315 250 Q 300 250 300 236 L 300 112"
                    />
                  </circle>
                )}
              </svg>
              <div className="graph-agent-row">
                {stages.map(({ id, label, short, Icon, description }) => {
                  const state = stageState(id, events, !!active);
                  return (
                    <div className={"graph-agent " + state} key={id}>
                      <span className="graph-node-code">
                        {short.toUpperCase()}
                      </span>
                      <div className="graph-agent-orb">
                        <span className="graph-orbit" />
                        <Icon size={25} />
                        {state === "complete" && (
                          <span className="graph-check">
                            <Check size={10} />
                          </span>
                        )}
                      </div>
                      <strong>{label}</strong>
                      <span className="stage-state">
                        {state === "working"
                          ? "Processing…"
                          : state === "complete"
                            ? "Complete"
                            : state === "revision"
                              ? "Revise"
                              : state === "stopped"
                                ? "Stopped"
                                : "Standby"}
                      </span>
                      <p className="graph-node-description">{description}</p>
                    </div>
                  );
                })}
              </div>
              <div className="graph-return-label">
                <RotateCcw size={12} />
                {lastRevision
                  ? "Critique feedback is routed back for revision"
                  : "Critique → Orchestrator · up to 3 rewrites"}
              </div>
            </div>
            <div className={"graph-review-gate " + (passed ? "unlocked" : "")}>
              <LockKeyhole size={14} />
              {passed ? "RM REVIEW READY" : "RM REVIEW GATE"}
              <ChevronRight size={14} />
              <span>
                {passed ? "Awaiting your decision" : "Unlocks after QA passes"}
              </span>
            </div>
          </div>
        </div>
      </div>
      {guidance && <div className="workflow-guidance">{guidance}</div>}
      <div className="live-feed">
        <div className="live-feed-heading">
          <span>
            <span className="dot" />
            LIVE ACTIVITY
          </span>
          <small>{activity.length} events · actual workflow updates</small>
        </div>
        <div
          className="live-feed-entries"
          ref={feed}
          role="log"
          aria-live="polite"
          aria-relevant="additions"
        >
          {!activity.length ? (
            <div className="feed-empty">
              <Radio size={16} />
              <p>Your team’s actions will appear here as they happen.</p>
            </div>
          ) : (
            activity.map((event) => (
              <div className={"feed-entry " + event.kind} key={event.id}>
                <span className="feed-event-icon">
                  {event.kind === "node_completed" ? (
                    <Check size={12} />
                  ) : event.kind === "revision" ||
                    event.kind === "provider_failover" ? (
                    <RotateCcw size={12} />
                  ) : event.kind === "run_failed" ? (
                    <X size={12} />
                  ) : (
                    <CircleDot size={12} />
                  )}
                </span>
                <div>
                  <p>{event.data.summary}</p>
                  {event.data.provider && <small>{event.data.provider}</small>}
                </div>
                <time>
                  {new Date(event.created_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </time>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}

export function StreamingDraftPreview({
  events,
  active,
}: {
  events: WorkflowEvent[];
  active: boolean;
}) {
  const lastReset = [...events]
    .reverse()
    .find((e) => e.kind === "preview_reset");
  const preview = [...events]
    .reverse()
    .find(
      (e) => e.kind === "draft_preview" && (!lastReset || e.id > lastReset.id),
    );
  // Keep the completed first wording visible while Toner waits for its first token.
  // A provider failover never carries over the failed provider's partial wording.
  const firstWording =
    lastReset?.data.agent === "toner"
      ? [...events]
          .reverse()
          .find((e) => e.kind === "draft_preview" && e.data.agent === "drafter")
      : undefined;
  const visibleBody = preview?.data.body || firstWording?.data.body;
  const body = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (body.current) body.current.scrollTop = body.current.scrollHeight;
  }, [visibleBody]);
  return (
    <div className="streaming-draft">
      <div className="streaming-heading">
        <span>
          <span className="live-indicator pulsing" />
          {lastReset?.data.agent === "toner"
            ? "TONER · LIVE REFINEMENT"
            : "DRAFTER · LIVE PREVIEW"}
        </span>
        <Pill tone="amber">Unreviewed</Pill>
      </div>
      <div className="streaming-subject">
        <span>SUBJECT</span>
        <strong>
          {preview?.data.subject ||
            firstWording?.data.subject ||
            "Preparing the consolidated email…"}
        </strong>
      </div>
      <div
        className="streaming-body"
        ref={body}
        aria-label="Streaming draft preview"
      >
        {visibleBody || (
          <div className="draft-waiting">
            <WandSparkles size={26} />
            <h3>
              {lastReset
                ? "Waiting for the first words…"
                : "Your agents are checking and planning."}
            </h3>
            <p>The email will appear here as the provider streams it.</p>
            <div className="writing-lines">
              <i />
              <i />
              <i />
            </div>
          </div>
        )}
        {visibleBody && active && <span className="writing-caret" />}
      </div>
      <div className="streaming-footnote">
        <ShieldCheck size={13} />
        Live wording may change during refinement or revision. RM approval is
        available after the final QA pass.
      </div>
    </div>
  );
}

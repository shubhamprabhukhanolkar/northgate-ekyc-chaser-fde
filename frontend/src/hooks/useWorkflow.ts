import { useCallback, useEffect, useRef, useState } from "react";
import { api, post, Draft } from "../api";
import { useAudio } from "../context/AudioContext";
import type { SoundCue } from "../audio/sound";
import { useDrafting } from "../context/DraftingContext";

export type WorkflowRun = {
  id: string;
  case_id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
};
export type WorkflowEvent = {
  id: number;
  run_id: string;
  kind: string;
  created_at: string;
  data: {
    node?: string;
    agent?: string;
    summary?: string;
    provider?: string;
    iteration?: number;
    subject?: string;
    body?: string;
    latency_ms?: number;
    feedback?: string[];
    scorecard?: Draft["scorecard"];
    draft?: Draft;
    passed?: boolean;
  };
};
const cues: Record<string, SoundCue> = {
  deterministic: "scan",
  orchestrator: "plan",
  drafter: "write",
  toner: "polish",
  critique: "verify",
};

export function useWorkflow(caseId = "") {
  const { registerBusy } = useDrafting();
  const busyOwner = useRef(Symbol("workflow"));
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [reconnecting, setReconnecting] = useState(false);
  const [starting, setStarting] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const source = useRef<EventSource | null>(null);
  const runRef = useRef<WorkflowRun | null>(null);
  const connectRef = useRef<(value: WorkflowRun) => void>(() => {});
  const { play } = useAudio();
  useEffect(() => {
    const owner = busyOwner.current;
    registerBusy(owner, starting || run?.status === "RUNNING");
    return () => registerBusy(owner, false);
  }, [starting, run?.status, registerBusy]);

  useEffect(() => {
    let disposed = false;
    runRef.current = null;
    source.current?.close();
    setRun(null);
    setEvents([]);
    setError("");
    setReconnecting(false);
    setLoaded(false);
    const connect = (value: WorkflowRun) => {
      if (disposed || runRef.current?.id === value.id) return;
      source.current?.close();
      runRef.current = value;
      setRun(value);
      setEvents([]);
      setError("");
      const subscribedAt = Date.now();
      const stream = new EventSource(`/api/runs/${value.id}/events`, {
        withCredentials: true,
      });
      source.current = stream;
      stream.onopen = () => !disposed && setReconnecting(false);
      stream.onerror = () => {
        if (!disposed && runRef.current?.status === "RUNNING")
          setReconnecting(true);
      };
      stream.addEventListener("workflow", (message) => {
        if (disposed || source.current !== stream) return;
        const event: WorkflowEvent = JSON.parse((message as MessageEvent).data);
        setEvents((previous) =>
          previous.some((item) => item.id === event.id)
            ? previous
            : [...previous, event],
        );
        if (
          new Date(event.created_at).getTime() >= subscribedAt &&
          value.status === "RUNNING"
        ) {
          if (event.kind === "node_completed")
            play(cues[event.data.node || ""] || "tap");
          if (event.kind === "revision" || event.kind === "provider_failover")
            play("reroute");
          if (event.kind === "run_completed")
            play(event.data.passed ? "ready" : "notice");
          if (event.kind === "run_failed") play("notice");
        }
        if (event.kind === "run_completed" || event.kind === "run_failed") {
          const status =
            event.kind === "run_failed"
              ? "FAILED"
              : event.data.passed
                ? "COMPLETED"
                : "BLOCKED";
          const terminal = { ...value, status, finished_at: event.created_at };
          runRef.current = terminal;
          setRun(terminal);
          setReconnecting(false);
          stream.close();
        }
      });
    };
    connectRef.current = connect;
    const refresh = () =>
      api<WorkflowRun | null>(
        `/runs/latest${caseId ? "?case_id=" + encodeURIComponent(caseId) : ""}`,
      )
        .then((value) => {
          if (!disposed) {
            if (value) connect(value);
            setLoaded(true);
          }
        })
        .catch((e) => !disposed && setError(e.message));
    void refresh();
    const interval = setInterval(refresh, 4000);
    return () => {
      disposed = true;
      clearInterval(interval);
      source.current?.close();
    };
  }, [caseId, play]);

  const start = useCallback(
    async (
      targetCaseId = caseId,
      request: { mode: "auto" | "guided"; instructions?: string } = {
        mode: "auto",
      },
    ) => {
      if (!targetCaseId) return;
      setStarting(true);
      setError("");
      try {
        const value = await post<WorkflowRun>(
          `/cases/${targetCaseId}/runs`,
          request,
        );
        connectRef.current(value);
        return value;
      } catch (e) {
        setError((e as Error).message);
        throw e;
      } finally {
        setStarting(false);
      }
    },
    [caseId],
  );

  return {
    run,
    events,
    start,
    starting,
    loaded,
    reconnecting,
    error,
    active: starting || run?.status === "RUNNING",
  };
}

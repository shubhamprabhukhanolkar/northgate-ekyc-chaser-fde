import { useState } from "react";
import {
  Braces,
  Check,
  FileSearch,
  Filter,
  GitBranch,
  MessageCircle,
  PenLine,
  Radio,
  ShieldCheck,
  WandSparkles,
  X,
} from "lucide-react";
import { api, Case } from "../api";
import {
  PageHead,
  Pill,
  Loading,
  ErrorBox,
  Empty,
  usePoll,
} from "../components/UI";

type Trace = {
  id: number;
  run_id: string;
  case_id: string | null;
  node: string;
  payload: any;
  created_at: string;
};
const agents = [
  { id: "deterministic", name: "Document check", Icon: FileSearch },
  { id: "orchestrator", name: "Orchestrator", Icon: GitBranch },
  { id: "drafter", name: "Drafter", Icon: PenLine },
  { id: "toner", name: "Toner", Icon: WandSparkles },
  { id: "critique", name: "Critique QA", Icon: ShieldCheck },
  { id: "policy_copilot", name: "Portal Guide", Icon: MessageCircle },
];

export default function TracePage() {
  const [caseId, setCaseId] = useState("");
  const [agent, setAgent] = useState("");
  const [selected, setSelected] = useState<Trace | null>(null);
  const { data: cases } = usePoll(() => api<Case[]>("/cases"));
  const { data: traces, error } = usePoll(
    () =>
      api<Trace[]>(
        "/traces" + (caseId ? "?case_id=" + encodeURIComponent(caseId) : ""),
      ),
    [caseId],
    3000,
  );
  const visible =
    traces?.filter((trace) => !agent || trace.node === agent) || [];
  return (
    <>
      <PageHead
        eyebrow="AGENT TRACE"
        title="Every step. An open book."
        description="A read-only record of all agent activity. Inspect handoffs, checks, revisions and Portal Guide answers."
        action={
          <select
            aria-label="Filter traces by case"
            value={caseId}
            onChange={(e) => setCaseId(e.target.value)}
          >
            <option value="">All cases and portal conversations</option>
            {cases?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.id} · {c.company}
              </option>
            ))}
          </select>
        }
      />
      <ErrorBox message={error} />
      <div className="trace-readonly-banner">
        <span>
          <Radio size={15} />
          <strong>Live execution history</strong>
          <span>Updates every 3 seconds</span>
        </span>
        <Pill tone="purple">Read-only</Pill>
      </div>
      <div className="trace-agent-summary">
        {agents.map(({ id, name, Icon }) => (
          <button
            type="button"
            key={id}
            aria-pressed={agent === id}
            onClick={() => setAgent(agent === id ? "" : id)}
          >
            <Icon size={19} />
            <strong>{name}</strong>
            <span>
              {traces?.filter((t) => t.node === id).length || 0}
              <small> events</small>
            </span>
          </button>
        ))}
      </div>
      <section className="panel trace-explorer">
        <div className="panel-heading">
          <div>
            <h2>
              <Braces size={18} />
              Execution ledger
            </h2>
            <p>
              Latest {traces?.length || 0} events · Select a row to inspect its
              recorded evidence.
            </p>
          </div>
          <div className="trace-filter-actions">
            <Filter size={14} />
            <select
              aria-label="Filter by agent"
              value={agent}
              onChange={(e) => setAgent(e.target.value)}
            >
              <option value="">All agents</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        {!traces ? (
          <Loading />
        ) : !visible.length ? (
          <Empty title="No matching agent events">
            <p>
              Activity appears here after agents run in Gap Workspace or answer
              in Portal Guide.
            </p>
          </Empty>
        ) : (
          <div className="trace-event-list">
            {visible.map((trace) => {
              const info = agents.find((a) => a.id === trace.node);
              const Icon = info?.Icon || Braces;
              const failed = trace.payload.status === "error";
              const score =
                trace.node === "critique"
                  ? trace.payload.result?.tone_score
                  : undefined;
              return (
                <button
                  className="trace-event-row"
                  key={trace.id}
                  onClick={() => setSelected(trace)}
                >
                  <span
                    className={"trace-event-icon " + (failed ? "failed" : "")}
                  >
                    <Icon size={18} />
                  </span>
                  <div>
                    <strong>{info?.name || trace.node}</strong>
                    <p>
                      {trace.case_id || "Portal conversation"}
                      <span> · </span>
                      {new Date(trace.created_at).toLocaleString()}
                    </p>
                    <small>
                      Run {trace.run_id.slice(0, 8)}
                      {trace.payload.iteration
                        ? ` · Iteration ${trace.payload.iteration}`
                        : ""}
                    </small>
                  </div>
                  <div className="trace-event-tags">
                    <Pill tone={failed ? "rose" : "green"}>
                      {failed ? (
                        "Failed"
                      ) : (
                        <>
                          <Check size={11} />
                          Recorded
                        </>
                      )}
                    </Pill>
                    {score !== undefined && <Pill>{score}% tone</Pill>}
                    <Pill>{trace.payload.provider || "Rules"}</Pill>
                  </div>
                  <Braces size={15} />
                </button>
              );
            })}
          </div>
        )}
      </section>
      {selected && (
        <div className="drawer-overlay" onClick={() => setSelected(null)}>
          <section className="json-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="panel-heading">
              <div>
                <div className="eyebrow">RECORDED AGENT EVIDENCE</div>
                <h2>
                  {agents.find((a) => a.id === selected.node)?.name ||
                    selected.node}
                </h2>
              </div>
              <button
                type="button"
                className="icon-button"
                aria-label="Close trace drawer"
                onClick={() => setSelected(null)}
              >
                <X />
              </button>
            </div>
            <p className="mono">
              {selected.case_id || "Portal conversation"} · {selected.run_id}
            </p>
            <pre>{JSON.stringify(selected.payload, null, 2)}</pre>
            <p className="muted">
              Recorded {new Date(selected.created_at).toLocaleString()}
            </p>
          </section>
        </div>
      )}
    </>
  );
}

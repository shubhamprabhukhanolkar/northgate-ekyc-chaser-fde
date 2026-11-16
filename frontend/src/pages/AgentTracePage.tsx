import { useState } from "react";
import { Workflow, Check, ArrowDown, RotateCcw, Braces, X } from "lucide-react";
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
  case_id: string;
  node: string;
  payload: any;
  created_at: string;
};
const nodes = [
  [
    "deterministic",
    "Gap & received-document check",
    "The authoritative checklist establishes the safe scope.",
  ],
  [
    "orchestrator",
    "Orchestrator",
    "Plans the consolidated chase and handles critique feedback.",
  ],
  [
    "drafter",
    "Drafter",
    "Creates one email containing every outstanding document.",
  ],
  [
    "toner",
    "Toner",
    "Calibrates formality, urgency and jurisdiction language.",
  ],
  [
    "critique",
    "Critique QA",
    "Four-rule gate; failures return for up to three rewrites.",
  ],
];
export default function AgentTracePage() {
  const [cid, setCid] = useState("");
  const { data: cases } = usePoll(() => api<Case[]>("/cases"));
  const { data: traces, error } = usePoll(
    () => api<Trace[]>("/traces" + (cid ? "?case_id=" + cid : "")),
    [cid],
    5000,
  );
  const [selected, setSelected] = useState<Trace | null>(null);
  const run = traces?.[0]?.run_id;
  const latest = traces?.filter((t) => t.run_id === run) || [];
  return (
    <>
      <PageHead
        eyebrow="VISIBLE BY DESIGN"
        title="Every step. An open book."
        description="Inspect the live agent workflow, critique revisions and structured execution evidence."
        action={
          <select
            aria-label="Filter traces by case"
            value={cid}
            onChange={(e) => setCid(e.target.value)}
          >
            <option value="">All cases</option>
            {cases?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.id} · {c.company}
              </option>
            ))}
          </select>
        }
      />
      <ErrorBox message={error} />
      {!traces ? (
        <Loading />
      ) : (
        <>
          <div className="trace-layout">
            <section className="panel flow-panel">
              <div className="panel-heading">
                <h2>
                  <Workflow size={20} />
                  The chaser pipeline
                </h2>
                <Pill tone="purple">LangGraph</Pill>
              </div>
              <div className="graph">
                {nodes.map(([id, name, description], i) => {
                  const trace = latest.find((t) => t.node === id);
                  return (
                    <div className="graph-stage" key={id}>
                      <button
                        className={"graph-node " + (trace ? "executed" : "")}
                        disabled={!trace}
                        onClick={() => setSelected(trace || null)}
                      >
                        <div className="node-number">
                          {trace ? (
                            <Check size={17} />
                          ) : (
                            String(i + 1).padStart(2, "0")
                          )}
                        </div>
                        <div>
                          <strong>{name}</strong>
                          <p>{description}</p>
                        </div>
                        {trace && <Braces size={16} />}
                      </button>
                      {i < 4 && <ArrowDown size={18} className="graph-arrow" />}
                    </div>
                  );
                })}
                <div className="loop-label">
                  <RotateCcw size={15} />
                  Critique failure → Orchestrator → Rewrite · max 3
                </div>
                <div className="human-gate-node">
                  PASS → RM REVIEW GATE → SYNTHETIC OUTBOX
                </div>
              </div>
            </section>
            <section className="panel execution">
              <div className="panel-heading">
                <h2>Execution ledger</h2>
                <Pill>{traces.length} events</Pill>
              </div>
              {!traces.length ? (
                <Empty title="No agent runs yet">
                  <p>Generate a draft in the workspace to see its trace.</p>
                </Empty>
              ) : (
                <div className="execution-list">
                  {traces.map((t) => (
                    <button
                      className="execution-row"
                      key={t.id}
                      onClick={() => setSelected(t)}
                    >
                      <span className="dot" />
                      <div>
                        <strong>{t.node}</strong>
                        <p>
                          {t.case_id} ·{" "}
                          {new Date(t.created_at).toLocaleTimeString()}
                        </p>
                      </div>
                      <Pill>{t.payload.provider || "rules"}</Pill>
                      <Braces size={14} />
                    </button>
                  ))}
                </div>
              )}
            </section>
          </div>
          {selected && (
            <div className="drawer-overlay" onClick={() => setSelected(null)}>
              <section
                className="json-drawer"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="panel-heading">
                  <div>
                    <div className="eyebrow">STRUCTURED EVIDENCE</div>
                    <h2>{selected.node}</h2>
                  </div>
                  <button
                    className="icon-button"
                    aria-label="Close trace drawer"
                    onClick={() => setSelected(null)}
                  >
                    <X />
                  </button>
                </div>
                <p className="mono">
                  {selected.case_id} · {selected.run_id}
                </p>
                <pre>{JSON.stringify(selected.payload, null, 2)}</pre>
                <p className="muted">
                  Recorded {new Date(selected.created_at).toLocaleString()}
                </p>
              </section>
            </div>
          )}
        </>
      )}
    </>
  );
}

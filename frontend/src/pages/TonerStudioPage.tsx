import { useEffect, useState } from "react";
import { SlidersHorizontal, Play, Save, Check, History } from "lucide-react";
import { api, post, put } from "../api";
import { useAuth } from "../context/AuthContext";
import { PageHead, Pill, ErrorBox, Loading } from "../components/UI";
type Tone = { formality: number; urgency: string; jurisdiction_clause: string };
type Prompt = { content: string; settings: Tone; version: number };
export default function TonerStudioPage() {
  const [prompts, setPrompts] = useState<Record<string, Prompt> | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [agent, setAgent] = useState("toner");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [result, setResult] = useState<any>(null);
  const [message, setMessage] = useState("");
  const { user } = useAuth();
  const writable = user?.role === "admin";
  const load = () =>
    api("/prompts").then((r) => {
      setPrompts(r.active);
      setHistory(r.history);
    });
  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);
  function change(key: string, value: any) {
    setResult(null);
    setMessage("");
    setPrompts((p) =>
      p ? { ...p, [agent]: { ...p[agent], [key]: value } } : p,
    );
  }
  async function execute(action: string) {
    setBusy(action);
    setError("");
    try {
      const candidate = {
        prompts: Object.fromEntries(
          Object.entries(prompts!).map(([k, p]) => [
            k,
            { content: p.content, settings: p.settings },
          ]),
        ),
        regression_id: result?.id,
      };
      if (action === "test") setResult(await post("/prompts/test", candidate));
      else {
        await put("/prompts", candidate);
        setMessage(
          "Prompt versions saved. The next agent run will use these settings.",
        );
        setResult(null);
        await load();
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  return (
    <>
      <PageHead
        eyebrow="PROMPT & TONER STUDIO"
        title="The right words. Your standards."
        description="Tune the agent prompts and voice, then prove the change against five synthetic cases."
      />
      <ErrorBox message={error} />
      {message && <div className="success">{message}</div>}
      {!prompts ? (
        <Loading />
      ) : (
        <>
          <div className="studio-grid">
            <section className="panel prompt-editor">
              <div className="tabs">
                {["orchestrator", "drafter", "toner", "critique"].map((a) => (
                  <button
                    key={a}
                    className={a === agent ? "active" : ""}
                    onClick={() => setAgent(a)}
                  >
                    {a[0].toUpperCase() + a.slice(1)}
                  </button>
                ))}
              </div>
              <div className="panel-heading">
                <h2>System instructions</h2>
                <Pill>Version {prompts[agent].version}</Pill>
              </div>
              <textarea
                aria-label={`${agent} system prompt`}
                className="prompt-textarea"
                readOnly={!writable}
                value={prompts[agent].content}
                onChange={(e) => change("content", e.target.value)}
              />
              <div className="rule-note">
                <SlidersHorizontal size={18} />
                <p>
                  Prompt changes are versioned. Safety rules remain enforced by
                  code and the human review gate.
                </p>
              </div>
            </section>
            <section className="panel tone-controls">
              <div className="panel-heading">
                <h2>Voice calibration</h2>
                <SlidersHorizontal size={19} />
              </div>
              <p className="muted">
                The dedicated Toner agent actively rewrites the draft using
                these controls.
              </p>
              <label>
                Formality <strong>{prompts.toner.settings.formality}%</strong>
                <input
                  aria-label="Formality"
                  type="range"
                  min="0"
                  max="100"
                  disabled={!writable}
                  value={prompts.toner.settings.formality}
                  onChange={(e) => {
                    setResult(null);
                    setPrompts({
                      ...prompts,
                      toner: {
                        ...prompts.toner,
                        settings: {
                          ...prompts.toner.settings,
                          formality: Number(e.target.value),
                        },
                      },
                    });
                  }}
                />
              </label>
              <div className="range-labels">
                <span>Conversational</span>
                <span>Institutional</span>
              </div>
              {[
                [
                  "Urgency",
                  "urgency",
                  ["First Chase", "3-Day Nudge", "Escalation"],
                ],
                [
                  "Jurisdiction clause",
                  "jurisdiction_clause",
                  ["Auto", "UK FCA", "MAS Singapore", "US FinCEN"],
                ],
              ].map(([title, key, options]) => (
                <label key={String(key)}>
                  {String(title)}
                  <select
                    aria-label={String(title)}
                    disabled={!writable}
                    value={(prompts.toner.settings as any)[String(key)]}
                    onChange={(e) => {
                      setResult(null);
                      setPrompts({
                        ...prompts,
                        toner: {
                          ...prompts.toner,
                          settings: {
                            ...prompts.toner.settings,
                            [String(key)]: e.target.value,
                          },
                        },
                      });
                    }}
                  >
                    {(options as string[]).map((o) => (
                      <option key={o}>{o}</option>
                    ))}
                  </select>
                </label>
              ))}
              <Pill tone="purple">Synthetic policy clauses</Pill>
            </section>
          </div>
          <section className="panel regression">
            <div className="panel-heading">
              <div>
                <div className="eyebrow">CONFIDENCE BEFORE CHANGE</div>
                <h2>Five-case regression</h2>
                <p>
                  Checks the exact candidate prompts against received-document
                  locks, completeness, claims and tone.
                </p>
              </div>
              <div className="actions">
                <button
                  className="secondary"
                  disabled={!!busy || !writable}
                  onClick={() => execute("test")}
                >
                  <Play size={15} />
                  {busy === "test" ? "Testing 5 cases…" : "Run golden set"}
                </button>
                <button
                  className="primary"
                  disabled={!!busy || !result?.passed || !writable}
                  onClick={() => execute("save")}
                >
                  <Save size={15} />
                  Save version
                </button>
              </div>
            </div>
            {!writable && (
              <p className="muted">
                Sign in as admin to test and publish prompt changes.
              </p>
            )}
            {result && (
              <div className="regression-results">
                {result.results.map((r: any) => (
                  <div key={r.case_id}>
                    <span
                      className={
                        r.scorecard.passed ? "green-text" : "rose-text"
                      }
                    >
                      <Check size={16} />
                      {r.case_id}
                    </span>
                    <Pill tone={r.scorecard.passed ? "green" : "rose"}>
                      {r.scorecard.passed ? "Passed" : "Blocked"} ·{" "}
                      {r.scorecard.tone_score}%
                    </Pill>
                  </div>
                ))}
              </div>
            )}
          </section>
          <section className="panel history">
            <h2>
              <History size={18} />
              Version history
            </h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>Version</th>
                    <th>Changed by</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h) => (
                    <tr key={h.id}>
                      <td>{h.agent}</td>
                      <td className="mono">v{h.version}</td>
                      <td>{h.actor}</td>
                      <td>{new Date(h.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  );
}

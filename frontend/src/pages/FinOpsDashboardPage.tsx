import { useState } from "react";
import {
  ShieldCheck,
  Download,
  ArrowRight,
  Activity,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import { api, put, money } from "../api";
import { useAuth } from "../context/AuthContext";
import {
  PageHead,
  Metric,
  Pill,
  ErrorBox,
  Loading,
  Empty,
  usePoll,
} from "../components/UI";
export default function FinOpsDashboardPage() {
  const { data, error } = usePoll(() => api("/finops"), [], 5000);
  const { data: runtime, setData: setRuntime } = usePoll(
    () => api("/runtime"),
    [],
    5000,
  );
  const [actionError, setError] = useState("");
  const { user } = useAuth();
  function download() {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "northgate-finops.json";
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <>
      <PageHead
        eyebrow="FINOPS & BUSINESS IMPACT"
        title="Clarity on cost. Focus on impact."
        description="Measured agent spend, visible provider resilience and the business case behind the first slice."
        action={
          <button className="secondary" onClick={download} disabled={!data}>
            <Download size={14} />
            Export telemetry
          </button>
        }
      />
      <ErrorBox message={error || actionError} />
      {!data ? (
        <Loading />
      ) : (
        <>
          <div className="metrics">
            <Metric
              label="Potential case-days saved"
              value="3,000"
              note="Projected per month · 400 cases × 3 × 2.5d"
              tone="green-text"
            />
            <Metric
              label="Total measured AI spend"
              value={money(data.cost_gbp)}
              note={`${money(data.cost_usd, "USD")} · Configurable pricing estimates`}
            />
            <Metric
              label="Provider failovers"
              value={data.failovers}
              note="Successful Gemini → Groq recovery calls"
              tone="purple-text"
            />
            <Metric
              label="RM discard rate"
              value={(data.discard_rate * 100).toFixed(1) + "%"}
              note="Discarded / (sent + discarded) drafts"
            />
          </div>
          <div className="two-columns">
            <section className="panel">
              <div className="panel-heading">
                <h2>Chase time, reclaimed.</h2>
                <Pill tone="green">Projected first-slice impact</Pill>
              </div>
              <p className="muted">
                Historical chasing contributes 17 of 62 onboarding days. This
                slice targets each chase round.
              </p>
              <div className="comparison">
                <div>
                  <span>Historical round</span>
                  <strong>5.5 days</strong>
                </div>
                <div className="bar-track">
                  <span style={{ width: "100%" }} />
                </div>
                <div>
                  <span>Target round</span>
                  <strong className="green-text">3.0 days</strong>
                </div>
                <div className="bar-track green">
                  <span style={{ width: "54.5%" }} />
                </div>
              </div>
              <div className="roi-equation">
                <span>400 cases</span>
                <span>×</span>
                <span>3 rounds</span>
                <span>×</span>
                <span>2.5 days</span>
                <ArrowRight size={16} />
                <strong>3,000</strong>
              </div>
              <p className="muted small-text">
                This is a capacity projection, not a measured onboarding
                outcome. No labor savings are assumed.
              </p>
            </section>
            <section className="panel">
              <div className="panel-heading">
                <h2>
                  <Activity size={18} />
                  Provider resilience
                </h2>
                <Pill tone={runtime?.offline_demo ? "amber" : "green"}>
                  {runtime?.offline_demo ? "Offline fixtures" : "Direct API"}
                </Pill>
              </div>
              <div className="provider-grid">
                <div>
                  <div className="eyebrow">PRIMARY</div>
                  <strong>Google Gemini</strong>
                  <p className="mono">{runtime?.gemini_model}</p>
                  <Pill tone={runtime?.gemini_configured ? "green" : "amber"}>
                    {runtime?.gemini_configured
                      ? "Key configured"
                      : "Key missing"}
                  </Pill>
                </div>
                <div>
                  <div className="eyebrow">BACKUP</div>
                  <strong>Groq</strong>
                  <p className="mono">{runtime?.groq_model}</p>
                  <Pill tone={runtime?.groq_configured ? "green" : "amber"}>
                    {runtime?.groq_configured
                      ? "Key configured"
                      : "Key missing"}
                  </Pill>
                </div>
              </div>
              <div className="outage-toggle">
                <div>
                  <strong>Simulate Gemini outage</strong>
                  <p>Routes recoverable calls to Groq for live verification.</p>
                </div>
                <button
                  className="icon-button"
                  title="Toggle simulated Gemini outage"
                  disabled={user?.role !== "admin"}
                  aria-pressed={!!runtime?.simulate_outage}
                  onClick={async () => {
                    try {
                      await put("/runtime/outage", {
                        enabled: !runtime?.simulate_outage,
                      });
                      setRuntime(await api("/runtime"));
                    } catch (e) {
                      setError((e as Error).message);
                    }
                  }}
                >
                  {runtime?.simulate_outage ? (
                    <ToggleRight size={35} className="purple-text" />
                  ) : (
                    <ToggleLeft size={35} />
                  )}
                </button>
              </div>
              <div className="rule-note">
                <ShieldCheck size={17} />
                <p>
                  API keys stay on the server. Every provider attempt and
                  successful usage record appears in the ledger.
                </p>
              </div>
            </section>
          </div>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Agent-level economics</h2>
                <p>
                  Usage and latency from actual recorded executions. Offline
                  fixtures have zero billed tokens.
                </p>
              </div>
              <Pill>{data.calls} attempts</Pill>
            </div>
            {data.agents.length ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Agent</th>
                      <th>Provider</th>
                      <th>Calls</th>
                      <th>Input tokens</th>
                      <th>Output tokens</th>
                      <th>Avg latency</th>
                      <th>Cost GBP</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.agents.map((a: any) => (
                      <tr key={a.agent_name + a.provider}>
                        <td>
                          <span className="agent-name">
                            <span className="dot" />
                            {a.agent_name}
                          </span>
                        </td>
                        <td>
                          <Pill>{a.provider}</Pill>
                        </td>
                        <td className="mono">{a.calls}</td>
                        <td className="mono">
                          {a.prompt_tokens.toLocaleString()}
                        </td>
                        <td className="mono">
                          {a.completion_tokens.toLocaleString()}
                        </td>
                        <td className="mono">{Math.round(a.latency_ms)} ms</td>
                        <td className="mono purple-text">
                          {money(a.cost_gbp)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Empty title="Telemetry begins with the first run">
                <p>Generate a draft or ask the policy copilot.</p>
              </Empty>
            )}
          </section>
          <div className="two-columns">
            <section className="panel">
              <h2>Per-case cost</h2>
              {data.cases.map((c: any) => (
                <div className="cost-row" key={c.case_id || "policy"}>
                  <span className="mono">{c.case_id || "Policy copilot"}</span>
                  <strong>{money(c.cost_usd, "USD")}</strong>
                </div>
              ))}
            </section>
            <section className="panel">
              <h2>Provider attempt status</h2>
              {data.providers.map((p: any) => (
                <div className="cost-row" key={p.provider + p.status}>
                  <span>
                    {p.provider} · {p.status}
                  </span>
                  <Pill tone={p.status === "error" ? "rose" : "green"}>
                    {p.calls} calls
                  </Pill>
                </div>
              ))}
              <p className="muted small-text">
                Failed attempts record unknown usage as zero; provider-billed
                usage may differ. USD/GBP and model rates are configurable
                estimates.
              </p>
            </section>
          </div>
        </>
      )}
    </>
  );
}

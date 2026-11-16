import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import {
  LockKeyhole,
  Sparkles,
  Check,
  Send,
  Trash2,
  ShieldCheck,
  FileText,
  ArrowRight,
  Copy,
} from "lucide-react";
import { api, post, put, Case, Checklist, Draft, label } from "../api";
import { useAuth } from "../context/AuthContext";
import { PageHead, Pill, ErrorBox, Loading, Empty } from "../components/UI";
export default function ChaserWorkspacePage() {
  const [params, setParams] = useSearchParams();
  const [cases, setCases] = useState<Case[]>([]);
  const [cid, setCid] = useState(params.get("case") || "NG-2026-0841");
  const [data, setData] = useState<{
    checklist: Checklist;
    draft: Draft | null;
  } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [reason, setReason] = useState("");
  const [showDiscard, setShowDiscard] = useState(false);
  const [message, setMessage] = useState("");
  const [approval, setApproval] = useState("");
  const { user } = useAuth();
  const canReview = ["rm", "admin"].includes(user?.role || "");
  const canGenerate = ["rm", "admin", "analyst"].includes(user?.role || "");
  async function load() {
    const result = await api<{ checklist: Checklist; draft: Draft | null }>(
      "/cases/" + cid,
    );
    setData(result);
    setSubject(result.draft?.subject || "");
    setBody(result.draft?.body || "");
  }
  useEffect(() => {
    api<Case[]>("/cases")
      .then(setCases)
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    setData(null);
    setMessage("");
    setApproval("");
    load().catch((e) => setError(e.message));
    setParams({ case: cid }, { replace: true });
  }, [cid]);
  async function perform(name: string, fn: () => Promise<any>) {
    setBusy(name);
    setError("");
    setMessage("");
    try {
      await fn();
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  const draft = data?.draft;
  const dirty = subject !== draft?.subject || body !== draft?.body;
  return (
    <>
      <PageHead
        eyebrow="GAP VERIFICATION & CHASER"
        title={data?.checklist.case.company || "Chaser workspace"}
        description="Verify the gaps. Shape the message. Keep the final decision yours."
        action={
          <select
            aria-label="Select case"
            value={cid}
            onChange={(e) => setCid(e.target.value)}
          >
            {cases.map((c) => (
              <option value={c.id} key={c.id}>
                {c.id} · {c.company}
              </option>
            ))}
          </select>
        }
      />
      <ErrorBox message={error} />
      {message && (
        <div className="success" role="status">
          {message}
        </div>
      )}
      {!data ? (
        <Loading />
      ) : (
        <>
          <div className="guardrail-banner">
            <div className="banner-icon">
              <ShieldCheck size={23} />
            </div>
            <div>
              <strong>Received-document lock is active</strong>
              <p>
                {data.checklist.received.length} received items excluded ·{" "}
                {data.checklist.missing.length} documentation gaps · Rechecked
                at approval
              </p>
            </div>
            <Pill tone="green">Metadata presence only</Pill>
          </div>
          <div className="workspace-grid">
            <section className="panel checklist">
              <div className="panel-heading">
                <div>
                  <div className="eyebrow">01 / DETERMINISTIC CHECK</div>
                  <h2>What’s here. What’s missing.</h2>
                </div>
                <FileText size={20} className="purple-text" />
              </div>
              <p className="muted">
                Synthetic On-Prem Document Store · Revision{" "}
                {data.checklist.revision}
              </p>
              <div className="doc-group-label">
                <LockKeyhole size={13} /> RECEIVED · LOCKED FROM CHASE
              </div>
              {data.checklist.received.map((d) => (
                <div className="document received" key={d.id}>
                  <div className="document-icon">
                    <LockKeyhole size={18} />
                  </div>
                  <div>
                    <strong>{d.name}</strong>
                    <p>
                      Received {d.received_at?.slice(0, 10)} · Presence recorded
                    </p>
                  </div>
                  <Check size={17} />
                </div>
              ))}
              <div className="doc-group-label">OUTSTANDING DOCUMENTS</div>
              {data.checklist.missing.map((d) => (
                <div className="document" key={d.id}>
                  <div className="document-icon missing">
                    <FileText size={18} />
                  </div>
                  <div>
                    <strong>{d.name}</strong>
                    <p>Required for {data.checklist.case.city} onboarding</p>
                    {["analyst", "admin"].includes(user?.role || "") && (
                      <button
                        className="text-button"
                        disabled={!!busy}
                        onClick={() =>
                          perform("receive", () =>
                            post(`/cases/${cid}/documents/${d.id}/receive`),
                          )
                        }
                      >
                        Record synthetic receipt <ArrowRight size={12} />
                      </button>
                    )}
                  </div>
                  <Pill tone="rose">Missing</Pill>
                </div>
              ))}
              <div className="rule-note">
                <ShieldCheck size={18} />
                <p>
                  Presence checks only. Authenticity judgments and final risk
                  ratings stay with the responsible human teams.
                </p>
              </div>
            </section>
            <section className="panel draft-panel">
              <div className="panel-heading">
                <div>
                  <div className="eyebrow">02 / CONSOLIDATED OUTREACH</div>
                  <h2>One email. Every missing item.</h2>
                </div>
                <Pill tone={draft?.scorecard.passed ? "green" : "purple"}>
                  {draft ? label(draft.status) : "Ready to draft"}
                </Pill>
              </div>
              {!draft ? (
                <Empty title="Your next chase starts here">
                  <p>
                    Five agent stages consolidate the gaps and check the message
                    before your review.
                  </p>
                  <button
                    disabled={!!busy || !canGenerate}
                    className="primary"
                    onClick={() =>
                      perform("generate", () =>
                        post("/cases/" + cid + "/generate"),
                      )
                    }
                  >
                    <Sparkles size={16} />
                    {busy === "generate"
                      ? "Agents are working…"
                      : "Generate consolidated draft"}
                  </button>
                </Empty>
              ) : (
                <>
                  <div className="draft-meta">
                    <span>
                      TO <strong>{data.checklist.case.contact}</strong>
                    </span>
                    <Pill>
                      {draft.provider === "offline_demo"
                        ? "Offline fixture"
                        : draft.provider}
                    </Pill>
                  </div>
                  <label className="subject-label">
                    SUBJECT
                    <input
                      aria-label="Email subject"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      readOnly={!canReview || draft.status !== "REVIEW"}
                    />
                  </label>
                  <textarea
                    aria-label="Draft email body"
                    className="email-body"
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    readOnly={!canReview || draft.status !== "REVIEW"}
                  />
                  <div className="scorecard">
                    <div>
                      <ShieldCheck size={17} />
                      <strong>Critique QA scorecard</strong>
                      <Pill tone={draft.scorecard.passed ? "green" : "rose"}>
                        {draft.scorecard.tone_score}% tone
                      </Pill>
                    </div>
                    <ul>
                      {[
                        [
                          draft.scorecard.zero_false_chases,
                          "Zero received documents requested",
                        ],
                        [
                          draft.scorecard.all_missing_consolidated,
                          "All missing items in one email",
                        ],
                        [
                          draft.scorecard.no_prohibited_claims,
                          "No risk or authenticity claims",
                        ],
                        [
                          draft.scorecard.tone_score >= 95 &&
                            draft.scorecard.policy_compliant,
                          "Tone & policy compliance ≥95%",
                        ],
                      ].map(([ok, text]) => (
                        <li
                          key={String(text)}
                          className={ok ? "green-text" : "rose-text"}
                        >
                          {ok ? <Check size={13} /> : <span>×</span>}
                          {text}
                        </li>
                      ))}
                    </ul>
                    {draft.scorecard.feedback.length > 0 && (
                      <p className="rose-text">
                        {draft.scorecard.feedback.join("; ")}
                      </p>
                    )}
                    <small className="muted">
                      {draft.scorecard.iterations} iteration(s) · Max 3 rewrites
                    </small>
                  </div>
                  <div className="review-gate">
                    <div>
                      <LockKeyhole size={18} />
                      <strong>RM review gate</strong>
                    </div>
                    <p>
                      Review this exact message before approving. Sends are
                      recorded in the synthetic outbox.
                    </p>
                    <div className="actions">
                      {canReview && draft.status === "REVIEW" && (
                        <>
                          <button
                            className="secondary"
                            disabled={!!busy || !dirty}
                            onClick={() =>
                              perform("edit", () =>
                                put("/cases/" + cid + "/draft", {
                                  subject,
                                  body,
                                }),
                              )
                            }
                          >
                            Save edits & recheck QA
                          </button>
                          <button
                            className="primary"
                            disabled={
                              !!busy || dirty || !draft.scorecard.passed
                            }
                            onClick={() =>
                              perform("approve", async () => {
                                const r = await post(
                                  "/cases/" + cid + "/decision",
                                  {
                                    action: "approve_send",
                                    draft_id: draft.id,
                                  },
                                );
                                setMessage(r.message);
                              })
                            }
                          >
                            <Send size={15} />
                            Approve & Send
                          </button>
                        </>
                      )}
                      {canReview &&
                        ["REVIEW", "BLOCKED"].includes(draft.status) && (
                          <button
                            className="danger ghost"
                            disabled={!!busy}
                            onClick={() => setShowDiscard(!showDiscard)}
                            title="Discard draft"
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                    </div>
                    {showDiscard && (
                      <div className="discard-form">
                        <input
                          placeholder="Reason for discarding (required)"
                          value={reason}
                          onChange={(e) => setReason(e.target.value)}
                        />
                        <button
                          disabled={!!busy || !reason.trim()}
                          className="danger"
                          onClick={() =>
                            perform("discard", async () => {
                              await post("/cases/" + cid + "/decision", {
                                action: "discard",
                                reason,
                                draft_id: draft.id,
                              });
                              setShowDiscard(false);
                            })
                          }
                        >
                          Confirm discard
                        </button>
                      </div>
                    )}
                    {canReview && draft.status === "REVIEW" && !dirty && (
                      <button
                        className="text-button"
                        disabled={!!busy}
                        onClick={async () => {
                          try {
                            const r = await post(
                              "/cases/" + cid + "/mcp-approval-token",
                            );
                            setApproval(r.approval_token);
                          } catch (e) {
                            setError((e as Error).message);
                          }
                        }}
                      >
                        Authorize exact draft for MCP · 2-minute token
                      </button>
                    )}
                    {approval && (
                      <div className="approval-token">
                        <input
                          aria-label="MCP approval token"
                          readOnly
                          value={approval}
                        />
                        <button
                          className="icon-button"
                          title="Copy approval token"
                          onClick={() =>
                            navigator.clipboard.writeText(approval)
                          }
                        >
                          <Copy size={15} />
                        </button>
                      </div>
                    )}
                    {!canReview && (
                      <p className="muted">
                        An RM or admin must perform the review decision.
                      </p>
                    )}
                  </div>
                  <button
                    disabled={!!busy || !canGenerate}
                    className="text-button regenerate"
                    onClick={() =>
                      perform("generate", () =>
                        post("/cases/" + cid + "/generate"),
                      )
                    }
                  >
                    <Sparkles size={14} />
                    {busy === "generate"
                      ? "Agents are working…"
                      : "Generate a fresh draft"}
                  </button>
                </>
              )}
            </section>
          </div>
          {busy && (
            <div className="working">
              <span className="working-dot" />{" "}
              {busy === "generate"
                ? "Running deterministic → orchestrator → drafter → toner → critique. Please keep this page open."
                : "Recording action and checking safety gates…"}
            </div>
          )}
        </>
      )}
    </>
  );
}

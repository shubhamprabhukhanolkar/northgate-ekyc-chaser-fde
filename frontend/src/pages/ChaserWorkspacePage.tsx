import { useState, useEffect, useRef } from "react";
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
  MessageSquareText,
} from "lucide-react";
import { api, post, put, Case, Checklist, Draft, label } from "../api";
import { useAuth } from "../context/AuthContext";
import { PageHead, Pill, ErrorBox, Loading, Empty } from "../components/UI";
import WorkflowMonitor, {
  StreamingDraftPreview,
} from "../components/WorkflowMonitor";
import { useWorkflow } from "../hooks/useWorkflow";
import { useDrafting } from "../context/DraftingContext";
export default function ChaserWorkspacePage() {
  const [params, setParams] = useSearchParams();
  const [cases, setCases] = useState<Case[]>([]);
  const [cid, setCid] = useState(params.get("case") || "NG-2026-0841");
  const [data, setData] = useState<{
    checklist: Checklist;
    draft: Draft | null;
  } | null>(null);
  const [error, setError] = useState("");
  const [actionBusy, setBusy] = useState("");
  const { mode: draftMode } = useDrafting();
  const [instructions, setInstructions] = useState("");
  const [guidedRunId, setGuidedRunId] = useState("");
  const autoAttempted = useRef(new Set<string>());
  const workflow = useWorkflow(cid);
  const busy = workflow.active ? "generate" : actionBusy;
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
    setGuidedRunId("");
    setInstructions("");
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
  const terminalEvent = [...workflow.events]
    .reverse()
    .find(
      (event) => event.kind === "run_completed" || event.kind === "run_failed",
    );
  useEffect(() => {
    if (!terminalEvent) return;
    void load().catch((e) => setError(e.message));
    if (
      terminalEvent.kind === "run_failed" &&
      (draftMode === "auto" || terminalEvent.run_id === guidedRunId)
    )
      setError(
        terminalEvent.data.summary || "Generation stopped. Please retry.",
      );
  }, [terminalEvent?.id]);
  async function generateLive() {
    setError("");
    setMessage("");
    setApproval("");
    try {
      const started = await workflow.start(cid, {
        mode: draftMode,
        instructions,
      });
      if (draftMode === "guided" && started) setGuidedRunId(started.id);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    if (
      draftMode !== "auto" ||
      !data ||
      data.checklist.case.id !== cid ||
      !workflow.loaded ||
      workflow.active ||
      !canGenerate ||
      !data.checklist.missing.length ||
      autoAttempted.current.has(cid)
    )
      return;
    autoAttempted.current.add(cid);
    if (data.draft?.status === "REVIEW" && data.draft.scorecard.passed) return;
    void generateLive();
  }, [draftMode, data, workflow.loaded, workflow.active, cid, canGenerate]);
  const showRun =
    draftMode === "auto" || (!!guidedRunId && guidedRunId === workflow.run?.id);
  const guidedReady =
    !!guidedRunId &&
    terminalEvent?.kind === "run_completed" &&
    terminalEvent.run_id === guidedRunId &&
    terminalEvent.data.draft?.id === data?.draft?.id;
  const draft = draftMode === "auto" || guidedReady ? data?.draft : null;
  useEffect(() => {
    setGuidedRunId("");
    setError("");
    setApproval("");
  }, [draftMode]);
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
      <ErrorBox message={error || workflow.error} />
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
            <WorkflowMonitor
              key={cid + ":" + draftMode}
              initialView={draftMode === "guided" ? "activity" : "drafter"}
              run={showRun ? workflow.run : null}
              events={showRun ? workflow.events : []}
              reconnecting={workflow.reconnecting}
              onGenerate={generateLive}
              hasDraft={!!draft}
              generationDisabled={
                !!busy ||
                !canGenerate ||
                (draftMode === "guided" && instructions.trim().length < 5)
              }
              guidance={
                <div className="draft-instructions">
                  <label htmlFor="draft-instructions">
                    <MessageSquareText size={15} />
                    {draftMode === "guided"
                      ? "Drafting & redrafting instructions"
                      : "Redraft guidance (optional)"}
                  </label>
                  <p>
                    {draftMode === "guided"
                      ? "Watch the workflow above, then tell the AI how you want the email written. Choose Draft to begin, or update these instructions for a redraft."
                      : "Want a different version? Add guidance for your next draft, or leave this empty to use the default style."}
                  </p>
                  <textarea
                    id="draft-instructions"
                    aria-label="Drafting instructions"
                    value={instructions}
                    maxLength={3000}
                    disabled={workflow.active}
                    onChange={(e) => setInstructions(e.target.value)}
                    placeholder="For example: Keep it brief and warm, list missing items as bullet points, and offer help if more time is needed."
                  />
                  <div>
                    <small>{instructions.length}/3000</small>
                    <span>
                      {draftMode === "guided" && instructions.trim().length < 5
                        ? "Add instructions to enable Draft."
                        : !instructions.trim()
                          ? "Optional. The default drafting style will be used."
                          : "These instructions will guide your next draft."}
                    </span>
                  </div>
                </div>
              }
              drafter={
                <section className="panel draft-panel">
                  <p className="drafting-mode-note">
                    {draftMode === "auto"
                      ? "Auto-draft is on. AI prepares and checks the email; you approve every send."
                      : "Guided draft is on. Add instructions beneath the AI workflow before choosing Draft."}
                  </p>
                  <div className="panel-heading">
                    <div>
                      <div className="eyebrow">02 / CONSOLIDATED OUTREACH</div>
                      <h2>One email. Every missing item.</h2>
                    </div>
                    <Pill
                      tone={
                        workflow.active && showRun
                          ? "purple"
                          : draft?.scorecard.passed
                            ? "green"
                            : "purple"
                      }
                    >
                      {workflow.active && showRun
                        ? "Generating · QA pending"
                        : draft
                          ? label(draft.status)
                          : "Ready to draft"}
                    </Pill>
                  </div>
                  {workflow.active && showRun ? (
                    <StreamingDraftPreview events={workflow.events} active />
                  ) : !draft ? (
                    <Empty
                      title={
                        draftMode === "guided"
                          ? "Your instructions. Your starting point."
                          : "Your next chase starts here"
                      }
                    >
                      <p>
                        {draftMode === "guided"
                          ? "Open AI workflow, add your instructions below the animation, then select Draft."
                          : "AI will consolidate the gaps and check the message before your review."}
                      </p>
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
                          <Pill
                            tone={draft.scorecard.passed ? "green" : "rose"}
                          >
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
                          {draft.scorecard.iterations} iteration(s) · Max 3
                          rewrites
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
                    </>
                  )}
                </section>
              }
            />
          </div>
          {busy && (
            <div className="task-toast">
              <span className="working-dot" />{" "}
              {busy === "generate"
                ? "Live run in progress. You can switch views or navigate away; progress will reconnect."
                : "Recording action and checking safety gates…"}
            </div>
          )}
        </>
      )}
    </>
  );
}

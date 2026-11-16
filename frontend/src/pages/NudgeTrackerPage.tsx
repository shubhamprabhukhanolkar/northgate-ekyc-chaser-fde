import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Clock3, ArrowRight, MessageSquare, ShieldCheck } from "lucide-react";
import { api, post, Case, label } from "../api";
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
export default function NudgeTrackerPage() {
  const { data: cases, error, setData } = usePoll(() => api<Case[]>("/cases"));
  const [tab, setTab] = useState("Due now");
  const [actionError, setError] = useState("");
  const navigate = useNavigate();
  const { user } = useAuth();
  if (!cases) return error ? <ErrorBox message={error} /> : <Loading />;
  const waiting = cases.filter((c) => c.last_sent_at && !c.replied_at);
  const due = waiting.filter((c) => c.nudge_due);
  const replied = cases.filter((c) => c.replied_at);
  const shown =
    tab === "Due now" ? due : tab === "Awaiting reply" ? waiting : replied;
  return (
    <>
      <PageHead
        eyebrow="FOLLOW-UP, WITHOUT THE FRICTION"
        title="A timely nudge. A human touch."
        description="Three-day follow-ups are flagged automatically. Every message still needs your approval."
      />
      <div className="metrics three">
        <Metric
          label="Ready for a nudge"
          value={due.length}
          note="No reply after 3 calendar days"
          tone="amber-text"
        />
        <Metric
          label="Awaiting client reply"
          value={waiting.length}
          note="Synthetic outreach history"
        />
        <Metric
          label="Replies recorded"
          value={replied.length}
          note="Reply receipt suppresses future nudges"
          tone="green-text"
        />
      </div>
      <div className="guardrail-banner">
        <ShieldCheck size={22} />
        <div>
          <strong>Automatic scheduling. Human-approved outreach.</strong>
          <p>
            The in-process worker scans every 30 seconds and never sends a
            message.
          </p>
        </div>
      </div>
      <div className="tabs standalone">
        {["Due now", "Awaiting reply", "Replied"].map((t) => (
          <button
            className={tab === t ? "active" : ""}
            onClick={() => setTab(t)}
            key={t}
          >
            {t}
          </button>
        ))}
      </div>
      <ErrorBox message={actionError || error} />
      {shown.length ? (
        <div className="nudge-list">
          {shown.map((c) => (
            <article className="panel nudge-card" key={c.id}>
              <div className="entity-icon amber">
                <Clock3 size={24} />
              </div>
              <div className="nudge-info">
                <div className="eyebrow">
                  {c.id} · {c.city}
                </div>
                <h2>{c.company}</h2>
                <p>
                  {c.last_sent_at
                    ? "Last chase " +
                      new Date(c.last_sent_at).toLocaleDateString("en-GB")
                    : "No chase sent"}{" "}
                  · {c.missing_count} outstanding items
                </p>
                <div className="timeline">
                  <span className="timeline-step done">Chase sent</span>
                  <span className="timeline-line" />
                  <span className="timeline-step done">3-day checkpoint</span>
                  <span className="timeline-line" />
                  <span className="timeline-step">RM review</span>
                </div>
              </div>
              <div className="nudge-actions">
                <Pill tone={c.nudge_due ? "amber" : "green"}>
                  {c.nudge_due ? "Nudge due" : label(c.status)}
                </Pill>
                <button
                  className="primary"
                  onClick={() => navigate("/workspace?case=" + c.id)}
                >
                  Review {c.nudge_due ? "nudge" : "case"}
                  <ArrowRight size={15} />
                </button>
                {!c.replied_at &&
                  ["rm", "analyst", "admin"].includes(user?.role || "") && (
                    <button
                      className="text-button"
                      onClick={async () => {
                        try {
                          await post("/cases/" + c.id + "/reply");
                          setData(await api<Case[]>("/cases"));
                        } catch (e) {
                          setError((e as Error).message);
                        }
                      }}
                    >
                      <MessageSquare size={13} />
                      Record client reply
                    </button>
                  )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty title="You’re all caught up">
          <p>No cases in this follow-up view.</p>
        </Empty>
      )}
    </>
  );
}

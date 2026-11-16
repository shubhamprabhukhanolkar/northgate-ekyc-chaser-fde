import { useState, FormEvent } from "react";
import {
  Bot,
  ArrowUp,
  BookOpen,
  ShieldCheck,
  ArrowUpRight,
  LoaderCircle,
} from "lucide-react";
import { post } from "../api";
import { PageHead, Pill, ErrorBox } from "../components/UI";
type Message = {
  role: string;
  answer: string;
  citations?: { id: string; title: string; text: string }[];
  provider?: string;
};
export default function PolicyCopilotPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function ask(q: string) {
    if (!q.trim() || busy) return;
    setBusy(true);
    setError("");
    setMessages((m) => [...m, { role: "user", answer: q }]);
    setQuestion("");
    try {
      const r = await post("/policy/query", { question: q });
      setMessages((m) => [...m, { role: "assistant", ...r }]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function submit(e: FormEvent) {
    e.preventDefault();
    ask(question);
  }
  return (
    <>
      <PageHead
        eyebrow="KYC POLICY COPILOT"
        title="A clear answer. A source to trust."
        description="Grounded assistance from the synthetic Northgate KYC policy. Every answer links back to a clause."
      />
      <div className="copilot-grid">
        <section className="panel chat-panel">
          {!messages.length ? (
            <div className="chat-welcome">
              <div className="copilot-symbol">
                <Bot size={34} />
              </div>
              <Pill tone="purple">NORTHGATE POLICY ASSISTANT</Pill>
              <h2>What would you like to clarify?</h2>
              <p>
                From missing-document checks to the three-day nudge,
                <br />
                find the policy behind your next action.
              </p>
              <div className="suggestions">
                {[
                  "When should I send a follow-up nudge?",
                  "Can I request a document already received?",
                  "What documents are required in Singapore?",
                  "Who makes the final risk decision?",
                ].map((q) => (
                  <button key={q} onClick={() => ask(q)}>
                    <BookOpen size={15} />
                    {q}
                    <ArrowUpRight size={15} />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((m, i) => (
                <article className={"message " + m.role} key={i}>
                  <div className="message-avatar">
                    {m.role === "user" ? "YOU" : <Bot size={19} />}
                  </div>
                  <div>
                    <strong>
                      {m.role === "user" ? "You" : "Northgate Policy Copilot"}
                    </strong>
                    <p>{m.answer}</p>
                    {m.citations && (
                      <div className="citations">
                        {m.citations.map((c) => (
                          <details key={c.id}>
                            <summary>
                              <BookOpen size={12} />
                              {c.id} · {c.title}
                            </summary>
                            <p>{c.text}</p>
                          </details>
                        ))}
                      </div>
                    )}
                    {m.provider && (
                      <small className="muted">
                        {m.provider === "offline_demo"
                          ? "Offline policy retrieval fixture"
                          : m.provider}
                      </small>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
          {busy && (
            <div className="chat-busy">
              <LoaderCircle size={15} className="spin" />
              Reading the synthetic policy…
            </div>
          )}
          <ErrorBox message={error} />
          <form className="chat-input" onSubmit={submit}>
            <input
              aria-label="Policy question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about Northgate KYC policy…"
              maxLength={3000}
            />
            <button
              className="primary"
              aria-label="Send policy question"
              disabled={busy || question.trim().length < 3}
            >
              <ArrowUp size={19} />
            </button>
          </form>
          <div className="chat-footnote">
            <ShieldCheck size={12} />
            Synthetic policy guidance · Verify decisions with your compliance
            team
          </div>
        </section>
        <aside className="panel knowledge-panel">
          <div className="eyebrow">KNOWLEDGE SCOPE</div>
          <h2>
            Built on policy.
            <br />
            Bound by oversight.
          </h2>
          <div>
            <BookOpen size={20} />
            <h3>Northgate KYC Playbook</h3>
            <p>
              Five synthetic policy clauses covering presence checks,
              consolidated outreach, nudges, governance and jurisdictions.
            </p>
            <Pill tone="green">Clause-cited responses</Pill>
          </div>
          <div>
            <ShieldCheck size={20} />
            <h3>Your judgment stays central</h3>
            <p>
              The copilot cannot approve outreach, assess document authenticity
              or assign risk ratings.
            </p>
          </div>
          <div className="knowledge-footer">
            SYNTHETIC REFERENCE LIBRARY
            <br />
            NG-KYC-01 — NG-KYC-05
          </div>
        </aside>
      </div>
    </>
  );
}

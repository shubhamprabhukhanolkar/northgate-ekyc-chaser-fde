import { useEffect, useRef, useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowUp,
  ArrowUpRight,
  BookOpen,
  Compass,
  FileText,
  HelpCircle,
  MessageCircle,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { api } from "../api";
import { ErrorBox } from "../components/UI";

type Message = {
  id: string;
  role: "user" | "assistant";
  answer: string;
  citations?: { id: string; title: string; text: string }[];
};
const suggestions = [
  {
    question:
      "How do I use Guided draft and add drafting instructions in this portal?",
    label: "Create your first draft",
    detail: "Choose a mode, add guidance and get started.",
    Icon: MessageCircle,
  },
  {
    question: "How can I find a case, filter the queue and move between pages?",
    label: "Find your way around cases",
    detail: "Search, filter and browse the case queue.",
    Icon: FileText,
  },
  {
    question: "How do I follow the AI workflow and inspect all agent traces?",
    label: "Follow your AI team",
    detail: "Understand the workflow and Agent Trace.",
    Icon: BookOpen,
  },
  {
    question: "How do I edit, review and approve a draft in the portal?",
    label: "Review with confidence",
    detail: "Edit a message and complete your review.",
    Icon: ShieldCheck,
  },
];

export default function PortalGuidePage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reset, setReset] = useState(0);
  const activeRequest = useRef<AbortController | null>(null);
  const requestVersion = useRef(0);
  const input = useRef<HTMLInputElement>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(
    () => () => {
      requestVersion.current++;
      activeRequest.current?.abort();
    },
    [],
  );
  useEffect(() => {
    end.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "nearest",
    });
  }, [messages, busy]);

  async function ask(value: string) {
    const text = value.trim();
    if (text.length < 3 || busy) return;
    const version = ++requestVersion.current;
    const controller = new AbortController();
    activeRequest.current = controller;
    setBusy(true);
    setError("");
    setQuestion("");
    setMessages((previous) => [
      ...previous,
      { id: crypto.randomUUID(), role: "user", answer: text },
    ]);
    try {
      const response = await api<{
        answer: string;
        citations: Message["citations"];
      }>("/policy/query", {
        method: "POST",
        body: JSON.stringify({
          question: text,
          history: messages.slice(-6).map((message) => ({
            role: message.role,
            content: message.answer.slice(0, 3000),
          })),
        }),
        signal: controller.signal,
      });
      if (version === requestVersion.current)
        setMessages((previous) => [
          ...previous,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            answer: response.answer,
            citations: response.citations,
          },
        ]);
    } catch (e) {
      if (!controller.signal.aborted && version === requestVersion.current)
        setError((e as Error).message);
    } finally {
      if (version === requestVersion.current) {
        setBusy(false);
        activeRequest.current = null;
        input.current?.focus();
      }
    }
  }

  function clear() {
    requestVersion.current++;
    activeRequest.current?.abort();
    activeRequest.current = null;
    setMessages([]);
    setQuestion("");
    setError("");
    setBusy(false);
    setReset((value) => value + 1);
    input.current?.focus();
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void ask(question);
  }
  function back() {
    clear();
  }

  return (
    <>
      <section className="panel portal-chat" aria-label="Portal Guide chat">
        <div className="portal-chat-toolbar">
          <button
            type="button"
            className="portal-back"
            onClick={back}
            title="Return to the Portal Guide welcome screen"
          >
            <ArrowLeft size={16} />
            Back
          </button>
          <div className="portal-chat-identity">
            <span className="portal-mini-icon">
              <Compass size={19} />
            </span>
            <div>
              <strong>Portal Guide</strong>
              <small>
                <span className={"dot " + (busy ? "pulsing" : "")} />
                {busy ? "Finding your answer" : "Here to help"}
              </small>
            </div>
          </div>
          <button
            type="button"
            className="portal-clear"
            onClick={clear}
            disabled={!messages.length && !question && !error && !busy}
            title="Clear this conversation and start fresh"
          >
            <RotateCcw size={14} />
            Clear chat
          </button>
        </div>
        <div className="portal-chat-content">
          {!messages.length ? (
            <div className="portal-welcome" key={reset}>
              <div className="portal-guide-mark">
                <span className="portal-guide-halo" aria-hidden="true" />
                <span className="portal-guide-ring" aria-hidden="true" />
                <span
                  className="portal-guide-ring portal-guide-ring-outer"
                  aria-hidden="true"
                />
                <Compass size={36} />
                <Sparkles size={14} className="portal-sparkle" />
              </div>
              <span className="portal-welcome-label">
                YOUR NEXT STEP STARTS HERE
              </span>
              <h1 className="portal-welcome-title">
                How can I help you today?
              </h1>
              <p>
                Learn your way around the portal, one step at a time.
                <br />
                Choose a starting point, or ask in your own words.
              </p>
              <div className="portal-suggestions">
                {suggestions.map(({ question, label, detail, Icon }, index) => (
                  <button
                    type="button"
                    key={label}
                    onClick={() => void ask(question)}
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <span className="portal-suggestion-icon">
                      <Icon size={19} />
                    </span>
                    <span>
                      <strong>{label}</strong>
                      <small>{detail}</small>
                    </span>
                    <ArrowUpRight size={16} />
                  </button>
                ))}
              </div>
              <div className="portal-shortcuts">
                <span>Or jump straight to</span>
                <button type="button" onClick={() => navigate("/")}>
                  Your cases
                  <ArrowUpRight size={12} />
                </button>
                <button type="button" onClick={() => navigate("/nudges")}>
                  Follow-ups
                  <ArrowUpRight size={12} />
                </button>
              </div>
            </div>
          ) : (
            <div
              className="portal-messages"
              role="log"
              aria-live="polite"
              aria-relevant="additions"
            >
              {messages.map((message) => (
                <article
                  className={"portal-message " + message.role}
                  key={message.id}
                >
                  <span className="portal-message-avatar">
                    {message.role === "user" ? "YOU" : <Compass size={19} />}
                  </span>
                  <div className="portal-message-bubble">
                    <strong>
                      {message.role === "user" ? "You" : "Portal Guide"}
                    </strong>
                    <p>{message.answer}</p>
                    {!!message.citations?.length && (
                      <details className="portal-sources">
                        <summary>
                          <BookOpen size={12} />
                          View sources<span>{message.citations.length}</span>
                        </summary>
                        <div>
                          {message.citations.map((citation) => (
                            <div className="portal-source" key={citation.id}>
                              <strong>{citation.title}</strong>
                              <p>{citation.text}</p>
                              <small>{citation.id}</small>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                </article>
              ))}
              {busy && (
                <div className="portal-typing" role="status">
                  <span className="portal-message-avatar">
                    <Compass size={19} />
                  </span>
                  <div>
                    <span className="typing-dots" aria-hidden="true">
                      <i />
                      <i />
                      <i />
                    </span>
                    <span>Finding the right guidance…</span>
                  </div>
                </div>
              )}
              <div ref={end} />
            </div>
          )}
        </div>
        <div className="portal-composer">
          <ErrorBox message={error} />
          <form className="portal-chat-input" onSubmit={submit}>
            <HelpCircle size={18} />
            <input
              ref={input}
              aria-label="Ask Portal Guide"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="What would you like help with?"
              maxLength={3000}
            />
            {question && (
              <button
                type="button"
                className="icon-button portal-clear-input"
                aria-label="Clear question"
                onClick={() => {
                  setQuestion("");
                  input.current?.focus();
                }}
              >
                <X size={14} />
              </button>
            )}
            <button
              type="submit"
              className="primary portal-send"
              aria-label="Send question"
              disabled={busy || question.trim().length < 3}
            >
              <ArrowUp size={19} />
            </button>
          </form>
          <div className="portal-composer-note">
            <span>
              <ShieldCheck size={12} />
              Guidance for your next step. You stay in control.
            </span>
            <span>Enter to send</span>
          </div>
        </div>
      </section>
    </>
  );
}

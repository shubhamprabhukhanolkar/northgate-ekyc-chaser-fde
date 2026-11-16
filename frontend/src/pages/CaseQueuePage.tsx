import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  ArrowRight,
  RefreshCw,
  Building2,
  LockKeyhole,
  Clock3,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { api, Case, label } from "../api";
import {
  PageHead,
  Metric,
  Pill,
  Loading,
  ErrorBox,
  Empty,
  usePoll,
} from "../components/UI";
export default function CaseQueuePage() {
  const navigate = useNavigate();
  const [city, setCity] = useState("All jurisdictions");
  const [search, setSearch] = useState("");
  const [due, setDue] = useState(false);
  const [page, setPage] = useState(1);
  const results = useRef<HTMLElement>(null);
  useEffect(() => setPage(1), [city, search, due]);
  const { data: cases, error, setData } = usePoll(() => api<Case[]>("/cases"));
  const { data: finops } = usePoll(() => api("/finops"));
  if (!cases) return error ? <ErrorBox message={error} /> : <Loading />;
  const filtered = cases.filter(
    (c) =>
      (city === "All jurisdictions" || c.city === city) &&
      (!due || c.nudge_due) &&
      `${c.company} ${c.id}`.toLowerCase().includes(search.toLowerCase()),
  );
  const pageCount = Math.max(1, Math.ceil(filtered.length / 6));
  const currentPage = Math.min(page, pageCount);
  const first = (currentPage - 1) * 6;
  const visibleCases = filtered.slice(first, first + 6);
  function changePage(next: number) {
    setPage(next);
    results.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "start",
    });
  }
  return (
    <>
      <PageHead
        eyebrow="DAILY ACTION HUB"
        title="Your cases. Moving forward."
        description="One clear view of outstanding documents, client follow-ups and reviews."
        action={
          <button
            className="secondary"
            onClick={() => api<Case[]>("/cases").then(setData)}
          >
            <RefreshCw size={14} />
            Refresh queue
          </button>
        }
      />
      <div className="metrics">
        <Metric
          label="Active workstream"
          value={cases.length}
          note="Synthetic corporate onboarding cases"
        />
        <Metric
          label="Chase round target"
          value={
            <>
              3.0<span>days</span>
            </>
          }
          note="5.5-day historical baseline"
          tone="green-text"
        />
        <Metric
          label="RM discard rate"
          value={((finops?.discard_rate || 0) * 100).toFixed(1) + "%"}
          note="Measured across reviewed drafts"
        />
        <Metric
          label="Potential capacity"
          value={
            <>
              3,000<span>days / mo</span>
            </>
          }
          note="Projected · 400 cases × 3 rounds × 2.5d"
          tone="purple-text"
        />
      </div>
      <div className="filterbar">
        <div className="tabs">
          {["All jurisdictions", "London", "Singapore", "New York"].map((c) => (
            <button
              className={city === c ? "active" : ""}
              onClick={() => setCity(c)}
              key={c}
            >
              {c}
              {c === "All jurisdictions" && <small>{cases.length}</small>}
            </button>
          ))}
        </div>
        <button
          className={"nudge-filter " + (due ? "active" : "")}
          onClick={() => setDue(!due)}
        >
          <Clock3 size={14} />
          {cases.filter((c) => c.nudge_due).length} nudges due
        </button>
        <label className="search">
          <Search size={16} />
          <input
            placeholder="Find a company or case"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
      </div>
      <ErrorBox message={error} />
      <section
        className="queue-results"
        ref={results}
        aria-label="Onboarding case results"
      >
        <div className="section-caption">
          <span>
            ONBOARDING CASES <small>{filtered.length}</small>
          </span>
          <span>
            Showing {filtered.length ? first + 1 : 0}–
            {Math.min(first + 6, filtered.length)} of {filtered.length}
          </span>
        </div>
        <div className="case-list">
          {visibleCases.map((c) => (
            <article className="case-card" key={c.id}>
              <div className="case-top">
                <div className={"entity-icon " + (c.nudge_due ? "amber" : "")}>
                  <Building2 size={23} />
                </div>
                <div className="case-heading">
                  <div>
                    <h2>{c.company}</h2>
                    <span className="mono">{c.id}</span>
                  </div>
                  <p>
                    {c.city} desk <span>·</span> Corporate onboarding{" "}
                    <span>·</span> Target {c.target_date}
                  </p>
                </div>
                <Pill
                  tone={
                    c.nudge_due
                      ? "amber"
                      : c.status === "RM_REVIEW"
                        ? "purple"
                        : "muted"
                  }
                >
                  {c.nudge_due ? (
                    <>
                      <Clock3 size={12} />
                      3-day nudge due
                    </>
                  ) : (
                    label(c.status)
                  )}
                </Pill>
              </div>
              <div className="case-docs">
                <div>
                  <span className="doc-indicator missing" />
                  <div>
                    <strong>{c.missing_count} outstanding documents</strong>
                    <p>Consolidated into a single chase email</p>
                  </div>
                  <Pill tone="rose">Missing</Pill>
                </div>
                <div>
                  <LockKeyhole size={16} className="green-text" />
                  <div>
                    <strong>{c.received_count} received & locked</strong>
                    <p>Excluded from every new chase</p>
                  </div>
                  <Pill tone="green">On-prem store</Pill>
                </div>
              </div>
              <div className="case-bottom">
                <span>
                  <span className="avatar mini">MS</span>Relationship Management{" "}
                  <span className="separator">·</span> {c.jurisdiction}{" "}
                  jurisdiction
                </span>
                <button
                  className="primary"
                  onClick={() => navigate("/workspace?case=" + c.id)}
                >
                  {c.nudge_due ? "Review nudge" : "Review & chase"}
                  <ArrowRight size={16} />
                </button>
              </div>
            </article>
          ))}
          {!filtered.length && (
            <Empty title="No cases match your filters">
              <p>Try another jurisdiction or company name.</p>
            </Empty>
          )}
        </div>
        {filtered.length > 0 && (
          <div className="queue-pagination">
            <span className="pagination-summary" aria-live="polite">
              Page {currentPage} of {pageCount} · 6 cases per page
            </span>
            <div
              className="pagination-controls"
              role="navigation"
              aria-label="Case queue pages"
            >
              <button
                type="button"
                disabled={currentPage === 1}
                onClick={() => changePage(currentPage - 1)}
              >
                <ChevronLeft size={14} />
                Previous
              </button>
              {Array.from({ length: pageCount }, (_, i) => i + 1).map(
                (number) => (
                  <button
                    key={number}
                    type="button"
                    className={number === currentPage ? "current-page" : ""}
                    aria-label={`Page ${number}`}
                    aria-current={number === currentPage ? "page" : undefined}
                    onClick={() => changePage(number)}
                  >
                    {number}
                  </button>
                ),
              )}
              <button
                type="button"
                disabled={currentPage === pageCount}
                onClick={() => changePage(currentPage + 1)}
              >
                Next
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </section>
    </>
  );
}

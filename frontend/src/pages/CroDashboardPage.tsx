import { useState } from "react";
import { Activity, AlertTriangle, BookOpenCheck, Download, Eye, FileCheck2, Info, LockKeyhole, RefreshCw, ShieldCheck } from "lucide-react";
import { api, label } from "../api";
import { ErrorBox, Loading, Metric, PageHead, Pill, usePoll } from "../components/UI";
import type { RiskReport } from "../risk/types";

const pct = (value: number | null) => value === null ? "—" : `${(value * 100).toFixed(1)}%`;
const issueLabels: Record<string, string> = { zero_false_chases: "Received-document exclusion", all_missing_consolidated: "Missing-document completeness", no_prohibited_claims: "Risk / authenticity wording", valid_email: "Email structure", tone_policy: "Tone / policy mismatch" };
const time = (value: string | null) => value ? new Date(value).toLocaleString() : "No record";
const tone = (status: string) => status === "implemented" ? "green" : status === "not evidenced" ? "rose" : "amber";

function DiscardTrend({ daily, threshold }: { daily: RiskReport["daily"]; threshold: number }) {
  const y = (rate: number) => 118 - rate * 90;
  return <svg className="cro-trend" viewBox="0 0 600 150" role="img" aria-label="Recorded daily discard rates. Missing days are not treated as zero; points show only days with review actions.">
    {[0,.5,1].map(value => <g key={value}><line x1="35" x2="555" y1={y(value)} y2={y(value)} stroke="var(--border)" strokeDasharray="3 5" /><text x="0" y={y(value)+3} fill="var(--muted)" fontSize="9">{value*100}%</text></g>)}
    <line x1="35" x2="555" y1={y(threshold/100)} y2={y(threshold/100)} stroke="var(--amber)" strokeDasharray="4 5" />
    {daily.map((day,index) => day.discard_rate === null ? null : <circle key={day.date} cx={35+index/Math.max(1,daily.length-1)*520} cy={y(day.discard_rate)} r="4" fill="var(--primary)"><title>{day.date}: {pct(day.discard_rate)} · {day.approved+day.discarded} review actions</title></circle>)}
    {!daily.some(day => day.discard_rate !== null) && <text x="295" y="72" textAnchor="middle" fill="var(--muted)" fontSize="11">No recorded review actions in this window</text>}
    <text x="35" y="140" fill="var(--muted)" fontSize="9">{daily[0]?.date}</text><text x="555" y="140" textAnchor="end" fill="var(--muted)" fontSize="9">{daily.at(-1)?.date} · UTC</text>
  </svg>;
}

export default function CroDashboardPage() {
  const [days,setDays] = useState(30), [threshold,setThreshold] = useState(10), [auditPage,setAuditPage] = useState(1), [exceptionPage,setExceptionPage] = useState(1);
  const [refreshError,setRefreshError] = useState("");
  const {data,error,setData} = usePoll(() => api<RiskReport>(`/cro/summary?days=${days}`),[days],30000);
  const report = data?.period.days === days ? data : null;
  const m = report?.metrics;
  const above = m?.discard_rate != null && m.discard_rate * 100 > threshold;
  const currentAuditPage = Math.min(auditPage,Math.max(1,Math.ceil((report?.audit.length ?? 0)/5)));
  const currentExceptionPage = Math.min(exceptionPage,Math.max(1,Math.ceil((report?.exceptions.length ?? 0)/5)));
  function exportReport() {
    if (!report) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify({report,local_review_threshold_percent:threshold,note:"Operational evidence, not regulatory assurance. Threshold changes do not affect operations."},null,2)],{type:"application/json"}));
    const anchor=document.createElement("a"); anchor.href=url; anchor.download="northgate-cro-governance-report.json"; anchor.click(); URL.revokeObjectURL(url);
  }
  return <div className="cro-dashboard">
    <PageHead eyebrow="CRO RISK & GOVERNANCE WORKSPACE" title="See the controls. Follow the evidence."
      description="Document-chase safeguards, human accountability and drift signals—grounded in stored operational records."
      action={<button className="secondary" disabled={!report} onClick={exportReport}><Download size={14} />Export governance report</button>} />
    <div className="cfo-toolbar"><div className="tabs" role="group" aria-label="Risk reporting period">{[[7,"7 days"],[30,"30 days"],[90,"90 days"],[0,"All history"]].map(([value,title]) => <button key={value} className={days===value?"active":""} aria-pressed={days===value} onClick={() => {setDays(Number(value));setAuditPage(1);setExceptionPage(1);}}>{title}</button>)}</div><div className="cfo-readonly"><ShieldCheck size={14} />Read-only oversight · no agent actions</div></div>
    <ErrorBox message={error || refreshError} />
    {!report || !m ? !error && <Loading /> : <>
      <div className="cfo-provenance"><Info size={17} /><span><strong>Evidence, with its limits visible.</strong> These are synthetic workflow controls—not client AML/credit ratings or a compliance certification. Unavailable evidence is shown explicitly.</span><button className="icon-button" aria-label="Refresh CRO report" onClick={() => {setRefreshError("");void api<RiskReport>(`/cro/summary?days=${days}`).then(setData).catch(() => setRefreshError("Refresh failed. The last loaded report remains visible."));}}><RefreshCw size={15} /></button></div>
      <div className="metrics cfo-metrics cro-kpis">
        <Metric label="Stored false-chase check failures" value={pct(m.outbox_check_failure_rate)} note={`${m.outbox_check_failures} / ${m.outbox_check_assessed} assessed outbox drafts · ${m.missing_outbox_check_evidence} evidence gaps`} tone={m.outbox_check_failures ? "amber-text":"green-text"} />
        <Metric label="Linked human sign-off evidence" value={pct(m.signoff_coverage)} note={`${m.human_signed} / ${m.outbox_records} synthetic outbox records matched to RM/admin approval`} />
        <Metric label="RM/admin discard rate" value={pct(m.discard_rate)} note={`${m.discarded} discards / ${m.review_actions} review actions · sample size matters`} tone={above?"amber-text":"purple-text"} />
        <Metric label="Final draft QA pass rate" value={pct(m.assessed_drafts ? m.qa_passed/m.assessed_drafts : null)} note={`${m.qa_passed} / ${m.assessed_drafts} assessed final scorecards · ${m.drafts_created-m.assessed_drafts} unavailable`} />
      </div>
      <div className="cfo-observation-strip"><span><strong>{m.average_tone_score===null?"—":m.average_tone_score.toFixed(1)}</strong> average stored tone score</span><span><strong>{m.initial_intercepted_runs}</strong> initial drafts intercepted in streamed runs</span><span><strong>{m.rewrite_events}</strong> streamed rewrite events</span><span><strong>{m.case_inventory}</strong> cases in current inventory</span><span><strong>{m.documents.RECEIVED ?? 0}</strong> received / locked documents</span></div>

      <section className="panel cro-gates"><div className="panel-heading"><div><div className="eyebrow">ENTERPRISE CONTROL POSTURE</div><h2><LockKeyhole size={17} />Eight governance gates. Clear evidence.</h2><p>Implementation descriptions and evidence gaps. These statuses are not production certifications.</p></div><Pill tone="purple">Control coverage</Pill></div>
        <div className="cro-gate-grid">{report.gates.map((gate,index) => <article className="cro-gate" key={gate.name}><div><small>{String(index+1).padStart(2,"0")}</small><Pill tone={tone(gate.status)}>{label(gate.status)}</Pill></div><h3>{gate.name}</h3><p>{gate.detail}</p></article>)}</div>
      </section>

      <div className="two-columns cfo-columns"><section className="panel"><div className="panel-heading"><div><div className="eyebrow">CRITIQUE QA INTERCEPTS</div><h2><FileCheck2 size={17} />What was caught before review?</h2><p>Failed checks across {m.streamed_qa_evaluations} persisted streaming QA evaluations. Categories can overlap.</p></div></div>
        <div className="cro-intercept-hero"><strong>{m.initial_intercepted_runs}</strong><div><b>runs with a failed first QA attempt</b><p>{m.qa_failed} final draft scorecards failed · {m.qa_passed} passed</p></div></div>
        {Object.entries(issueLabels).map(([key,title]) => <div className="cro-intercept" key={key}><div><span>{title}</span><strong>{report.intercepts[key] ?? 0}</strong></div><div className="cro-bar"><span style={{width:`${(report.intercepts[key] ?? 0)/Math.max(1,...Object.values(report.intercepts))*100}%`}} /></div></div>)}
        <p className="cfo-footnote">Older/nonstreaming runs may have no intermediate QA events. These are intercepted checks, not confirmed client incidents. Outbox checks use linked stored scorecards, not independent historic replays.</p>
      </section><section className="panel"><div className="panel-heading"><div><div className="eyebrow">ADOPTION & DRIFT REVIEW</div><h2><Activity size={17} />Watch the people closest to the work.</h2><p>Discard actions, not an inferred model-risk score.</p></div><Pill tone={m.discard_rate===null?"purple":above?"amber":"green"}>{m.discard_rate===null?"No review sample":above?"Review threshold exceeded":"Within local threshold"}</Pill></div>
        <div className="cro-threshold"><label htmlFor="cro-threshold">Local review threshold <input id="cro-threshold" type="number" min="1" max="100" value={threshold} onChange={event => {const value=event.target.valueAsNumber;if(Number.isFinite(value))setThreshold(Math.max(1,Math.min(100,value)));}} />%</label><span>Display only · no alerts or service changes</span></div>
        <DiscardTrend daily={report.daily} threshold={threshold} />
        <div className="cfo-mini-values"><div><small>Current discard rate</small><strong data-testid="cro-discard-rate">{pct(m.discard_rate)}</strong></div><div><small>Prior comparable window</small><strong>{pct(m.previous_discard_rate)}</strong></div><div><small>Discard reason coverage</small><strong>{pct(m.discarded?m.discard_reasons_recorded/m.discarded:null)}</strong></div></div>
        <p className="cfo-footnote">Current sample: {m.review_actions} review actions; prior sample: {m.previous_review_actions}. {m.edited} edit/recheck actions recorded. Missing days are not zero-discard days. All-history has no prior-period comparison.</p>
      </section></div>

      <section className="panel"><div className="panel-heading"><div><div className="eyebrow">CURRENT EXCEPTION QUEUE</div><h2><Eye size={17} />Where does human attention belong?</h2><p>{report.exception_count} cases with stale checklists, blocked/unavailable QA or a follow-up due. These are workflow flags, not client risk ratings.</p></div><Pill tone={report.exception_count?"amber":"green"}>{report.exception_count} cases flagged</Pill></div>
        <div className="cro-regions">{Object.entries(report.regions).map(([region,value]) => <div key={region}><strong>{region}</strong><span>{value.cases} current cases</span><b>{value.exceptions} flagged</b></div>)}</div>
        <div className="cfo-table-scroll"><table><thead><tr><th>Case</th><th>Jurisdiction</th><th>Recorded flags</th><th>Human next step</th></tr></thead><tbody>{report.exceptions.length?report.exceptions.slice((currentExceptionPage-1)*5,currentExceptionPage*5).map(row => <tr key={row.case_id}><td>{row.case_id}</td><td>{row.jurisdiction}</td><td>{row.issues.join(" · ")}</td><td>Operator reviews in Gap Workspace / 3-Day Nudges</td></tr>):<tr><td colSpan={4}>No current workflow exceptions found. This does not certify absence of client risk.</td></tr>}</tbody></table></div>
        {report.exceptions.length>5 && <div className="cfo-pagination"><button className="secondary" disabled={currentExceptionPage===1} onClick={() => setExceptionPage(currentExceptionPage-1)}>Previous exceptions</button><span>{currentExceptionPage} / {Math.ceil(report.exceptions.length/5)}</span><button className="secondary" disabled={currentExceptionPage*5>=report.exceptions.length} onClick={() => setExceptionPage(currentExceptionPage+1)}>Next exceptions</button></div>}
        <p className="cfo-footnote">Up to 50 current exceptions are returned. This oversight screen cannot redraft, approve, record receipts or contact clients.</p>
      </section>

      <div className="two-columns cfo-columns"><section className="panel"><div className="panel-heading"><div><div className="eyebrow">MODEL & PROMPT CHANGE CONTROL</div><h2><BookOpenCheck size={17} />Trace the last validation evidence.</h2><p>Admin changes require the exact candidate to pass the five-case regression.</p></div></div>
        <div className="cro-evidence-list"><div><span>Latest stored test</span><strong>{time(report.change_control.latest_test_at)}</strong></div><div><span>Recorded test result</span><Pill tone={report.change_control.latest_test_passed===null?"purple":report.change_control.latest_test_passed?"green":"amber"}>{report.change_control.latest_test_passed===null?"No test evidence":report.change_control.latest_test_passed?"Passed":"Failed"}</Pill></div><div><span>Cases in that test</span><strong>{report.change_control.latest_test_cases}</strong></div>{report.change_control.prompt_versions.map(row => <div key={row.agent}><span>{row.agent==="critique"?"Critique QA":label(row.agent)} prompt</span><strong>Version {row.version}</strong></div>)}</div>
        <p className="cfo-footnote">The latest test is not a publication attestation. No formal MRM classification or exemption is stored; information preparation must not be confused with automated risk decisioning.</p>
      </section><section className="panel"><div className="panel-heading"><div><div className="eyebrow">PROVIDER & AUDIT RESILIENCE</div><h2>Keep the gaps in view.</h2><p>Current audit inventory and recorded provider outcomes.</p></div></div>
        <div className="cro-evidence-list"><div><span>All stored audit records</span><strong>{report.audit_coverage.total}</strong></div><div><span>Records with ≥7-year retention date</span><strong>{report.audit_coverage.retention_marked ?? 0}</strong></div><div><span>Append-only triggers present</span><strong>{report.audit_coverage.append_only_triggers} / 2</strong></div><div><span>Durable seven-year storage</span><Pill tone="amber">Not verified</Pill></div><div><span>Cryptographic hash chaining</span><Pill tone="amber">Not implemented</Pill></div></div>
        <div className="cro-provider-grid">{["gemini","groq"].map(provider => {const rows=report.providers.filter(row=>row.provider===provider);return <div key={provider}><strong>{label(provider)}</strong><span>{rows.reduce((sum,row)=>sum+row.calls,0)} attempts · {rows.filter(row=>row.status==="error").reduce((sum,row)=>sum+row.calls,0)} errors</span><small>{rows.filter(row=>row.status==="success").reduce((sum,row)=>sum+(row.failovers ?? 0),0)} successful failovers</small></div>;})}</div>
      </section></div>

      <section className="panel"><div className="panel-heading"><div><div className="eyebrow">RECENT GOVERNANCE EVENTS</div><h2>A record of review and control activity.</h2><p>Latest 50 matching events in the window · five per page · no client wording or contact details.</p></div></div>
        <div className="cfo-table-scroll"><table><thead><tr><th>Event / time</th><th>Case / jurisdiction</th><th>Action</th><th>Actor role</th><th>Linked tone score</th><th>Discard reason</th></tr></thead><tbody>{report.audit.length?report.audit.slice((currentAuditPage-1)*5,currentAuditPage*5).map(row => <tr key={row.event_id}><td>#{row.event_id}<small className="cro-audit-time">{time(row.created_at)}</small></td><td>{row.case_id ?? "System-wide"}<small className="cro-audit-time">{row.jurisdiction ?? "—"}</small></td><td>{label(row.action)}</td><td>{label(row.actor_role)}</td><td>{row.tone_score===null?"Not linked":`${row.tone_score}%`}</td><td>{row.reason_recorded===null?"—":row.reason_recorded?"Recorded":"Missing"}</td></tr>):<tr><td colSpan={6}>No matching governance events stored in this window.</td></tr>}</tbody></table></div>
        {report.audit.length>5 && <div className="cfo-pagination"><button className="secondary" disabled={currentAuditPage===1} onClick={() => setAuditPage(currentAuditPage-1)}>Previous events</button><span>Page {currentAuditPage} of {Math.ceil(report.audit.length/5)}</span><button className="secondary" disabled={currentAuditPage*5>=report.audit.length} onClick={() => setAuditPage(currentAuditPage+1)}>Next events</button></div>}
        <p className="cfo-footnote">Scores are linked to a stored draft where available; they do not prove the content of an historical edit. Unresolved actor roles and missing links remain visible rather than being fabricated.</p>
      </section>

      <section className="cro-escalation"><AlertTriangle size={23} /><div><strong>When a control needs attention</strong><p>Review the supporting evidence and sample size, ask the RM/admin to inspect the case or prompt change, and escalate provider, policy or drift concerns to the responsible owner. Operators can use existing manual processes while an issue is investigated. This dashboard has no kill switch and changes no running services.</p></div></section>
      <details className="panel cfo-methodology"><summary>Risk methodology, evidence limits & reporting definitions</summary><ul>{report.limitations.map(text=><li key={text}>{text}</li>)}</ul></details>
      <div className="cfo-report-stamp"><ShieldCheck size={13} />CRO read-only oversight · Generated {time(report.period.end)} · UTC report boundaries</div>
    </>}
  </div>;
}

import { useId, useState } from "react";
import { ArrowDownRight, ArrowUpRight, BarChart3, Check, CircleDollarSign, Clock3, FlaskConical,
  Gauge, GitBranch, LockKeyhole, RotateCcw, ShieldCheck, ShieldOff, Sparkles, TrendingUp } from "lucide-react";
import { Metric, PageHead, Pill } from "../components/UI";
import { demoAgentUsage, demoAudit, demoGates, demoIntercepts, executiveScenario } from "../demo/executiveDemo";

const gbp = (value: number) => new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 0 }).format(value);
const number = (value: number) => Math.round(value).toLocaleString("en-GB");

function ScenarioChart({ net }: { net: number }) {
  const gradient = useId().replaceAll(":", "");
  const max = Math.max(180000, Math.abs(net * 12));
  const y = (value: number) => 114 - Math.max(0, value) / max * 90;
  const points = Array.from({ length: 13 }, (_, month) => `${36 + month * 30},${y(net * month)}`).join(" ");
  return <svg className="exec-payback-chart" viewBox="0 0 440 144" role="img" aria-label="Scenario cumulative net benefit over 12 months compared with the 120,000 pound build investment">
    <defs><linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1"><stop stopColor="var(--green)" stopOpacity=".22" /><stop offset="1" stopColor="var(--green)" stopOpacity="0" /></linearGradient></defs>
    {[0, 60000, 120000].map(value => <g key={value}><line x1="36" x2="396" y1={y(value)} y2={y(value)} stroke="var(--border)" strokeDasharray={value ? "3 5" : undefined} /><text x="0" y={y(value) + 3} fill="var(--muted)" fontSize="8">{value / 1000}k</text></g>)}
    <polygon points={`36,114 ${points} 396,114`} fill={`url(#${gradient})`} />
    <polyline points={points} fill="none" stroke="var(--green)" strokeWidth="2.5" strokeLinejoin="round" />
    <text x="396" y={y(120000) - 6} textAnchor="end" fill="var(--muted)" fontSize="8">£120k build investment</text>
    {[0, 3, 6, 9, 12].map(month => <text key={month} x={36 + month * 30} y="135" fill="var(--muted)" textAnchor="middle" fontSize="8">{month === 0 ? "Start" : `M${month}`}</text>)}
  </svg>;
}

function RoiSimulator() {
  const [volume, setVolume] = useState(400);
  const [days, setDays] = useState(2.5);
  const [hours, setHours] = useState(5);
  const s = executiveScenario(volume, days, hours);
  function reset() { setVolume(400); setDays(2.5); setHours(5); }
  return <section className="panel exec-simulator" aria-labelledby="roi-title">
    <div className="panel-heading"><div><div className="eyebrow">EXPLORE THE BUSINESS CASE</div><h2 id="roi-title"><Sparkles size={17} />What if the opportunity grows?</h2><p>Adjust the assumptions. See the economics change.</p></div><button className="secondary exec-reset" onClick={reset}><RotateCcw size={13} />Reset</button></div>
    <div className="exec-simulator-grid"><div className="exec-sliders">
      <label htmlFor="exec-volume"><span>Monthly corporate volume<strong>{number(volume)}<small> / mo</small></strong></span><input id="exec-volume" type="range" min="100" max="1000" step="25" value={volume} onChange={e => setVolume(Number(e.target.value))} /><span className="exec-range"><span>100 clients</span><span>1,000 clients</span></span></label>
      <label htmlFor="exec-days"><span>Days saved per chase round<strong>{days.toFixed(1)}<small> days</small></strong></span><input id="exec-days" type="range" min="0.5" max="4" step="0.1" value={days} onChange={e => setDays(Number(e.target.value))} /><span className="exec-range"><span>0.5 days</span><span>4.0 days</span></span></label>
      <label htmlFor="exec-hours"><span>Hours freed per file<strong>{hours.toFixed(1)}<small> hrs @ £45/hr</small></strong></span><input id="exec-hours" type="range" min="0.5" max="8" step="0.5" value={hours} onChange={e => setHours(Number(e.target.value))} /><span className="exec-range"><span>0.5 hours</span><span>8 hours</span></span></label>
    </div><div className="exec-scenario" aria-live="polite" aria-atomic="true">
      <div className="exec-scenario-values"><div><small>Annual hours realized</small><strong data-testid="annual-hours">{number(s.annualHours)}<span> hrs</span></strong></div><div><small>Net monthly saving</small><strong className={s.netMonthly > 0 ? "green-text" : "amber-text"} data-testid="net-saving">{gbp(s.netMonthly)}</strong></div><div><small>Build payback</small><strong data-testid="payback">{s.payback === null ? "No payback" : `${s.payback.toFixed(1)} mo`}</strong></div></div>
      <ScenarioChart net={s.netMonthly} />
      <div className="exec-scenario-caption"><span><i className="exec-dot green" />Cumulative net benefit</span><strong>{number(s.caseDays)} case-days / mo</strong></div>
      {s.netMonthly <= 0 && <p className="exec-negative" role="status">This scenario does not cover the £4,000 monthly run cost. Increase realized capacity to reach payback.</p>}
    </div></div>
    <details className="exec-assumptions"><summary>Model assumptions & calculation notes</summary><p>Scenario benefit realization is 18.75% of the gross hours opportunity. At 400 files × 5 hours × 12 months this gives 4,500 realized hours/year, valued at £45/hour. Gross monthly value is £16,875 (rounded to £17,000 in the board case); less £4,000 run cost gives £12,875 net, approximately £13,000. Payback = £120,000 ÷ net monthly saving. Case-days = volume × 3 rounds × days saved. Days saved represents time-to-revenue opportunity and is not counted again as cash savings.</p><p>The top cards show the fixed, rounded board case. Its 0.3× Year-1 net ROI comes from (£13,000 × 12 − £120,000) ÷ £120,000. The 1.6× annualized run-rate figure is a separate illustrative target, not a result of this simulator; the base-case annual net benefit/build ratio is 1.3×. All values are hypothetical.</p></details>
  </section>;
}

function CfoView() {
  return <>
    <div className="metrics exec-kpis">
      <Metric label="Net monthly savings" value={<>£13,000<span>/ mo</span></>} note="£17,000 gross time value − £4,000 run cost" tone="green-text" />
      <Metric label="Build cost & payback" value={<>9.3<span>months</span></>} note="£120k build · 0.3× Year-1 ROI · 1.6× run-rate target" />
      <Metric label="Time-to-revenue opportunity" value={<>3,000<span>case-days / mo</span></>} note="400 clients × 3 rounds × 2.5 days saved" tone="purple-text" />
      <Metric label="AI unit cost per case" value={<>£0.018<span>/ case</span></>} note="vs £225 manual effort · 5 hrs × £45/hr" />
    </div>
    <RoiSimulator />
    <div className="two-columns exec-two-panels">
      <section className="panel exec-cycle"><div className="panel-heading"><div><div className="eyebrow">CYCLE-TIME COMPRESSION</div><h2><Clock3 size={17} />Fewer days. Earlier opportunity.</h2></div><Pill tone="green">Pilot projection</Pill></div>
        <div className="exec-chart-key"><span><i className="exec-dot baseline" />Baseline</span><span><i className="exec-dot green" />First slice</span></div>
        {[{ label: "Median onboarding", before: 62, after: 54 }, { label: "Time spent chasing", before: 17, after: 9 }].map(row => <div className="exec-cycle-row" key={row.label}><div><strong>{row.label}</strong><span>{row.before}d → <b className="green-text">{row.after}d</b></span></div><div className="exec-track baseline"><span style={{ width: `${row.before / 62 * 100}%` }} /></div><div className="exec-track green"><span style={{ width: `${row.after / 62 * 100}%` }} /></div></div>)}
        <div className="exec-cycle-bottom"><div><small>Per chase round</small><strong>5.5d <ArrowDownRight size={17} /> <b>3.0d</b></strong></div><div><small>Client abandonment</small><strong>7.0% <ArrowDownRight size={17} /> <b>&lt;3.5%</b></strong></div></div>
        <p className="exec-footnote">54-day median assumes an eight-day reduction in chasing only. Abandonment improvement is an illustrative target, not a measured outcome.</p>
      </section>
      <section className="panel exec-provider"><div className="panel-heading"><div><div className="eyebrow">AI FINOPS & RESILIENCE</div><h2><GitBranch size={17} />Two providers. One steady workflow.</h2></div></div>
        <div className="exec-provider-values"><div><small><i className="exec-dot purple" />Gemini Flash Lite</small><strong>96.8<span>%</span></strong><p>Primary route</p></div><div><small><i className="exec-dot green" />Groq</small><strong>3.2<span>%</span></strong><p>Automatic failover</p></div></div>
        <div className="exec-distribution" role="img" aria-label="Dummy call distribution: 96.8 percent Gemini primary and 3.2 percent Groq failover"><span style={{ width: "96.8%" }} /><span style={{ width: "3.2%" }} /></div>
        <div className="exec-token-heading"><span>Agent token consumption</span><span>970k total · demo window</span></div>
        <div className="exec-agent-ledger">{demoAgentUsage.map(agent => <div key={agent.name}><strong>{agent.name}</strong><div className="exec-track"><span style={{ width: `${agent.share * 2.5}%` }} /></div><span>{number(agent.tokens / 1000)}k</span><small>£{agent.cost.toFixed(3)}/case</small></div>)}</div>
        <div className="exec-avoidance"><ShieldCheck size={18} /><div><strong>£1,440 screening cost avoided / mo</strong><p>180 duplicate checks × £8 assumed fee. Screen complete packs once.</p></div></div>
      </section>
    </div>
  </>;
}

function CroView() {
  const [manual, setManual] = useState(false);
  return <>
    <div className="metrics exec-kpis">
      <Metric label="False-chase incident rate" value="0.0%" note="0 / 412 sample cases · pre-check lock" tone="green-text" />
      <Metric label="RM draft-discard rate" value="4.2%" note="Within baseline · alert above 10.0%" tone="green-text" />
      <Metric label="Human sign-off coverage" value="100%" note="0 autonomous emails · 0 AI risk ratings" />
      <Metric label="Model risk classification" value={<>Tier 0<span>information prep</span></>} note="Illustrative classification · not an MRM exemption" tone="purple-text" />
    </div>
    <section className={`exec-fallback ${manual ? "is-manual" : ""}`} aria-label="Simulated emergency AI kill-switch">
      <span className="exec-fallback-icon">{manual ? <ShieldOff size={24} /> : <ShieldCheck size={24} />}</span><div><div className="eyebrow">EMERGENCY CONTROL · DEMONSTRATION ONLY</div><h2>{manual ? "Manual fallback mode" : "Human accountability. At every handoff."}</h2><p>{manual ? "AI assistance is paused in this dashboard scenario. RMs prepare drafts manually and retain all review gates." : "Simulate a gateway failure or drift alert to preview manual RM drafting. No actual service or agent is switched off."}</p></div>
      <button type="button" className="exec-kill-switch" role="switch" aria-checked={manual} aria-label="Simulate emergency AI kill-switch" onClick={() => setManual(value => !value)}><span className="exec-switch-track"><span /></span><span>{manual ? "Resume demo AI mode" : "Simulate manual fallback"}</span></button>
    </section>
    <section className="panel exec-gates"><div className="panel-heading"><div><div className="eyebrow">CONTROL POSTURE</div><h2><LockKeyhole size={17} />Eight enterprise production gates</h2><p>Illustrative governance readiness. Visible ownership, before scale.</p></div><Pill tone="purple">Demo scorecard</Pill></div>
      <div className="exec-gate-grid">{demoGates.map((gate,index) => <article className="exec-gate" key={gate.title}><div className="exec-gate-top"><span className="exec-gate-number">{String(index+1).padStart(2,"0")}</span><Pill tone={gate.active ? "green" : "amber"}><span className="dot" />{gate.active ? "Active" : "Monitored"}</Pill></div><h3>{gate.title}</h3><p>{gate.detail}</p></article>)}</div>
      <p className="exec-footnote">Sample statuses are not production certifications. The 50-case golden set is a dashboard scenario; the working portal currently uses five regression cases. Retention, gateway limits and training-retention terms are illustrative governance assumptions.</p>
    </section>
    <div className="two-columns exec-two-panels">
      <section className="panel exec-intercepts"><div className="panel-heading"><div><div className="eyebrow">CRITIQUE QA</div><h2><ShieldCheck size={17} />Caught before the review gate.</h2></div><Pill tone="green">0 leaked to client</Pill></div>
        <div className="exec-intercept-total"><strong>26</strong><div><b>initial drafts intercepted</b><p>Rewritten before reaching the RM · sample window</p></div></div>
        {demoIntercepts.map(row => <div className="exec-intercept-row" key={row.label}><div><span>{row.label}</span><strong>{row.count}</strong></div><div className="exec-track"><span style={{ width: `${row.count / 14 * 100}%`, background: row.color }} /></div></div>)}
      </section>
      <section className="panel exec-drift"><div className="panel-heading"><div><div className="eyebrow">EARLY DRIFT SIGNAL</div><h2><Gauge size={17} />Listen to the relationship managers.</h2></div><Pill tone="green">Within threshold</Pill></div>
        <div className="exec-drift-value"><strong>4.2<span>%</span></strong><p>Draft-discard rate<br /><span>0.2 percentage points above 4.0% pilot baseline</span></p></div>
        <svg viewBox="0 0 420 132" className="exec-drift-chart" role="img" aria-label="Illustrative discard rate trend between 3.7 and 4.8 percent, below the ten percent alert threshold"><line x1="12" x2="405" y1="20" y2="20" stroke="var(--amber)" strokeDasharray="4 5" /><text x="405" y="12" textAnchor="end" fill="var(--amber)" fontSize="9">10% alert threshold</text><line x1="12" x2="405" y1="87" y2="87" stroke="var(--border)" strokeDasharray="3 5" /><polyline points="12,85 47,82 82,88 117,78 152,80 187,75 222,82 257,86 292,79 327,83 362,85 397,82" stroke="var(--green)" strokeWidth="3" strokeLinejoin="round" fill="none" /><circle cx="397" cy="82" r="4" fill="var(--green)" /><text x="12" y="123" fill="var(--muted)" fontSize="9">Week 1</text><text x="397" y="123" textAnchor="end" fill="var(--muted)" fontSize="9">Week 12</text></svg>
        <p className="exec-footnote">Illustrative trend. A breach would trigger an investigation of edit/discard reasons and a human decision on fallback. This dashboard does not monitor or enforce the threshold.</p>
      </section>
    </div>
    <section className="panel exec-audit"><div className="panel-heading"><div><div className="eyebrow">GOVERNANCE EVIDENCE</div><h2><BarChart3 size={17} />A clear record of human judgment.</h2><p>Five synthetic entries · illustrative retention hashes</p></div><Pill tone="purple">Sample audit log</Pill></div>
      <div className="exec-table-scroll" tabIndex={0} aria-label="Sample governance audit entries"><table><thead><tr><th>Case / time</th><th>Jurisdiction</th><th>Document lock</th><th>Critique score</th><th>RM action</th><th>7-year hash · mock</th></tr></thead><tbody>{demoAudit.map(entry => <tr key={entry.caseId}><td><strong>{entry.caseId}</strong><small>{entry.time} · demo session</small></td><td>{entry.city}</td><td><span className="exec-lock"><Check size={13} />Passed</span></td><td>{entry.score}%</td><td><Pill tone={entry.action === "Discarded" ? "rose" : entry.action === "Edited" ? "amber" : "green"}>{entry.action}</Pill></td><td><code>{entry.hash}</code></td></tr>)}</tbody></table></div>
    </section>
  </>;
}

export default function ExecutiveDashboardPage() {
  const [view, setView] = useState<"cfo" | "cro">("cfo");
  return <div className="executive-dashboard">
    <PageHead eyebrow="EXECUTIVE COMMAND CENTER" title="The bigger picture. A clearer decision."
      description="Financial opportunity and governance confidence, in one executive view."
      action={<Pill tone="purple"><FlaskConical size={13} />Illustrative demo</Pill>} />
    <div className="exec-toolbar"><div className="exec-view-toggle" role="group" aria-label="Executive dashboard view"><button aria-pressed={view === "cfo"} onClick={() => setView("cfo")}><CircleDollarSign size={17} /><span>CFO <small>Financial & ROI</small></span></button><button aria-pressed={view === "cro"} onClick={() => setView("cro")}><ShieldCheck size={17} /><span>CRO <small>Risk & governance</small></span></button></div><span className="exec-window"><Clock3 size={13} />Synthetic pilot · monthly board view</span></div>
    <div className="exec-demo-note"><FlaskConical size={15} /><span>All figures are seeded demo assumptions. Sliders and fallback controls simulate this screen only; they do not change cases, agents or services.</span></div>
    <div className="exec-view-content" key={view}>{view === "cfo" ? <CfoView /> : <CroView />}</div>
    <div className="exec-bottom-note"><TrendingUp size={14} /><span>First solution slice · missing-document chasing · synthetic Northgate corporate onboarding</span><span>Prepared for the boardroom <ArrowUpRight size={13} /></span></div>
  </div>;
}

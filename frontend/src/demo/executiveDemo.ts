/** Presentation-only telemetry. No records, agent calls or production controls. */
export const executiveAssumptions = {
  buildCost: 120000, monthlyRunCost: 4000, hourlyRate: 45,
  benefitRealization: 0.1875, chaseRounds: 3, aiCostPerCase: 0.018,
};

export function executiveScenario(volume: number, days: number, hours: number) {
  const a = executiveAssumptions;
  const annualHours = volume * hours * a.benefitRealization * 12;
  const grossMonthly = annualHours / 12 * a.hourlyRate;
  const netMonthly = grossMonthly - a.monthlyRunCost;
  return { annualHours, grossMonthly, netMonthly,
    payback: netMonthly > 0 ? a.buildCost / netMonthly : null,
    caseDays: volume * a.chaseRounds * days,
    yearOneRoi: (netMonthly * 12 - a.buildCost) / a.buildCost,
  };
}

export const demoAgentUsage = [
  { name: "Orchestrator", tokens: 184000, share: 19, cost: 0.002 },
  { name: "Drafter", tokens: 326000, share: 34, cost: 0.006 },
  { name: "Toner", tokens: 274000, share: 28, cost: 0.005 },
  { name: "Critique", tokens: 186000, share: 19, cost: 0.005 },
];

export const demoGates = [
  { title: "Identity & access", detail: "Least-privilege RM / analyst scopes", active: true },
  { title: "Data classification", detail: "Synthetic pilot · confidential stays on-prem", active: true },
  { title: "AI gateway & egress", detail: "6.4 / 20 RPM · no training retention assumed", active: false },
  { title: "Tool sign-off", detail: "Read-before-write · no autonomous send", active: true },
  { title: "Model risk (MRM)", detail: "Information preparation · human risk decisions", active: false },
  { title: "Change advisory board", detail: "50-case illustrative golden-set sign-off", active: true },
  { title: "Audit & retention", detail: "Seven-year retention target · trace evidence", active: false },
  { title: "Adoption & drift", detail: "RM edit / discard reasons · 10% alert line", active: false },
];

export const demoIntercepts = [
  { label: "Missing holding-layer document", count: 14, color: "var(--primary)" },
  { label: "Tone / jurisdiction clause", count: 6, color: "var(--amber)" },
  { label: "Unsupported risk wording", count: 4, color: "var(--rose)" },
  { label: "Checklist consolidation", count: 2, color: "var(--green)" },
];

export const demoAudit = [
  { caseId: "NG-2026-0841", city: "Singapore", score: 99, action: "Approved", hash: "c9f3…a102", time: "09:42" },
  { caseId: "NG-2026-0852", city: "New York", score: 98, action: "Edited", hash: "7d21…b8e4", time: "09:35" },
  { caseId: "NG-2026-0860", city: "London", score: 96, action: "Approved", hash: "a4e8…903f", time: "09:28" },
  { caseId: "NG-2026-0873", city: "New York", score: 100, action: "Approved", hash: "f028…d6c1", time: "09:19" },
  { caseId: "NG-2026-0881", city: "Singapore", score: 94, action: "Discarded", hash: "e13b…472a", time: "09:07" },
];

export type FinancialBucket = { calls: number; cost_gbp: number; cost_usd: number; prompt_tokens: number; completion_tokens: number; errors: number; failovers: number; average_latency_ms: number | null; p95_latency_ms: number | null };
export type FinanceReport = {
  period: { days: number; start: string; end: string; timezone: string };
  totals: FinancialBucket & { case_cost_gbp: number; non_case_cost_gbp: number; costed_cases: number; average_case_cost_gbp: number | null; average_call_cost_gbp: number | null; error_rate: number | null; offline_fixture_calls: number };
  agents: (FinancialBucket & { agent: string })[];
  providers: (FinancialBucket & { provider: string; model: string })[];
  daily: { date: string; cost_gbp: number; calls: number }[];
  case_costs: (FinancialBucket & { case_id: string; jurisdiction: string })[];
  jurisdictions: Record<string, { cases: number; costed_cases: number; cost_gbp: number; average_case_cost_gbp: number | null; nudge_due: number }>;
  activity: { case_inventory: number; case_statuses: Record<string, number>; documents: Record<string, number>; drafts_created: number; draft_statuses: Record<string, number>; generated: number; approved: number; discarded: number; edited: number; synthetic_outbox: number; discard_rate: number | null; workflow_runs: Record<string, number>; rewrite_events: number };
  pricing: Record<string, number>; limitations: string[];
};

export const defaultPlan = { volume: 400, manualHours: 5, assistedHours: 3, hourlyRate: 45, realization: 50,
  compute: 125, storage: 15, logging: 20, support: 300, external: 0, build: 120000, assumedAi: 0.02,
  rounds: 3, baselineDays: 5.5, targetDays: 3 };
export type FinancePlan = typeof defaultPlan;

export function calculatePlan(plan: FinancePlan, observedUnitCost: number | null) {
  const aiUnit = observedUnitCost ?? plan.assumedAi;
  const aiMonthly = aiUnit * plan.volume;
  const resources = plan.compute + plan.storage + plan.logging + plan.support + plan.external;
  const monthlyCost = resources + aiMonthly;
  const hoursFreed = Math.max(0, plan.manualHours - plan.assistedHours) * plan.volume;
  const grossValue = hoursFreed * plan.hourlyRate * plan.realization / 100;
  const net = grossValue - monthlyCost;
  return { aiUnit, aiMonthly, resources, monthlyCost, hoursFreed, grossValue, net,
    manualUnit: plan.manualHours * plan.hourlyRate,
    assistedUnit: plan.assistedHours * plan.hourlyRate + monthlyCost / plan.volume,
    technologyUnit: monthlyCost / plan.volume,
    payback: net > 0 ? plan.build / net : null,
    yearOneNet: net * 12 - plan.build,
    roi: plan.build > 0 ? (net * 12 - plan.build) / plan.build : null,
    caseDays: Math.max(0, plan.baselineDays - plan.targetDays) * plan.rounds * plan.volume };
}

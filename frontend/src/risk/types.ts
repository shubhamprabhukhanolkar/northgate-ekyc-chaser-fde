export type RiskReport = {
  period: { days: number; start: string; end: string; timezone: string };
  metrics: { outbox_records: number; human_signed: number; signoff_coverage: number | null; outbox_check_assessed: number; outbox_check_failures: number; outbox_check_failure_rate: number | null; missing_outbox_check_evidence: number; review_actions: number; approved: number; discarded: number; edited: number; discard_rate: number | null; previous_discard_rate: number | null; previous_review_actions: number; discard_reasons_recorded: number; drafts_created: number; assessed_drafts: number; qa_passed: number; qa_failed: number; average_tone_score: number | null; initial_intercepted_runs: number; streamed_qa_evaluations: number; rewrite_events: number; case_inventory: number; documents: Record<string, number>; workflow_runs: Record<string, number> };
  intercepts: Record<string, number>;
  daily: { date: string; approved: number; discarded: number; discard_rate: number | null }[];
  gates: { name: string; status: string; detail: string }[];
  providers: { provider: string; status: string; calls: number; failovers: number }[];
  exceptions: { case_id: string; jurisdiction: string; issues: string[] }[]; exception_count: number;
  regions: Record<string, { cases: number; exceptions: number }>;
  audit: { event_id: number; created_at: string; action: string; case_id: string | null; jurisdiction: string | null; actor_role: string; tone_score: number | null; reason_recorded: boolean | null }[];
  audit_coverage: { total: number; retention_marked: number | null; latest: string | null; append_only_triggers: number };
  change_control: { latest_test_at: string | null; latest_test_passed: boolean | null; latest_test_cases: number; prompt_versions: { agent: string; version: number }[] };
  limitations: string[];
};

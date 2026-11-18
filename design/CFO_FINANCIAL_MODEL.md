# CFO financial workspace

## Workflow analysis

The portal checks the synthetic document store before any drafting: received items
are locked out and missing items become the authoritative checklist. Orchestrator
plans one consolidated chase, Drafter creates it, Toner rewrites its voice, and
Critique QA checks document coverage, tone and policy. A failing critique can
trigger up to three rewrites. Drafting and redrafting therefore consume multiple
provider calls for one case. Editing and rechecking can add further critique calls.

Gemini is primary and Groq is the recovery provider. Failed attempts, successful
attempts, returned input/output token counts, latency and estimated costs are
recorded in `cost_ledger`. Invalid JSON can still incur recorded usage; failures
before token usage is returned are recorded with zero usage, so these records are
not a complete billing statement. The deterministic document check has no token
charge, but its infrastructure cost is not measured separately.

Portal Guide and Toner Studio regression tests also incur model costs. Some calls
have case IDs, including regression-test calls; others are non-case overhead.
The ledger has no run ID, so costs cannot be precisely attributed to individual
workflow executions. The CFO workspace reports average cost per **touched case**,
not a falsely precise cost per successfully completed onboarding or draft.

An RM/admin reviews the final draft. Approval records a synthetic outbox message;
this app does not send real client email. Follow-up scheduling flags unanswered
chases after three calendar days and requires human review again.

## Separate login and access

- `cfo@northgate.demo` is seeded as an independent `cfo` account using the same
  configured prototype operator password as the other seeded roles.
- CFO sign-in opens `/cfo`, with a finance-only sidebar and no drafting controls.
- The CFO account may read its identity, safe runtime metadata and
  `GET /api/cfo/summary`. Operational APIs, agent calls and case-data MCP linking
  are blocked for that account. Existing operator permissions are preserved.
- Admins may inspect the dashboard. Other roles cannot access its financial API.
- Loading, refreshing, exporting or changing planning assumptions never calls an
  agent, changes a case, updates prompts or writes financial records.

## Recorded reporting

Windows are the current UTC calendar day plus the preceding 6, 29 or 89 calendar
days, or all stored history, ending at report generation time. The trend is capped
at 90 days. Zero-activity days are displayed as zero; missing denominators are null
and displayed as a dash. No dummy transactions are inserted to populate the page.

| Metric | Calculation / source |
| --- | --- |
| Recorded provider spend | Sum stored GBP/USD cost for Gemini and Groq attempts in the window |
| Average cost per attempt | Total recorded provider cost / provider attempt count, including failures |
| Average cost per touched case | Case-attributed provider cost / distinct case IDs with provider attempts |
| Non-case overhead | Provider spend without a case ID, including Portal Guide |
| Failure rate | Attempts recorded with `error` / provider attempts |
| Successful failovers | Attempts marked failover and recorded successful; not a QA-pass rate |
| Average / p95 latency | Provider attempt latency, including failures; p95 uses nearest-rank percentile |
| Component/provider/region costs | Aggregation of the same filtered financial ledger |
| Draft records | Drafts created in the window, grouped by their current status |
| Review outcomes | Approval, discard and edit/recheck audit events dated in the window |
| Runs / rewrite events | Runs started in the window / persisted streaming revision events |
| Inventory / documents | Current snapshots; do not pretend these are historic inventory snapshots |

Offline fixtures are reported separately and excluded from provider cost averages.
Stored historical pricing is retained; current configured price assumptions and
USD/GBP conversion are shown separately in methodology. The report exposes case
references and aggregated costs, not client contacts, draft wording, prompts,
passwords or API keys.

## Savings and resource planning

There is no cloud billing integration, staff timesheet feed or realized-savings
record. Resource estimates (compute, storage/backups, logging/monitoring,
operations/support and external service fees) are browser-editable monthly GBP
assumptions, not claimed vendor rates. Defaults are illustrative starting inputs.

For monthly volume `V`, manual hours `M`, assisted hours `A`, hourly rate `R`,
recognized capacity percentage `P`, build investment `B` and AI unit estimate `U`:

- Monthly hours freed = `max(M − A, 0) × V`.
- Recognized monthly capacity value = `hours freed × R × P / 100`.
- Monthly technology/operating cost = `resource assumptions + U × V`.
- Monthly net projected value = `recognized capacity value − operating cost`.
- Payback = `B / positive monthly net`; nonpositive net has no payback.
- Year-1 net value = `12 × monthly net − B`.
- Year-1 net ROI = `Year-1 net value / B`; zero build cost has undefined ROI.
- Manual effort cost per file = `M × R`.
- Assisted effort plus technology per file = `A × R + operating cost / V`.
- Time-to-revenue opportunity = `(5.5 − 3.0) × 3 × V` case-days/month, never
  monetized again as cash savings.

`U` uses the selected window's observed cost per touched case when available;
otherwise it uses the explicit fallback planning assumption. A change in workload
mix, retries or the reporting period can change that estimate. This is not a price
guarantee or a run-cost forecast based on matched execution-level billing.

Inputs persist only for the current page instance. Export downloads the selected
financial aggregates, planning assumptions, derived projections and limitations as
JSON. All savings remain projected capacity value, not realized cash savings or
confirmed staffing reductions. The existing instance-local lab database can lose
history on service replacement and is not a durable accounting system.

## Verification

Backend tests cover known cost samples, reporting windows, zero denominators,
offline exclusion, failovers, latency, roles and forbidden actions. Browser checks
cover separate CFO login, redirects, refresh persistence, report windows, planner
edge cases, reset/export, dark/light modes and narrow-screen layouts. The existing
portal suite is retained.

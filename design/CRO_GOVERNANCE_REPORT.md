# CRO risk and governance workspace

The separate `cro@northgate.demo` account opens `/cro`. It is seeded with the
configured prototype operator password. CRO users have only their read-only
governance workspace; admins may inspect it too. CFO and operational roles cannot
read its API. The CRO account cannot generate, edit, approve, discard, run prompts,
change outages, query the operational chatbot or authorize case-reading MCP access.

`GET /api/cro/summary?days=7|30|90|0` aggregates existing records in a read
transaction. It invokes no agent and writes no operational records. Reporting
windows use UTC calendar boundaries, ending at generation time; `0` means all
stored history. Refresh, the local threshold input and JSON export are read-only.

## Metrics and evidence

| Panel | Basis and limits |
| --- | --- |
| Stored false-chase check failures | Failed `zero_false_chases` flags on drafts linked to synthetic outbox rows / rows with a known boolean flag. Missing links/flags are separate gaps, not implicit passes. This is not an independent replay against historical documents. |
| Human sign-off evidence | Outbox rows matched to an approval audit by case/draft ID, within five minutes, with a current RM/admin actor role. Current roles are not historical identity-provider attestations. |
| Discard rate | Discard actions / approval plus discard actions in the selected window. Prior comparison uses the preceding equal calendar window; volumes can differ. All-history has no comparison. |
| Final QA outcomes | Stored final scorecards for drafts created in the window. Unknown/invalid scorecards are not treated as passes. Tone averages include only numeric 0–100 scores. |
| Intercepts and rewrites | First-attempt streaming Critique failures counted by unique run; failure categories aggregated across streaming QA events. Categories overlap. Nonstreaming/older runs may lack intermediate evidence. |
| Exceptions | Current latest pending drafts with changed checklist revisions, blocked or unavailable QA; plus current follow-up flags. These are workflow flags, not client risk ratings. Up to 50 cases are returned, five per page. |
| Prompt controls | Current maximum prompt versions and latest stored regression result/case count. The latest test is not proof that a particular version was published. Existing admin publishing enforces the exact five-case test and one-hour freshness. |
| Audit coverage | Current record counts, retention-date metadata and presence of the two append-only triggers. This does not attest durable seven-year retention or a cryptographic hash chain. |
| Provider resilience | Recorded provider attempts, errors and successful failovers in the window. Transport success is not final QA success. |
| Governance table | Latest 50 selected operational audit events in the window, five per page. Scores are linked to stored drafts where available; actor roles can remain unresolved. Raw reasons, contacts, full drafts, prompts and secrets are excluded. |

## Eight governance gates

The scorecard distinguishes **implemented**, **partial**, **scope limited** and
**not evidenced**. It describes app-level RBAC, synthetic-data scope, gateway/
egress evidence, tool sign-off, model risk review, prompt change control, audit/
retention and adoption/drift tracking. It does not label every gate passed merely
because the dashboard exists. No formal MRM exemption, gateway rate limit,
production data classification or vendor retention agreement is inferred.

The discard review threshold defaults to 10% and is a local display aid only.
Changing it sends no write request, produces no external alert and does not pause
services. The escalation panel is guidance for human follow-up; it is not a kill
switch. Empty samples display unavailable rates rather than invented zero-incident
or 100%-compliance values. Daily charts omit days without review actions.

The app sends no external client emails. Its instance-local SQLite history can be
lost on replacement. Operational evidence here is not a regulatory assessment,
independent audit, AML decision or credit-risk rating.

## Verification

Tests cover missing evidence, known sign-off/QA/drift samples, privacy canaries,
window validation, absence of agent calls and server-enforced role restrictions.
Browser checks cover CRO login/redirects, finance separation, report windows,
threshold changes, export, themes, mobile layouts and preservation of CFO access.

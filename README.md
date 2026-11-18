# Northgate eKYC — Missing-Document Chaser

A synthetic corporate onboarding prototype: React/Vite/Tailwind, Python 3.12/FastAPI, a cyclical LangGraph workflow, SQLite, and the official Python FastMCP adapter. Direct Gemini APIs only; no Vertex AI.

**Live app:** https://northgate-ekyc-chaser-ruxttjrlxq-el.a.run.app · **MCP:** https://northgate-ekyc-chaser-ruxttjrlxq-el.a.run.app/mcp/ · [Public repository](https://github.com/shubhamprabhukhanolkar/northgate-ekyc-chaser-fde) · [Successful CI/container deployment](https://github.com/shubhamprabhukhanolkar/northgate-ekyc-chaser-fde/actions/workflows/deploy.yml).

Validation covers 35 backend tests, the production frontend build, official stdio and authenticated HTTP MCP, real Gemini generation and Groq outage failover, and desktop/mobile browser checks. Docker is built and deployed by GitHub Actions; Docker is unavailable on the local Windows host, so a local Docker run is not performed. The local FastAPI process serves the same built frontend on port 8080.

## Operator experience

The queue contains 42 synthetic companies, 14 per jurisdiction, displayed six per page with Previous, numbered pages and Next. Search and jurisdiction filters reset pagination to the first page.

The top bar contains **Guided draft** (yellow), **Auto-draft** (green), Audio and Dark/Light in that order. The drafting preference is shared across pages, remembered by the browser and synchronized across tabs. Guided draft initially shows the AI workflow and waits for at least five characters of instructions before generating; Auto-draft automatically prepares a needed draft and accepts optional guidance for redrafts. Both modes keep the mandatory RM approval gate. Guidance is positioned beneath the workflow visualization and is sent to the agents as operator input, with safety contracts enforced separately.

Gap Workspace flips between the draft editor and **AI workflow**, with live stage events, revision paths and a shared activity feed. Drafter and Toner stream actual provider output into an explicitly unreviewed preview. Runs persist events in SQLite and continue after the browser navigates away; SSE reconnects using event IDs. Interrupted runs are marked accordingly on restart. Agent Trace is read-only and filters recorded activity for all five workflow stages plus Portal Guide; it has no drafting controls.

Portal Guide primarily explains how to use the actual portal, with citations to 12 product-help references and the five synthetic KYC clauses. It includes recent conversation context, starting questions, Clear chat and Back-to-welcome controls. Clear and Back cancel pending browser requests and prevent late answers from restoring cleared conversations.

Interface sounds are synthesized locally with Web Audio, disabled by default and enabled only after a user gesture. Optional cues distinguish navigation, theme changes, stage handoffs, rewrites and review readiness. The muted speaker icon uses a theme-appropriate red. Theme switches, workflow flips, chat replies and the Portal Guide illustration animate while respecting reduced-motion preferences. Browser preferences and audio do not expose provider keys.

## Run locally

```powershell
Copy-Item .env.example .env
# Set your keys and random AUTH_SECRET / MCP_API_KEY privately in .env.
uv sync --frozen
cd frontend
npm ci
npm run build
cd ..
uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8080
```

Open http://localhost:8080. For frontend development, run `npm run dev` in `frontend/`; Vite proxies `/api` to port 8080. Demo roles: `rm@northgate.demo`, `analyst@northgate.demo`, `coo@northgate.demo`, `admin@northgate.demo`. Initial password: `NorthgateDemo!2026` (override `DEFAULT_OPERATOR_PASSWORD` before the first seed). Passwords use Argon2, sessions use signed expiring tokens in HTTP-only cookies; Bearer tokens are also supported. Password changes require an explicit migration/reset of the synthetic database; changing the environment after seeding does not replace password hashes.

`OFFLINE_DEMO=true` explicitly enables labeled deterministic fixtures with zero billed tokens. Defaults to false: missing keys and provider failures return errors rather than manufactured AI results.

## Workflow and safety

1. Read the deterministic jurisdiction checklist from the synthetic document store.
2. Orchestrator plans the chase; Drafter writes one email; Toner rewrites using versioned settings.
3. Critique checks received-document exclusions, completeness, prohibited claims, and tone/policy ≥95%. Failure routes to Orchestrator for up to **three rewrites after the initial attempt**. Exhausted drafts remain blocked.
4. The RM reviews, edits (which reruns QA), approves, or discards with a reason. Approval rechecks document state in a SQLite transaction and refuses stale drafts.
5. Approved messages go to a **synthetic outbox**, not an external mail service. The worker flags unanswered chases after three calendar days, every 30 seconds. A recorded reply suppresses nudges. Nothing auto-sends.

The draft must include canonical document names and exact missing IDs; received canonical names and IDs are rejected. The LLM critique also receives the complete checklist. This is a tested prototype safety gate, not a claim that arbitrary natural-language false chases have been proven impossible. Document checks verify presence/metadata only, with no authenticity or final risk judgments.

Analysts can run drafts and record synthetic receipts. RMs/admins can approve, discard, or edit. Only admins can change prompts or simulate outages in the web app. COO access is read-only. MCP is a separately authorized integration: its key permits drafting, discard, policy questions and regression-tested tone updates; approval additionally requires an RM session token tied to the exact draft.

## Prompts, policy and FinOps

The studio persists all four prompts and version history in SQLite. An exact-candidate five-case regression must pass within the last hour before web prompt saves. MCP toner updates also run the five-case regression. Portal Guide retrieves four relevant references from the product-help and synthetic KYC collection, with weighted title/keyword/text matching and bounded recent-chat context. It returns only known source citations and records its own agent trace. It is a small grounded help system, not a legal research system.

Every LLM provider attempt records agent, model, provider, input/output tokens, latency, USD/GBP estimates and case. Successful billable responses are recorded even if JSON parsing fails; failed calls have unknown usage represented as zero. Gemini 429/5xx/timeouts/connection/quota-unavailable failures trigger Groq. Other errors remain visible. The admin outage toggle forces that failover path.

Default pricing estimates per million tokens are Gemini $0.10/$0.40 and Groq $0.59/$0.79 (input/output), with USD→GBP 0.79. Override `GEMINI_INPUT_PER_MILLION`, `GEMINI_OUTPUT_PER_MILLION`, `GROQ_INPUT_PER_MILLION`, `GROQ_OUTPUT_PER_MILLION`, `USD_TO_GBP` for your model contract. Telemetry is an estimate rather than billing reconciliation. ROI is explicitly projected: `(5.5 − 3.0) × 3 rounds × 400 cases = 3,000 case-days/month`. No unmeasured savings are presented as realized outcomes.

The verified deployed primary is `GEMINI_MODEL_NAME=gemini-3.5-flash-lite`; `GEMINI_MODEL` remains a compatible fallback variable. The configured backup is `GROQ_MODEL=openai/gpt-oss-120b`, approved because the supplied key cannot access `llama-3.3-70b-versatile`. Both provider connections were verified. Update the pricing overrides to your chosen backup's rates. Provider availability depends on the key's accessible models.

## CRO risk and governance workspace

The separate **CRO** demo login (`cro@northgate.demo`, configured operator password) opens `/cro` for read-only governance oversight. It reports existing QA, sign-off, drift, exception, prompt-control and sanitized audit evidence without invoking agents. Empty evidence is not treated as compliance; the local threshold changes no services. See [CRO governance methodology](design/CRO_GOVERNANCE_REPORT.md). Admins can inspect both executive dashboards; CFO and CRO accounts remain separately scoped.

## CFO financial workspace

Choose **CFO** on the demo login (`cfo@northgate.demo`, configured operator password) to open `/cfo`. This is a separate read-only finance role; admins can inspect it too. The dashboard reads existing telemetry, provides dated cost and unit-economics reports, and includes a clearly labelled resource/savings planner. It invokes no AI agents. Recorded token-price estimates, current inventory and planning assumptions remain distinct. See [workflow analysis and financial methodology](design/CFO_FINANCIAL_MODEL.md) for sources, formulas, permissions and data limits.

## Gemini / MCP connection guide

Portal Guide's operational knowledge and six starting questions are maintained together in `backend/app/agents/portal_help.py`. Update this catalog when changing screens, control labels, defaults, permissions or workflows. The welcome cards load from the authenticated `/api/policy/help` endpoint, so their questions match the backend knowledge. Guide requests include the authenticated operator role and current browser drafting preference; they do not grant the guide action tools or live-case lookup. Coverage tests compare the help index with every navigation screen and exercise operational questions, follow-ups and unsupported requests.

### Personal read-only connections

The local implementation now has a separate `/mcp-readonly/` Streamable HTTP endpoint with user-delegated OAuth authorization-code access and mandatory S256 PKCE. It is separate from the shared-key `/mcp/` integration described below. Deploy and test the new endpoint before giving its URL to end users; these changes do not update an already-running Cloud Run revision.

Signed-in users open **Connected Apps** in the portal to copy the endpoint and manage their connections. A compatible client discovers `/.well-known/oauth-protected-resource/mcp-readonly` and `/.well-known/oauth-authorization-server`, registers a public PKCE client at `/oauth/register`, and starts `/oauth/authorize`. The user explicitly allows read-only access, signing in if needed. `/oauth/token` issues one-hour opaque access tokens and rotating refresh tokens, with a maximum connection lifetime of 30 days. Token/code values are stored only as SHA-256 hashes. Disconnecting from the portal or calling `/oauth/revoke` invalidates the grant and its access/refresh tokens. Reads are audited with the operator's email.

Only three tools are registered: `list_onboarding_cases`, `get_case_gap_checklist`, and `get_case_draft`. No generation, edits, approvals, discards, sending, system settings or FinOps tools are exposed. These credentials are rejected by `/mcp/` and the web API. Conversely, portal session tokens and the shared `MCP_API_KEY` do not authorize `/mcp-readonly/`. Reading a checklist through this endpoint does not create a write-enabling read receipt. The prototype has a shared case queue: read-only users see the same cases they can see in the portal, without individual case assignments.

For deployment set `PUBLIC_BASE_URL` to the canonical public HTTPS portal origin (no trailing path), and include its hostname in `MCP_ALLOWED_HOSTS`. Local testing uses `http://localhost:8080/mcp-readonly/`. The public origin can otherwise be derived only from explicit allowed hosts or loopback hosts. Use persistent database storage before relying on long-lived connections: the current Cloud Run lab stores SQLite on ephemeral instance storage, so grants can disappear on replacement and cannot be shared across instances reliably.

For eligible personal Gemini accounts, Google's documented flow is **Settings > Connected Apps > Add a custom app**, paste the public `/mcp-readonly/` URL, follow the Northgate sign-in/consent flow, then select Northgate with `@` in chat. Google's current eligibility is US users aged 18+, English, with Keep Activity enabled; availability is controlled by Google. See [Gemini custom app instructions](https://support.google.com/gemini/answer/17209137?hl=en) and [Google's OAuth account-linking guide](https://developers.google.com/connected-apps/mcp/oauth). We test the server's OAuth and MCP flows locally; a successful personal Gemini connection still requires verification in an eligible real Gemini account after deployment.

### Existing shared-key integration

The remote server uses **Streamable HTTP**, supporting JSON/SSE content negotiation. The canonical URL ends in `/mcp/`; `/mcp` redirects there. This is not the legacy standalone SSE transport. MCP clients must support Streamable HTTP and custom Bearer headers. [Gemini CLI's official MCP guide](https://geminicli.com/docs/tools/mcp-server/) documents these configurations; Gemini Enterprise availability and credential setup depend on the host's connector support, so this is not an assertion that every Gemini surface accepts arbitrary custom-header MCP servers.

`MCP_ALLOWED_HOSTS` is a comma-separated explicit hostname allowlist for DNS-rebinding protection (no scheme or path). The deployment workflow includes the existing Cloud Run URL and the regional project-number URL. Add any custom host before connecting through it; the SDK supports wildcard ports, not wildcard domain names.

Local Gemini CLI `.gemini/settings.json` (replace the absolute checkout path):

```json
{
  "mcpServers": {
    "northgate": {
      "command": "uv",
      "args": ["run", "--project", "C:/Users/shubh/Desktop/northgate", "--directory", "C:/Users/shubh/Desktop/northgate/backend", "python", "-m", "app.mcp.server"],
      "env": {
        "DATABASE_PATH": "C:/Users/shubh/Desktop/northgate/data/northgate.db",
        "GEMINI_API_KEY": "${GEMINI_API_KEY}",
        "GROQ_API_KEY": "${GROQ_API_KEY}",
        "AUTH_SECRET": "${AUTH_SECRET}",
        "GROQ_MODEL": "openai/gpt-oss-120b",
        "GEMINI_MODEL_NAME": "gemini-3.5-flash-lite"
      },
      "trust": false
    }
  }
}
```

For manual stdio use, from `backend/`: `uv run --project .. python -m app.mcp.server`. Set keys in the parent process environment: the root `.env` is not automatically loaded when launching from another working directory. Stdio is trusted local-process access and does not use HTTP bearer middleware. It does not start the follow-up worker; run the main web app for that worker.

Remote Gemini CLI configuration (substitute the verified Cloud Run service URL and export `MCP_API_KEY` privately):

```json
{
  "mcpServers": {
    "northgate": {
      "httpUrl": "https://northgate-ekyc-chaser-ruxttjrlxq-el.a.run.app/mcp/",
      "headers": {"Authorization": "Bearer ${MCP_API_KEY}"},
      "trust": false
    }
  }
}
```

Tools: `list_onboarding_cases`, `get_case_gap_checklist`, `generate_chase_draft`, `approve_or_discard_draft`, `get_finops_cost_summary`, `query_kyc_policy`, `update_toner_settings`. Tools publish validated JSON input/output schemas.

Read-before-write example: list cases → get the gap checklist → generate a draft. `approve_send` with only an MCP key returns a human-approval requirement. The RM opens the case workspace, reviews the exact draft, and clicks **Authorize exact draft for MCP**. The resulting two-minute token can be passed as `rm_approval_token`; it is bound to the case, draft ID and content digest. A successful decision consumes the pending draft, preventing repeat sends. An edited, replaced, stale, blocked or already-sent draft cannot be approved with that token. Alternatively, the RM clicks Approve & Send directly in the UI.

## Test and container

```powershell
uv run pytest -q
cd frontend
npm run build
cd ..
docker build -t northgate-ekyc .
docker run --rm -p 8080:8080 --env-file .env -e DATABASE_PATH=/app/data/northgate.db -e STATIC_DIR=/app/static northgate-ekyc
```

The Dockerfile builds Vite with Node 20 and serves FastAPI + built assets + `/mcp` in one non-root Python 3.12 container. Unit/integration tests use isolated databases and explicit offline fixtures or mocked providers, never your live API keys. `scripts/probe_providers.py` makes small real provider calls; `scripts/smoke_live.py [base-url]` verifies login, a full real-agent run, citations, ledger and authenticated HTTP MCP. It leaves the draft awaiting RM review.

## GitHub Actions and Cloud Run

The deployment workflow follows `p1.yml`: tests/build → Google authentication → Artifact Registry Docker build/push → Cloud Run deployment → health/static/MCP verification. It uses only the existing `slabsuser37-service-account` for deployment and runtime, project `slabspro-slabsuser37`, region `asia-south1`, service `northgate-ekyc-chaser`, image repository `omnistream-repo`.

GitHub secrets: `GCP_CREDENTIALS` (or `GCP_SA_KEY`), `GEMINI_API_KEY`, `GROQ_API_KEY`, `AUTH_SECRET`, `MCP_API_KEY`, `DEFAULT_OPERATOR_PASSWORD`. Variables: `GCP_PROJECT`, `GCP_SERVICE_ACCOUNT`, `GEMINI_MODEL_NAME`; `GROQ_MODEL` when overriding the default. Credentials must never be committed. The bootstrap script transfers `.env` secrets through stdin; service-account key creation requires explicit authorization. The workflow copies runtime secrets into regional-replica Secret Manager secrets and mounts secret references into Cloud Run.

One instance with allocated CPU keeps the in-process worker active. SQLite lives inside the container as requested. **Container replacement can reset cases, sessions, prompt history, costs and audit records.** Cloud Run's filesystem is ephemeral and this profile does not provide durable seven-year retention. Audit rows are append-only within the application DB and carry seven-year retention timestamps; external durable archival is required before any real production use. Revision rollout may briefly overlap instances, each with its own SQLite database. This is a lab prototype with synthetic data only.

Structured worker/error events are emitted as JSON to stdout/stderr for Cloud Logging. No optional Firestore or Storage resources are used. Secret Manager replicas and Cloud Run are in `asia-south1`; the direct Gemini/Groq inference APIs do not guarantee Mumbai-only processing.

## Design references

The UI follows the workspace's Stitch screen structure: slim navigation, daily queue cards, two-pane checklist/draft, pipeline trace, prompt studio, follow-up tracker, FinOps and policy chat. Phantom tokens: `#111114`, `#1C1C21`, `#AB9FF2`, `#2EC08B`. Light tokens: `#F8FAFC`, `#FFFFFF`, `#2563EB`. The exported designs contain unreachable image assets and illustrative metrics; the implementation uses a local monogram and measured or explicitly projected metrics.

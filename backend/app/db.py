import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .config import settings


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect():
    path = Path(settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def rows(query, args=()):
    with connect() as db:
        return [dict(r) for r in db.execute(query, args).fetchall()]


def audit(db, actor, action, case_id=None, payload=None):
    db.execute("INSERT INTO audit(actor,action,case_id,payload,created_at,retain_until) VALUES(?,?,?,?,?,?)",
               (actor, action, case_id, json.dumps(payload or {}), now(),
                (datetime.now(timezone.utc) + timedelta(days=365 * 7 + 2)).isoformat()))


PROMPTS = {
    "orchestrator": "Plan a single consolidated missing-document chase. Use only supplied gap IDs. Respect the mandatory RM review gate. Return JSON with plan.",
    "drafter": "Draft one courteous email requesting every missing document, and no received document. Never judge authenticity or assign a risk rating. Return JSON with subject, body, requested_document_ids.",
    "toner": "Rewrite the draft using the supplied formality, urgency and synthetic jurisdiction clause. Preserve every missing document ID. Never add requirements. Return JSON with subject, body, requested_document_ids.",
    "critique": "Evaluate tone and synthetic policy compliance. Reject pressure, threats, authenticity or risk claims. Return JSON with tone_score (0-100), policy_compliant (boolean), feedback (list of strings). Score honestly; do not assume a pass."
}
DOCUMENTS = {
    "UK": [("incorporation", "Certificate of incorporation"), ("ubo", "Beneficial ownership register"), ("address", "Registered address evidence")],
    "SG": [("incorporation", "ACRA business profile"), ("ubo", "Register of controllers"), ("mandate", "Board account mandate")],
    "US": [("incorporation", "Articles of incorporation"), ("ubo", "Beneficial ownership certification"), ("ein", "IRS EIN confirmation")],
}


def initialize():
    from .auth import password_hash
    with connect() as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users(email TEXT PRIMARY KEY, name TEXT, role TEXT, password_hash TEXT);
        CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY, company TEXT, jurisdiction TEXT, city TEXT,
          contact TEXT, status TEXT DEFAULT 'NEEDS_DRAFT', opened_at TEXT, target_date TEXT,
          last_sent_at TEXT, replied_at TEXT, nudge_due INTEGER DEFAULT 0, revision INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS documents(case_id TEXT REFERENCES cases(id), id TEXT, name TEXT,
          status TEXT CHECK(status IN ('RECEIVED','MISSING')), received_at TEXT, source TEXT DEFAULT 'Synthetic On-Prem Document Store',
          PRIMARY KEY(case_id,id));
        CREATE TABLE IF NOT EXISTS drafts(id TEXT PRIMARY KEY, case_id TEXT REFERENCES cases(id), subject TEXT,
          body TEXT, requested_ids TEXT, scorecard TEXT, status TEXT, gap_revision INTEGER, created_at TEXT, provider TEXT);
        CREATE UNIQUE INDEX IF NOT EXISTS one_review_draft ON drafts(case_id) WHERE status='REVIEW';
        CREATE TABLE IF NOT EXISTS prompt_versions(id INTEGER PRIMARY KEY, agent TEXT, content TEXT, settings TEXT,
          version INTEGER, created_at TEXT, actor TEXT);
        CREATE TABLE IF NOT EXISTS cost_ledger(id INTEGER PRIMARY KEY, agent_name TEXT, provider TEXT, model TEXT,
          prompt_tokens INTEGER, completion_tokens INTEGER, latency_ms REAL, cost_usd REAL, cost_gbp REAL,
          case_id TEXT, created_at TEXT, status TEXT, failover INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS traces(id INTEGER PRIMARY KEY, run_id TEXT, case_id TEXT, node TEXT, payload TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, actor TEXT, action TEXT, case_id TEXT, payload TEXT,
          created_at TEXT, retain_until TEXT);
        CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'append-only audit'); END;
        CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'seven-year audit retention'); END;
        CREATE TABLE IF NOT EXISTS config(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS read_receipts(actor TEXT, case_id TEXT, revision INTEGER, read_at TEXT,
          PRIMARY KEY(actor,case_id));
        CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, draft_id TEXT UNIQUE, case_id TEXT, payload TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS regression(id TEXT PRIMARY KEY, digest TEXT, result TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS workflow_runs(id TEXT PRIMARY KEY, case_id TEXT REFERENCES cases(id), actor TEXT,
          status TEXT, started_at TEXT, finished_at TEXT);
        CREATE UNIQUE INDEX IF NOT EXISTS one_live_case_run ON workflow_runs(case_id) WHERE status='RUNNING';
        CREATE TABLE IF NOT EXISTS workflow_events(id INTEGER PRIMARY KEY, run_id TEXT REFERENCES workflow_runs(id),
          kind TEXT, data TEXT, created_at TEXT);
        CREATE INDEX IF NOT EXISTS workflow_event_cursor ON workflow_events(run_id,id);
        CREATE TABLE IF NOT EXISTS workflow_requests(run_id TEXT PRIMARY KEY REFERENCES workflow_runs(id),
          mode TEXT, instructions TEXT);
        CREATE TABLE IF NOT EXISTS mcp_clients(id TEXT PRIMARY KEY, name TEXT NOT NULL, redirects TEXT NOT NULL,
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS mcp_authorizations(id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES mcp_clients(id),
          redirect_uri TEXT NOT NULL, challenge TEXT NOT NULL, state TEXT NOT NULL, resource TEXT NOT NULL,
          csrf_hash TEXT NOT NULL, expires_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS mcp_codes(hash TEXT PRIMARY KEY, client_id TEXT NOT NULL, email TEXT NOT NULL REFERENCES users(email),
          redirect_uri TEXT NOT NULL, challenge TEXT NOT NULL, resource TEXT NOT NULL, expires_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS mcp_grants(id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES mcp_clients(id),
          email TEXT NOT NULL REFERENCES users(email), resource TEXT NOT NULL, created_at TEXT NOT NULL,
          expires_at REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS mcp_tokens(hash TEXT PRIMARY KEY, grant_id TEXT NOT NULL REFERENCES mcp_grants(id),
          kind TEXT NOT NULL, expires_at REAL NOT NULL);
        ''')
        for role, name in [("rm", "Marcus Sterling"), ("analyst", "Priya Chen"), ("coo", "Alex Morgan"), ("admin", "Sam Taylor"), ("cfo", "Eleanor Brooks")]:
            if not db.execute("SELECT 1 FROM users WHERE email=?", (f"{role}@northgate.demo",)).fetchone():
                db.execute("INSERT INTO users VALUES(?,?,?,?)", (f"{role}@northgate.demo", name, role, password_hash(settings().default_operator_password)))
        for agent, content in PROMPTS.items():
            if not db.execute("SELECT 1 FROM prompt_versions WHERE agent=?", (agent,)).fetchone():
                db.execute("INSERT INTO prompt_versions(agent,content,settings,version,created_at,actor) VALUES(?,?,?,?,?,?)",
                           (agent, content, json.dumps({"formality": 75, "urgency": "First Chase", "jurisdiction_clause": "Auto"}), 1, now(), "system"))
        names = [("Helios Maritime Ltd", "SG", "Singapore"), ("Ashford Capital Partners", "UK", "London"),
                 ("Meridian Technologies Inc", "US", "New York"), ("Evergreen Logistics Pte", "SG", "Singapore"),
                 ("Sterling Energy Holdings", "UK", "London"), ("Atlas Healthcare Inc", "US", "New York"),
                 ("Crescent Trade Group", "UK", "London"), ("Orion Pacific Pte", "SG", "Singapore"),
                 ("Brookfield Robotics Inc", "US", "New York"), ("Harbour & Finch Ltd", "UK", "London"),
                 ("Solstice Ventures Pte", "SG", "Singapore"), ("Pioneer Materials Inc", "US", "New York")]
        from .synthetic import ADDITIONAL_CASES
        names += ADDITIONAL_CASES
        for i, (company, jurisdiction, city) in enumerate(names):
            cid = f"NG-2026-{841+i:04}"
            if db.execute("SELECT 1 FROM cases WHERE id=?", (cid,)).fetchone():
                continue
            sent = (datetime.now(timezone.utc)-timedelta(days=4)).isoformat() if i in (3, 5, 9) else None
            db.execute("INSERT INTO cases(id,company,jurisdiction,city,contact,status,opened_at,target_date,last_sent_at,nudge_due) VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (cid, company, jurisdiction, city, f"onboarding{i+1}@example.com", "AWAITING_REPLY" if sent else "NEEDS_DRAFT", now(),
                        (datetime.now(timezone.utc)+timedelta(days=10+i)).date().isoformat(), sent, int(bool(sent))))
            for j, (did, title) in enumerate(DOCUMENTS[jurisdiction]):
                status = "RECEIVED" if j == 0 or (i % 4 == 2 and j == 2) else "MISSING"
                db.execute("INSERT INTO documents(case_id,id,name,status,received_at) VALUES(?,?,?,?,?)", (cid, did, title, status, now() if status == "RECEIVED" else None))


def prompt(agent):
    return rows("SELECT * FROM prompt_versions WHERE agent=? ORDER BY version DESC LIMIT 1", (agent,))[0]


def config(key, default="false"):
    result = rows("SELECT value FROM config WHERE key=?", (key,))
    return result[0]["value"] if result else default

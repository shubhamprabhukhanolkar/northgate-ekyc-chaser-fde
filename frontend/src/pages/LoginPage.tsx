import { useState, FormEvent } from "react";
import { ArrowRight, ShieldCheck, LockKeyhole, Check } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import ExperienceControls from "../components/ExperienceControls";
import { ErrorBox } from "../components/UI";
export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("rm@northgate.demo");
  const [password, setPassword] = useState("NorthgateDemo!2026");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login">
      <div className="login-story">
        <a className="brand" href="/">
          <div className="monogram">
            N<span>◈</span>
          </div>
          <div>
            <strong>Northgate</strong>
            <small>CORPORATE BANK</small>
          </div>
        </a>
        <div className="login-copy">
          <div className="eyebrow">ONBOARDING, MOVING FORWARD</div>
          <h1>
            Less chasing.
            <br />
            More <em>progress.</em>
          </h1>
          <p>
            A considered approach to corporate onboarding.
            <br />
            One consolidated chase. Your judgment at every step.
          </p>
          <div className="login-visual">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="visual-core">
              <ShieldCheck size={38} />
            </div>
            <span className="visual-tag tag-one">
              <Check size={14} /> Received documents locked
            </span>
            <span className="visual-tag tag-two">
              <LockKeyhole size={14} /> RM approval required
            </span>
            <span className="visual-tag tag-three">
              62d <ArrowRight size={16} /> 30d target
            </span>
          </div>
          <div className="login-stat">
            <strong>
              3,000<span>case-days / month</span>
            </strong>
            <p>
              Projected capacity unlocked across
              <br />
              London, Singapore and New York.
            </p>
          </div>
        </div>
        <small className="muted">
          NORTHGATE CORPORATE BANK · SYNTHETIC DEMONSTRATION
        </small>
      </div>
      <div className="login-panel">
        <ExperienceControls login />
        <form onSubmit={submit}>
          <div className="login-lock">
            <LockKeyhole size={25} />
          </div>
          <div className="eyebrow">SECURE OPERATOR ACCESS</div>
          <h2>Welcome to your workspace.</h2>
          <p>Sign in to keep corporate onboarding moving.</p>
          <label>
            Work email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          <div className="login-helper">
            <ShieldCheck size={14} /> Password authentication · 8-hour secure
            session
          </div>
          <ErrorBox message={error} />
          <button className="primary full" disabled={busy}>
            {busy ? "Signing in…" : "Enter workspace"}
            <ArrowRight size={17} />
          </button>
          <div className="demo-label">EXPLORE A DEMO ROLE</div>
          <div className="role-pills">
            {["rm", "analyst", "coo", "cfo", "admin"].map((role) => (
              <button
                type="button"
                className={email.startsWith(role + "@") ? "selected" : ""}
                onClick={() => {
                  setEmail(role + "@northgate.demo");
                  setPassword("NorthgateDemo!2026");
                }}
                key={role}
              >
                {role.toUpperCase()}
              </button>
            ))}
          </div>
          <p className="login-disclaimer">
            Synthetic cases only. Demo passwords are prefilled.
            <br />
            No client messages are sent outside this application.
          </p>
        </form>
        <small className="login-bottom">
          <ShieldCheck size={13} /> Human oversight is built into every action.
        </small>
      </div>
    </div>
  );
}

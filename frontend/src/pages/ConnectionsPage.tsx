import { useState } from "react";
import { Copy, Link2, ShieldCheck, Unplug } from "lucide-react";
import { api } from "../api";
import { Empty, ErrorBox, Loading, PageHead, Pill, usePoll } from "../components/UI";

type Connection = { id: string; client_name: string; created_at: string; expires_at: number };
type Connections = { endpoint: string; connections: Connection[] };

export default function ConnectionsPage() {
  const { data, error, setData } = usePoll(() => api<Connections>("/mcp/connections"));
  const [notice, setNotice] = useState("");
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  async function disconnect(connection: Connection) {
    setBusy(connection.id);
    setActionError("");
    try {
      await api(`/mcp/connections/${encodeURIComponent(connection.id)}`, { method: "DELETE" });
      setData(await api<Connections>("/mcp/connections"));
      setNotice(`${connection.client_name} disconnected. Its access has been revoked.`);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Could not disconnect. Please try again.");
    } finally {
      setBusy(null);
    }
  }
  return <>
    <PageHead eyebrow="YOUR ACCOUNT, CONNECTED" title="Your cases. In your conversation."
      description="Let a compatible AI chat app read case details while you keep control of every action." />
    <div className="guardrail-banner"><ShieldCheck size={24} /><div>
      <strong>Read-only, with your permission.</strong>
      <p>Connections can view the shared case queue, document checklists and existing drafts. They cannot draft, edit, approve, send or change settings.</p>
    </div></div>
    <ErrorBox message={actionError || error} />
    {notice && <p className="connections-notice" role="status">{notice}</p>}
    {!data ? !error && <Loading /> : <div className="connections-grid">
      <section className="panel connections-panel" aria-labelledby="connect-title">
        <div className="connections-title"><Link2 size={21} /><h2 id="connect-title">Connect your chat app</h2><Pill tone="green">Read-only</Pill></div>
        <p>Copy this connection address into a compatible app, then sign into Northgate and choose <strong>Allow read-only access</strong>. No API key is needed.</p>
        <div className="connections-endpoint"><code>{data.endpoint}</code><button className="icon-button" title="Copy connection address" aria-label="Copy connection address" onClick={async () => {
          try { await navigator.clipboard.writeText(data.endpoint); setNotice("Connection address copied."); }
          catch { setActionError("Copy is unavailable. Select and copy the connection address above."); }
        }}><Copy size={18} /></button></div>
        <h3>For personal Gemini chat</h3>
        <ol><li>Open Gemini in your browser and go to Settings → Connected Apps.</li>
          <li>Choose Add a custom app and paste the connection address.</li>
          <li>Follow the sign-in prompts and allow read-only access.</li>
          <li>Type @ in Gemini, select Northgate, and ask about a case.</li></ol>
        <p className="connections-note">Google currently documents this feature for US users aged 18+, in English, with Keep Activity enabled. Availability is controlled by Google. A localhost address is for local testing; Gemini needs a public HTTPS connection.</p>
        <a href="https://support.google.com/gemini/answer/17209137?hl=en" target="_blank" rel="noreferrer">Check Google's current availability and instructions ↗</a>
        <h3>Try asking</h3>
        <p>“List cases awaiting a reply.”<br />“What documents are missing for NG-2026-0843?”<br />“Show the existing draft for that case.”</p>
        <p className="connections-note">The portal currently shares its synthetic queue across operators. Connections see that same queue; cases are not individually assigned.</p>
      </section>
      <section className="panel connections-panel" aria-labelledby="connections-title">
        <div className="connections-title"><ShieldCheck size={21} /><h2 id="connections-title">Your connections</h2></div>
        <p>Connections last up to 30 days. Disconnect at any time to revoke access immediately.</p>
        {data.connections.length ? <ul className="connections-list">{data.connections.map(connection => <li key={connection.id}>
          <div><strong>{connection.client_name}</strong><small>Connected {new Date(connection.created_at).toLocaleDateString()} · Expires {new Date(connection.expires_at * 1000).toLocaleDateString()}</small></div>
          <button className="btn secondary" disabled={busy !== null} onClick={() => void disconnect(connection)}><Unplug size={16} />{busy === connection.id ? "Disconnecting…" : "Disconnect"}</button>
        </li>)}</ul> : <Empty title="No apps connected"><p>Your approved connections will appear here.</p></Empty>}
      </section>
    </div>}
  </>;
}

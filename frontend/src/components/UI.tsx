import { ReactNode, useEffect, useState } from "react";
import { LoaderCircle, ShieldCheck, ArrowUpRight } from "lucide-react";
export function Pill({
  children,
  tone = "muted",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={"pill " + tone}>{children}</span>;
}
export function PageHead({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-head">
      <div>
        <div className="eyebrow">
          {eyebrow}
          <span className="dot" /> SYNTHETIC NORTHGATE DATA
        </div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function Metric({
  label,
  value,
  note,
  tone = "",
}: {
  label: string;
  value: ReactNode;
  note: string;
  tone?: string;
}) {
  return (
    <div className="metric">
      <div className="metric-label">
        {label}
        <ArrowUpRight size={16} />
      </div>
      <div className={"metric-value " + tone}>{value}</div>
      <div className="metric-note">{note}</div>
    </div>
  );
}
export function Loading() {
  return (
    <div className="empty">
      <LoaderCircle className="spin" />
      <p>Loading workspace…</p>
    </div>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <ShieldCheck size={34} />
      <h3>{title}</h3>
      {children}
    </div>
  );
}
export function ErrorBox({ message }: { message: string }) {
  return message ? (
    <div role="alert" className="error">
      {message}
    </div>
  ) : null;
}
export function usePoll<T>(
  load: () => Promise<T>,
  deps: unknown[] = [],
  interval = 15000,
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const refresh = () =>
      load()
        .then((v) => {
          if (active) {
            setData(v);
            setError("");
          }
        })
        .catch((e) => active && setError(e.message));
    void refresh();
    const timer = setInterval(refresh, interval);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, deps);
  return { data, error, setData };
}

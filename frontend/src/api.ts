import { actionFeedback } from "./audio/sound";

export type Case = {
  id: string;
  company: string;
  jurisdiction: string;
  city: string;
  status: string;
  contact: string;
  missing_count: number;
  received_count: number;
  nudge_due: number;
  target_date: string;
  last_sent_at: string | null;
  draft_id: string | null;
  replied_at: string | null;
};
export type Doc = {
  id: string;
  name: string;
  status: string;
  received_at: string | null;
  source: string;
};
export type Checklist = {
  case: Case;
  revision: number;
  received: Doc[];
  missing: Doc[];
};
export type Scorecard = {
  zero_false_chases: boolean;
  all_missing_consolidated: boolean;
  no_prohibited_claims: boolean;
  valid_email: boolean;
  tone_score: number;
  policy_compliant: boolean;
  passed: boolean;
  feedback: string[];
  iterations: number;
};
export type Draft = {
  id: string;
  subject: string;
  body: string;
  status: string;
  provider: string;
  scorecard: Scorecard;
  requested_document_ids: string[];
};
export async function api<T = any>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const mutation =
    !!options.method && !["GET", "HEAD"].includes(options.method.toUpperCase());
  let response: Response;
  try {
    response = await fetch("/api" + path, {
      ...options,
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...options.headers },
    });
  } catch (error) {
    if (
      mutation &&
      !(error instanceof DOMException && error.name === "AbortError")
    )
      actionFeedback("notice");
    throw error;
  }
  const data = await response.json();
  if (!response.ok) {
    if (mutation) actionFeedback("notice");
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Request failed. Check your inputs.",
    );
  }
  if (mutation && path !== "/auth/logout" && !path.endsWith("/runs")) {
    actionFeedback(
      data.scorecard?.passed === false || data.passed === false
        ? "notice"
        : "success",
    );
  }
  return data;
}
export const post = <T = any>(path: string, body: unknown = {}) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const put = <T = any>(path: string, body: unknown) =>
  api<T>(path, { method: "PUT", body: JSON.stringify(body) });
export const label = (text: string) =>
  text
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
export const money = (value: number, currency = "GBP") =>
  new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency,
    minimumFractionDigits: 4,
    maximumFractionDigits: 4,
  }).format(value || 0);

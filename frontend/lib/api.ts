// Thin API client for the FastAPI backend.

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type LeadState = "PENDING" | "REACHED_OUT";

export interface Lead {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  resume_filename: string;
  resume_content_type: string;
  state: LeadState;
  created_at: string;
  updated_at: string;
}

export interface LeadList {
  items: Lead[];
  total: number;
  limit: number;
  offset: number;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) return data.detail.map((d: any) => d.msg).join(", ");
    return JSON.stringify(data);
  } catch {
    return res.statusText;
  }
}

// ---- Public ----

export async function submitLead(form: FormData): Promise<Lead> {
  const res = await fetch(`${API_URL}/api/leads`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  return res.json();
}

// ---- Auth ----

export async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  const data = await res.json();
  return data.access_token as string;
}

// ---- Authenticated ----

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export async function fetchLeads(
  token: string,
  opts: { state?: LeadState; limit?: number; offset?: number } = {}
): Promise<LeadList> {
  const params = new URLSearchParams();
  if (opts.state) params.set("state", opts.state);
  if (opts.limit != null) params.set("limit", String(opts.limit));
  if (opts.offset != null) params.set("offset", String(opts.offset));
  const res = await fetch(`${API_URL}/api/leads?${params.toString()}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  return res.json();
}

export async function markReachedOut(token: string, id: string): Promise<Lead> {
  const res = await fetch(`${API_URL}/api/leads/${id}`, {
    method: "PATCH",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ state: "REACHED_OUT" }),
  });
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  return res.json();
}

export function resumeDownloadUrl(id: string): string {
  return `${API_URL}/api/leads/${id}/resume`;
}

// Download the resume with the bearer token and trigger a browser save.
export async function downloadResume(
  token: string,
  lead: Lead
): Promise<void> {
  const res = await fetch(resumeDownloadUrl(lead.id), {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = lead.resume_filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

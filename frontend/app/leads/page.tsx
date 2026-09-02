"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Lead,
  LeadState,
  fetchLeads,
  markReachedOut,
  downloadResume,
  ApiError,
} from "@/lib/api";
import { getToken, clearToken } from "@/lib/auth";

type Filter = "ALL" | LeadState;

export default function LeadsDashboard() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<Filter>("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  // Guard: redirect to login if there's no token.
  useEffect(() => {
    const t = getToken();
    if (!t) {
      router.replace("/login");
      return;
    }
    setToken(t);
  }, [router]);

  const load = useCallback(
    async (activeToken: string, activeFilter: Filter) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetchLeads(activeToken, {
          state: activeFilter === "ALL" ? undefined : activeFilter,
          limit: 100,
        });
        setLeads(res.items);
        setTotal(res.total);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          clearToken();
          router.replace("/login");
          return;
        }
        setError(err instanceof ApiError ? err.message : "Failed to load leads.");
      } finally {
        setLoading(false);
      }
    },
    [router]
  );

  useEffect(() => {
    if (token) load(token, filter);
  }, [token, filter, load]);

  async function handleMark(lead: Lead) {
    if (!token) return;
    setBusyId(lead.id);
    setError(null);
    try {
      const updated = await markReachedOut(token, lead.id);
      setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDownload(lead: Lead) {
    if (!token) return;
    try {
      await downloadResume(token, lead);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Download failed.");
    }
  }

  function logout() {
    clearToken();
    router.replace("/login");
  }

  if (!token) return null;

  return (
    <div className="container">
      <div className="topbar">
        <div>
          <h1>Leads</h1>
          <p className="muted">{total} total</p>
        </div>
        <button className="secondary" onClick={logout}>
          Log out
        </button>
      </div>

      <div className="card">
        <div className="toolbar">
          <div className="filters">
            {(["ALL", "PENDING", "REACHED_OUT"] as Filter[]).map((f) => (
              <button
                key={f}
                className={filter === f ? "" : "secondary"}
                onClick={() => setFilter(f)}
              >
                {f === "ALL" ? "All" : f === "PENDING" ? "Pending" : "Reached out"}
              </button>
            ))}
          </div>
          <button
            className="secondary"
            onClick={() => token && load(token, filter)}
          >
            Refresh
          </button>
        </div>

        {error && <div className="alert error">{error}</div>}

        {loading ? (
          <p className="muted">Loading…</p>
        ) : leads.length === 0 ? (
          <p className="muted">No leads yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>State</th>
                <th>Submitted</th>
                <th>Resume</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id}>
                  <td>
                    {lead.first_name} {lead.last_name}
                  </td>
                  <td>{lead.email}</td>
                  <td>
                    <span className={`badge ${lead.state}`}>
                      {lead.state === "PENDING" ? "Pending" : "Reached out"}
                    </span>
                  </td>
                  <td className="muted">
                    {new Date(lead.created_at).toLocaleString()}
                  </td>
                  <td>
                    <button
                      className="linkbtn"
                      onClick={() => handleDownload(lead)}
                    >
                      {lead.resume_filename}
                    </button>
                  </td>
                  <td>
                    {lead.state === "PENDING" ? (
                      <button
                        onClick={() => handleMark(lead)}
                        disabled={busyId === lead.id}
                      >
                        {busyId === lead.id ? "…" : "Mark reached out"}
                      </button>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

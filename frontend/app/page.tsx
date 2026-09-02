"use client";

import { useState } from "react";
import Link from "next/link";
import { submitLead, ApiError } from "@/lib/api";

export default function PublicLeadForm() {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    const form = new FormData(e.currentTarget);
    try {
      await submitLead(form);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className="container narrow">
        <div className="card">
          <h1>Thank you! 🎉</h1>
          <p className="subtitle">
            Your submission has been received. An attorney will reach out to you
            shortly. A confirmation email is on its way.
          </p>
          <button className="secondary" onClick={() => setDone(false)}>
            Submit another
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container narrow">
      <div className="card">
        <div className="topbar">
          <h1>Get in touch</h1>
          <Link href="/login" className="muted">
            Staff login →
          </Link>
        </div>
        <p className="subtitle">
          Fill in your details and upload your resume / CV. Our team will be in
          touch.
        </p>

        {error && <div className="alert error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="first_name">First name</label>
            <input id="first_name" name="first_name" type="text" required />
          </div>
          <div className="field">
            <label htmlFor="last_name">Last name</label>
            <input id="last_name" name="last_name" type="text" required />
          </div>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" name="email" type="email" required />
          </div>
          <div className="field">
            <label htmlFor="resume">Resume / CV</label>
            <input
              id="resume"
              name="resume"
              type="file"
              accept=".pdf,.doc,.docx,.txt"
              required
            />
            <p className="muted">PDF, DOC, DOCX or TXT — up to 10 MB.</p>
          </div>
          <button type="submit" disabled={submitting}>
            {submitting ? "Submitting…" : "Submit"}
          </button>
        </form>
      </div>
    </div>
  );
}

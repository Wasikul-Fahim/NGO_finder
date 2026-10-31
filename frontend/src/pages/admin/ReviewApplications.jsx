import { useState } from "react";

import { reviewApplication, reviewQueue } from "../../api/opportunities";
import { parseError } from "../../api/client";
import { EmptyState, ErrorState, Loading } from "../../components/AsyncState";
import { ChipList, StatusPill } from "../../components/Chips";
import { inputClass, primaryButton, secondaryButton } from "../../components/FormField";
import useAsync from "../../hooks/useAsync";

const STATUSES = ["", "SUBMITTED", "UNDER_REVIEW", "ACCEPTED", "REJECTED"];
const NEXT = {
  SUBMITTED: [["UNDER_REVIEW", "Start review", true]],
  UNDER_REVIEW: [["ACCEPTED", "Accept", true], ["REJECTED", "Reject", false]],
  ACCEPTED: [],
  REJECTED: [],
};

export default function ReviewApplications() {
  const [status, setStatus] = useState("SUBMITTED");
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(
    () => reviewQueue({ page, page_size: 10, ...(status ? { status } : {}) }), [status, page]);
  const [notes, setNotes] = useState({});
  const [busy, setBusy] = useState(null);
  const [actionError, setActionError] = useState("");

  async function move(a, target) {
    setBusy(a.id);
    setActionError("");
    try { await reviewApplication(a.id, target, notes[a.id]); reload(); }
    catch (err) { setActionError(parseError(err).message); }
    finally { setBusy(null); }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-bold text-slate-900">Applications</h1>
        <select className={`${inputClass} !w-auto`} value={status} aria-label="Filter by status" onChange={(e) => { setPage(1); setStatus(e.target.value); }}>
          {STATUSES.map((s) => <option key={s} value={s}>{s ? s.replace("_", " ") : "All statuses"}</option>)}
        </select>
      </div>
      {actionError && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{actionError}</p>}
      {loading ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data.items.length === 0 ? (
        <EmptyState title="Nothing here" hint="No applications with this status." />
      ) : (
        <ul className="space-y-3">
          {data.items.map((a) => (
            <li key={a.id} className="surface-card space-y-3 p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h3 className="font-display text-base font-bold text-slate-900">{a.volunteer_name}</h3>
                  <p className="text-xs text-slate-500">for {a.opportunity_title}{a.volunteer_location ? ` · ${a.volunteer_location}` : ""}</p>
                </div>
                <StatusPill status={a.status} />
              </div>
              <ChipList items={a.volunteer_skills} tone="slate" />
              {NEXT[a.status].length > 0 && (
                <div className="flex flex-col gap-2 sm:flex-row">
                  <input className={inputClass} placeholder="Optional note to the volunteer" maxLength={500} value={notes[a.id] ?? ""} onChange={(e) => setNotes((n) => ({ ...n, [a.id]: e.target.value }))} />
                  {NEXT[a.status].map(([target, label, primary]) => (
                    <button key={target} className={`${primary ? primaryButton : secondaryButton} shrink-0`} disabled={busy === a.id} onClick={() => move(a, target)}>{label}</button>
                  ))}
                </div>
              )}
              {a.review_note && NEXT[a.status].length === 0 && <p className="text-xs text-slate-500">Note: {a.review_note}</p>}
            </li>
          ))}
        </ul>
      )}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button className={secondaryButton} disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
          <span className="text-xs font-bold text-slate-500">Page {data.page} of {data.pages}</span>
          <button className={secondaryButton} disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      )}
    </div>
  );
}

import { useState } from "react";

import { messageApplicant, reviewApplication, reviewQueue } from "../../api/opportunities";
import { parseError } from "../../api/client";
import { EmptyState, ErrorState, Loading } from "../../components/AsyncState";
import { ChipList, StatusPill } from "../../components/Chips";
import { inputClass, primaryButton, secondaryButton, textareaClass } from "../../components/FormField";
import useAsync from "../../hooks/useAsync";

const STATUSES = ["", "SUBMITTED", "UNDER_REVIEW", "ACCEPTED", "REJECTED"];
const NEXT = {
  SUBMITTED: [["UNDER_REVIEW", "Start review", true]],
  UNDER_REVIEW: [["ACCEPTED", "Accept", true], ["REJECTED", "Reject", false]],
  ACCEPTED: [],
  REJECTED: [],
};

function MessageBox({ application, onDone }) {
  const [text, setText] = useState("");
  const [state, setState] = useState({ busy: false, error: "", ok: "" });
  async function send(e) {
    e.preventDefault();
    setState({ busy: true, error: "", ok: "" });
    try {
      const r = await messageApplicant(application.id, text);
      setState({ busy: false, error: "", ok: r.sent ? "Message sent." : "That exact message is already waiting unread." });
      if (r.sent) setText("");
    } catch (err) { setState({ busy: false, error: parseError(err).message, ok: "" }); }
  }
  return (
    <form onSubmit={send} className="space-y-2 rounded-lg bg-slate-50 p-3">
      <textarea className={textareaClass} rows={3} maxLength={1000} required aria-label={`Message to ${application.volunteer_name}`}
        placeholder={`Write to ${application.volunteer_name}: interview time, next steps, questions…`} value={text} onChange={(e) => setText(e.target.value)} />
      <div className="flex flex-wrap items-center gap-3">
        <button className={primaryButton} disabled={state.busy || !text.trim()}>{state.busy ? "Sending…" : "Send message"}</button>
        <button type="button" className={secondaryButton} onClick={onDone}>Close</button>
        {state.ok && <span role="status" className="text-xs font-semibold text-emerald-700">{state.ok}</span>}
        {state.error && <span role="alert" className="text-xs font-semibold text-rose-600">{state.error}</span>}
      </div>
    </form>
  );
}

export default function ReviewApplications() {
  const [status, setStatus] = useState("SUBMITTED");
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(
    () => reviewQueue({ page, page_size: 10, ...(status ? { status } : {}) }), [status, page]);
  const [notes, setNotes] = useState({});
  const [busy, setBusy] = useState(null);
  const [messaging, setMessaging] = useState(null);
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
              <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs">
                <a className="font-bold text-purple-700 hover:text-purple-900" href={`mailto:${a.volunteer_email}`}>{a.volunteer_email}</a>
                {a.volunteer_phone && <a className="font-bold text-purple-700 hover:text-purple-900" href={`tel:${a.volunteer_phone}`}>{a.volunteer_phone}</a>}
                <button className="font-bold text-slate-600 hover:text-slate-900" onClick={() => setMessaging(messaging === a.id ? null : a.id)}>{messaging === a.id ? "Hide message box" : "Message in app"}</button>
              </div>
              {messaging === a.id && <MessageBox application={a} onDone={() => setMessaging(null)} />}
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

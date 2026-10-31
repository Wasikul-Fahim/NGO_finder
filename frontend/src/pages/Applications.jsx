import { useState } from "react";

import { parseError } from "../api/client";
import { myApplications, replyToNgo } from "../api/opportunities";
import { EmptyState, ErrorState, Loading } from "../components/AsyncState";
import { StatusPill } from "../components/Chips";
import { primaryButton, secondaryButton, textareaClass } from "../components/FormField";
import useAsync from "../hooks/useAsync";

function ReplyBox({ application }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [state, setState] = useState({ busy: false, ok: "", error: "" });
  async function send(e) {
    e.preventDefault();
    setState({ busy: true, ok: "", error: "" });
    try { const r = await replyToNgo(application.id, text); setState({ busy: false, ok: r.sent ? "Reply sent to the NGO." : "That reply is already waiting unread.", error: "" }); setText(""); }
    catch (err) { setState({ busy: false, ok: "", error: parseError(err).message }); }
  }
  if (!open) return <button className="text-xs font-bold text-purple-700 hover:text-purple-900" onClick={() => setOpen(true)}>Message the NGO</button>;
  return (
    <form onSubmit={send} className="mt-2 w-full space-y-2 rounded-lg bg-slate-50 p-3">
      <textarea className={textareaClass} rows={2} maxLength={1000} required placeholder="Write to the NGO about this application" value={text} onChange={(e) => setText(e.target.value)} />
      <div className="flex flex-wrap items-center gap-3">
        <button className={primaryButton} disabled={state.busy || !text.trim()}>Send</button>
        <button type="button" className={secondaryButton} onClick={() => setOpen(false)}>Close</button>
        {state.ok && <span role="status" className="text-xs font-semibold text-emerald-700">{state.ok}</span>}
        {state.error && <span role="alert" className="text-xs font-semibold text-rose-600">{state.error}</span>}
      </div>
    </form>
  );
}

export default function Applications() {
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(() => myApplications({ page, page_size: 10 }), [page]);
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <div className="space-y-5">
      <h1 className="font-display text-2xl font-bold text-slate-900">My applications</h1>
      {data.items.length === 0 ? (
        <EmptyState title="You haven't applied yet" hint="Find an opportunity that fits you and hit Apply." />
      ) : (
        <ul className="space-y-3">
          {data.items.map((a) => (
            <li key={a.id} className="surface-card flex flex-col gap-2 p-4 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
              <div>
                <h3 className="font-display text-base font-bold text-slate-900">{a.opportunity_title}</h3>
                <p className="text-xs text-slate-500">{a.ngo_name} · applied {new Date(a.application_date + "Z").toLocaleDateString()}</p>
                {a.review_note && <p className="mt-1 text-xs text-slate-600">Note from NGO: {a.review_note}</p>}
              </div>
              <StatusPill status={a.status} />
              <ReplyBox application={a} />
            </li>
          ))}
        </ul>
      )}
      {data.pages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button className={secondaryButton} disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
          <span className="text-xs font-bold text-slate-500">Page {data.page} of {data.pages}</span>
          <button className={secondaryButton} disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      )}
    </div>
  );
}

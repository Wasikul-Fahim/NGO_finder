import { CalendarDays, MapPin } from "lucide-react";
import { useState } from "react";

import { joinEvent, leaveEvent, listEvents, myEvents } from "../api/campaigns";
import { parseError } from "../api/client";
import { EmptyState, ErrorState, Loading } from "../components/AsyncState";
import { secondaryButton, primaryButton } from "../components/FormField";
import { ErrorNotice } from "../components/Notice";
import Pager from "../components/Pager";
import useAsync from "../hooks/useAsync";

const today = () => new Date().toISOString().slice(0, 10);

function EventCard({ event, onChange, setError }) {
  const [busy, setBusy] = useState(false);
  async function toggle() {
    setBusy(true); setError("");
    try { await (event.joined ? leaveEvent(event.id) : joinEvent(event.id)); onChange(); }
    catch (err) { setError(parseError(err).message); }
    finally { setBusy(false); }
  }
  return (
    <li className="surface-card flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-display text-base font-bold text-slate-900">{event.event_name}</h3>
          {event.joined && <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-extrabold uppercase text-emerald-700">On your roster</span>}
        </div>
        <p className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
          <span className="flex items-center gap-1"><CalendarDays size={13} />{event.event_date}{event.event_time ? ` · ${event.event_time.slice(0, 5)}` : ""}</span>
          {event.location && <span className="flex items-center gap-1"><MapPin size={13} />{event.location}</span>}
          <span>{event.campaign_title}</span>
        </p>
        {event.description && <p className="mt-1 text-sm text-slate-600">{event.description}</p>}
      </div>
      <button className={event.joined ? secondaryButton : primaryButton} disabled={busy} onClick={toggle}>{event.joined ? "Leave" : "Join event"}</button>
    </li>
  );
}

export default function Events() {
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const mine = useAsync(() => myEvents({ page_size: 50 }));
  const all = useAsync(() => listEvents({ upcoming: true, page, page_size: 10 }), [page]);
  const refresh = () => { mine.reload(); all.reload(); };
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-slate-900">Events</h1>
        <p className="mt-1 text-sm text-slate-500">Upcoming events. You can join events of NGOs that have accepted you; NGOs may also add you to their roster.</p>
      </div>
      <ErrorNotice>{error}</ErrorNotice>
      <section className="space-y-3">
        <h2 className="font-display text-lg font-bold text-slate-900">My events</h2>
        {mine.loading ? <Loading rows={1} /> : mine.error ? <ErrorState message={mine.error} onRetry={mine.reload} /> : mine.data.items.length === 0 ? (
          <EmptyState title="Nothing planned yet" hint="Join an event below to put it on your list." />
        ) : <ul className="space-y-3">{mine.data.items.map((e) => <EventCard key={e.id} event={e} onChange={refresh} setError={setError} />)}</ul>}
      </section>
      <section className="space-y-3">
        <h2 className="font-display text-lg font-bold text-slate-900">All upcoming events</h2>
        {all.loading ? <Loading /> : all.error ? <ErrorState message={all.error} onRetry={all.reload} /> : all.data.items.length === 0 ? (
          <EmptyState title="No upcoming events" />
        ) : <ul className="space-y-3">{all.data.items.map((e) => <EventCard key={e.id} event={e} onChange={refresh} setError={setError} />)}</ul>}
        <Pager data={all.data} page={page} onPage={setPage} />
      </section>
    </div>
  );
}

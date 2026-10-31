import { useState } from "react";

import { listCampaigns, listEvents } from "../../api/campaigns";
import { parseError } from "../../api/client";
import { listParticipation, recordAttendance, updateAttendance } from "../../api/impact";
import { reviewQueue } from "../../api/opportunities";
import { EmptyState, ErrorState, Loading } from "../../components/AsyncState";
import { inputClass, primaryButton, secondaryButton } from "../../components/FormField";
import { ErrorNotice, SuccessNotice } from "../../components/Notice";
import useAsync from "../../hooks/useAsync";

const today = () => new Date().toISOString().slice(0, 10);

function Roster({ event }) {
  const roster = useAsync(async () => {
    const [accepted, records] = await Promise.all([
      reviewQueue({ status: "ACCEPTED", page_size: 100 }),
      listParticipation({ event_id: event.id, page_size: 100 }),
    ]);
    const byVol = new Map(records.items.map((r) => [r.volunteer_id, r]));
    const seen = new Map();
    accepted.items.forEach((a) => seen.set(a.volunteer_id, a.volunteer_name));
    return [...seen].map(([id, name]) => ({ id, name, record: byVol.get(id) }));
  }, [event.id]);
  const [hours, setHours] = useState({});
  const [msg, setMsg] = useState({ ok: "", error: "" });
  const [busy, setBusy] = useState(null);

  if (roster.loading) return <Loading rows={2} />;
  if (roster.error) return <ErrorState message={roster.error} onRetry={roster.reload} />;
  if (roster.data.length === 0) return <EmptyState title="No eligible volunteers" hint="Volunteers must have an accepted application with your NGO." />;

  async function save(v, attendance) {
    setBusy(v.id); setMsg({ ok: "", error: "" });
    const h = attendance ? Number(hours[v.id] ?? v.record?.hours ?? 0) : 0;
    try {
      await (v.record ? updateAttendance(v.record.id, { attendance, hours: h }) : recordAttendance({ event_id: event.id, volunteer_id: v.id, attendance, hours: h }));
      setMsg({ ok: `Saved ${v.name}.`, error: "" });
      roster.reload();
    } catch (err) { setMsg({ ok: "", error: parseError(err).message }); }
    finally { setBusy(null); }
  }

  return (
    <div className="space-y-3">
      <SuccessNotice>{msg.ok}</SuccessNotice>
      <ErrorNotice>{msg.error}</ErrorNotice>
      <ul className="space-y-2">
        {roster.data.map((v) => (
          <li key={v.id} className="surface-card flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-bold text-slate-900">{v.name}</p>
              <p className="text-xs text-slate-500">{v.record ? (v.record.attendance ? `Present · ${v.record.hours} h` : "Absent") : "Not recorded"}</p>
            </div>
            <div className="flex items-center gap-2">
              <input className={`${inputClass} !w-24`} type="number" min="0" max="24" step="0.25" aria-label={`Hours for ${v.name}`} placeholder="Hours"
                value={hours[v.id] ?? v.record?.hours ?? ""} onChange={(e) => setHours((h) => ({ ...h, [v.id]: e.target.value }))} />
              <button className={primaryButton} disabled={busy === v.id} onClick={() => save(v, true)}>Present</button>
              <button className={secondaryButton} disabled={busy === v.id} onClick={() => save(v, false)}>Absent</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Attendance() {
  const events = useAsync(async () => {
    const [evts, own] = await Promise.all([
      listEvents({ to_date: today(), page_size: 100 }),
      listCampaigns({ mine: true, page_size: 100 }),
    ]);
    const ownIds = new Set(own.items.map((c) => c.id));
    return evts.items.filter((e) => ownIds.has(e.campaign_id));
  });
  const [eventId, setEventId] = useState("");
  if (events.loading) return <Loading />;
  if (events.error) return <ErrorState message={events.error} onRetry={events.reload} />;
  const past = [...events.data].reverse();
  const event = past.find((e) => String(e.id) === eventId);
  return (
    <div className="space-y-5">
      <h1 className="font-display text-2xl font-bold text-slate-900">Attendance</h1>
      <p className="text-sm text-slate-500">Pick an event that has already happened, then mark each accepted volunteer present (with hours) or absent.</p>
      <select className={inputClass} value={eventId} aria-label="Event" onChange={(e) => setEventId(e.target.value)}>
        <option value="">Choose an event…</option>
        {past.map((e) => <option key={e.id} value={e.id}>{e.event_date} — {e.event_name} ({e.campaign_title})</option>)}
      </select>
      {event ? <Roster event={event} /> : past.length === 0 && <EmptyState title="No past events" hint="Attendance can be recorded once an event date has passed." />}
    </div>
  );
}

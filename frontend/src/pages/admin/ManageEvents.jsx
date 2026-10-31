import { useState } from "react";

import { assignVolunteer, createEvent, deleteEvent, eventRoster, getMyNgo, listCampaigns, listEvents, removeFromRoster, updateEvent } from "../../api/campaigns";
import { reviewQueue } from "../../api/opportunities";
import { parseError } from "../../api/client";
import { sendEventReminder } from "../../api/notifications";
import { EmptyState, ErrorState, Loading } from "../../components/AsyncState";
import FormField, { inputClass, primaryButton, secondaryButton, textareaClass } from "../../components/FormField";
import useAsync from "../../hooks/useAsync";

function EventForm({ initial, campaigns, onSaved, onCancel }) {
  const [form, setForm] = useState(initial ? {
    campaign_id: initial.campaign_id, event_name: initial.event_name, event_date: initial.event_date,
    event_time: initial.event_time?.slice(0, 5) ?? "", location: initial.location ?? "", description: initial.description ?? "",
  } : { campaign_id: campaigns[0]?.id ?? "", event_name: "", event_date: "", event_time: "", location: "", description: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState({ message: "", fields: {} });
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setError({ message: "", fields: {} });
    const { campaign_id, ...rest } = form;
    const body = { ...rest, event_time: form.event_time || null, location: form.location || null, description: form.description || null };
    try {
      await (initial ? updateEvent(initial.id, body) : createEvent({ ...body, campaign_id: Number(campaign_id) }));
      onSaved();
    } catch (err) {
      setError(parseError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="surface-card space-y-4 p-5" noValidate>
      <h2 className="font-display text-lg font-bold text-slate-900">{initial ? "Edit event" : "New event"}</h2>
      {error.message && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{error.message}</p>}
      <FormField label="Campaign" error={error.fields.campaign_id}>
        <select className={inputClass} value={form.campaign_id} onChange={set("campaign_id")} disabled={!!initial}>
          {campaigns.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
        </select>
      </FormField>
      <FormField label="Event name" error={error.fields.event_name}><input className={inputClass} value={form.event_name} onChange={set("event_name")} required /></FormField>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Date" error={error.fields.event_date}><input className={inputClass} type="date" value={form.event_date} onChange={set("event_date")} required /></FormField>
        <FormField label="Time" error={error.fields.event_time}><input className={inputClass} type="time" value={form.event_time} onChange={set("event_time")} /></FormField>
      </div>
      <FormField label="Location" error={error.fields.location}><input className={inputClass} value={form.location} onChange={set("location")} /></FormField>
      <FormField label="Description" error={error.fields.description}><textarea className={textareaClass} rows={3} value={form.description} onChange={set("description")} /></FormField>
      <div className="flex gap-3">
        <button className={primaryButton} disabled={saving}>{saving ? "Saving…" : "Save event"}</button>
        <button type="button" className={secondaryButton} onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

function RosterPanel({ event }) {
  const roster = useAsync(async () => {
    const [list, accepted] = await Promise.all([eventRoster(event.id), reviewQueue({ status: "ACCEPTED", page_size: 100 })]);
    const names = new Map(accepted.items.map((a) => [a.volunteer_id, a.volunteer_name]));
    return { list, candidates: [...names].map(([id, name]) => ({ id, name })).filter((c) => !list.some((r) => r.volunteer_id === c.id)) };
  }, [event.id]);
  const [pick, setPick] = useState("");
  const [error, setError] = useState("");
  if (roster.loading) return <Loading rows={1} />;
  if (roster.error) return <ErrorState message={roster.error} onRetry={roster.reload} />;
  const run = async (fn) => { setError(""); try { await fn(); setPick(""); roster.reload(); } catch (err) { setError(parseError(err).message); } };
  return (
    <div className="mt-3 w-full space-y-2 rounded-lg bg-slate-50 p-3">
      <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Roster ({roster.data.list.length})</p>
      {error && <p role="alert" className="text-xs font-semibold text-rose-600">{error}</p>}
      {roster.data.list.length === 0 ? <p className="text-sm text-slate-500">Nobody yet.</p> : (
        <ul className="divide-y divide-slate-200">
          {roster.data.list.map((r) => (
            <li key={r.volunteer_id} className="flex items-center justify-between py-1.5 text-sm">
              <span className="font-semibold text-slate-800">{r.volunteer_name} <span className="text-[10px] font-bold uppercase text-slate-400">{r.assigned_by === "SELF" ? "joined" : "assigned"}</span></span>
              <button className="text-xs font-bold text-rose-600" onClick={() => run(() => removeFromRoster(event.id, r.volunteer_id))}>Remove</button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <select className={inputClass} aria-label="Add volunteer" value={pick} onChange={(e) => setPick(e.target.value)}>
          <option value="">{roster.data.candidates.length ? "Add an accepted volunteer…" : "No more accepted volunteers"}</option>
          {roster.data.candidates.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <button className={primaryButton} disabled={!pick} onClick={() => run(() => assignVolunteer(event.id, Number(pick)))}>Add</button>
      </div>
    </div>
  );
}

export default function ManageEvents() {
  const ngo = useAsync(getMyNgo);
  const campaigns = useAsync(() => listCampaigns({ mine: true, page_size: 100 }));
  const events = useAsync(() => listEvents({ page_size: 100 }));
  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");
  const [rosterFor, setRosterFor] = useState(null);

  if (ngo.loading || campaigns.loading || events.loading) return <Loading />;
  const error = ngo.error || campaigns.error || events.error;
  if (error) return <ErrorState message={error} onRetry={() => { ngo.reload(); campaigns.reload(); events.reload(); }} />;

  const verified = ngo.data.verification_status === "VERIFIED";
  // Only open campaigns accept event changes (server enforces this too).
  const open = campaigns.data.items.filter((c) => ["DRAFT", "ACTIVE"].includes(c.status));
  const ownIds = new Set(campaigns.data.items.map((c) => c.id));
  const mine = events.data.items.filter((e) => ownIds.has(e.campaign_id));
  const openIds = new Set(open.map((c) => c.id));

  async function remind(event) {
    setActionError("");
    try {
      const r = await sendEventReminder(event.id);
      setActionError("");
      window.alert(r.audience_size === 0 ? "No accepted volunteers to remind yet." : r.recipients === 0 ? "Everyone has already been reminded." : `Reminder sent to ${r.recipients} volunteer(s).`);
    } catch (err) { setActionError(parseError(err).message); }
  }

  async function remove(event) {
    if (!window.confirm(`Delete "${event.event_name}"?`)) return;
    setActionError("");
    try { await deleteEvent(event.id); events.reload(); } catch (err) { setActionError(parseError(err).message); }
  }

  if (editing) {
    return <EventForm initial={editing === "new" ? null : editing} campaigns={open} onCancel={() => setEditing(null)} onSaved={() => { setEditing(null); events.reload(); }} />;
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-bold text-slate-900">Events</h1>
        <button className={primaryButton} disabled={!verified || open.length === 0} onClick={() => setEditing("new")}>New event</button>
      </div>
      {verified && open.length === 0 && <p className="rounded-lg bg-amber-50 px-3 py-2.5 text-sm text-amber-800">Create a draft or active campaign first; events belong to a campaign.</p>}
      {!verified && <p className="rounded-lg bg-amber-50 px-3 py-2.5 text-sm text-amber-800">Events can be created once your organisation is verified.</p>}
      {actionError && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{actionError}</p>}
      {mine.length === 0 ? (
        <EmptyState title="No events yet" hint="Schedule an event to give volunteers something to show up for." />
      ) : (
        <ul className="space-y-3">
          {mine.map((e) => (
            <li key={e.id} className="surface-card flex flex-col gap-3 p-4 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
              <div className="min-w-0">
                <h3 className="truncate font-display text-base font-bold text-slate-900">{e.event_name}</h3>
                <p className="mt-1 text-xs text-slate-500">{e.campaign_title} · {e.event_date}{e.event_time ? ` ${e.event_time.slice(0, 5)}` : ""}{e.location ? ` · ${e.location}` : ""}</p>
              </div>
              {openIds.has(e.campaign_id) && verified && (
                <div className="flex gap-2">
                  {e.event_date >= new Date().toISOString().slice(0, 10) && <button className={secondaryButton} onClick={() => setRosterFor(rosterFor === e.id ? null : e.id)}>Roster</button>}
                  {e.event_date >= new Date().toISOString().slice(0, 10) && <button className={secondaryButton} onClick={() => remind(e)}>Remind volunteers</button>}
                  <button className={secondaryButton} onClick={() => setEditing(e)}>Edit</button>
                  <button className={secondaryButton} onClick={() => remove(e)}>Delete</button>
                </div>
              )}
              {rosterFor === e.id && <RosterPanel event={e} />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

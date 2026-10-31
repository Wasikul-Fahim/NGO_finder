import { useState } from "react";

import { archiveCampaign, changeCampaignStatus, createCampaign, getMyNgo, listCampaigns, updateCampaign } from "../../api/campaigns";
import { parseError } from "../../api/client";
import { EmptyState, ErrorState, Loading } from "../../components/AsyncState";
import FormField, { inputClass, primaryButton, secondaryButton, textareaClass } from "../../components/FormField";
import useAsync from "../../hooks/useAsync";

const STATUS_STYLE = {
  DRAFT: "bg-slate-100 text-slate-600",
  ACTIVE: "bg-emerald-50 text-emerald-700",
  COMPLETED: "bg-blue-50 text-blue-700",
  ARCHIVED: "bg-slate-100 text-slate-400",
};
// Mirrors the server state machine; the server remains the authority (409 on anything else).
const NEXT_ACTIONS = {
  DRAFT: [["ACTIVE", "Publish"]],
  ACTIVE: [["COMPLETED", "Mark completed"]],
  COMPLETED: [],
  ARCHIVED: [],
};
const EMPTY = { title: "", description: "", location: "", start_date: "", end_date: "", required_volunteers: 0, donation_goal: "", is_emergency: false, publish: false };

function CampaignForm({ initial, onSaved, onCancel }) {
  const [form, setForm] = useState(initial ? {
    title: initial.title, description: initial.description ?? "", location: initial.location ?? "",
    start_date: initial.start_date, end_date: initial.end_date, required_volunteers: initial.required_volunteers,
    donation_goal: initial.donation_goal ?? "", is_emergency: initial.is_emergency, publish: false,
  } : EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState({ message: "", fields: {} });
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setError({ message: "", fields: {} });
    const { publish, ...rest } = form;
    const body = {
      ...rest, description: form.description || null, location: form.location || null,
      required_volunteers: Number(form.required_volunteers) || 0,
      donation_goal: form.donation_goal === "" ? null : Number(form.donation_goal),
      ...(initial ? {} : { status: publish ? "ACTIVE" : "DRAFT" }),
    };
    try {
      await (initial ? updateCampaign(initial.id, body) : createCampaign(body));
      onSaved();
    } catch (err) {
      setError(parseError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="surface-card space-y-4 p-5" noValidate>
      <h2 className="font-display text-lg font-bold text-slate-900">{initial ? "Edit campaign" : "New campaign"}</h2>
      {error.message && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{error.message}</p>}
      <FormField label="Title" error={error.fields.title}><input className={inputClass} value={form.title} onChange={set("title")} required /></FormField>
      <FormField label="Description" error={error.fields.description}><textarea className={textareaClass} rows={3} value={form.description} onChange={set("description")} /></FormField>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Location" error={error.fields.location}><input className={inputClass} value={form.location} onChange={set("location")} /></FormField>
        <FormField label="Volunteers needed" error={error.fields.required_volunteers}><input className={inputClass} type="number" min="0" value={form.required_volunteers} onChange={set("required_volunteers")} /></FormField>
        <FormField label="Start date" error={error.fields.start_date}><input className={inputClass} type="date" value={form.start_date} onChange={set("start_date")} required /></FormField>
        <FormField label="End date" error={error.fields.end_date}><input className={inputClass} type="date" value={form.end_date} onChange={set("end_date")} required /></FormField>
      </div>
      <FormField label="Donation goal (৳, optional)" error={error.fields.donation_goal}><input className={inputClass} type="number" min="0" step="0.01" value={form.donation_goal} onChange={set("donation_goal")} /></FormField>
      <label className="flex items-center gap-2 text-sm font-semibold text-slate-700"><input type="checkbox" checked={form.is_emergency} onChange={(e) => setForm((f) => ({ ...f, is_emergency: e.target.checked }))} /> Emergency relief campaign (shown first, with an emergency badge)</label>
      {!initial && <label className="flex items-center gap-2 text-sm font-semibold text-slate-700"><input type="checkbox" checked={form.publish} onChange={(e) => setForm((f) => ({ ...f, publish: e.target.checked }))} /> Publish immediately (otherwise it is saved as a draft)</label>}
      <div className="flex gap-3">
        <button className={primaryButton} disabled={saving}>{saving ? "Saving…" : "Save campaign"}</button>
        <button type="button" className={secondaryButton} onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

export default function ManageCampaigns() {
  const ngo = useAsync(getMyNgo);
  const { data, loading, error, reload } = useAsync(() => listCampaigns({ mine: true, page_size: 100 }));
  const [editing, setEditing] = useState(null); // null | "new" | campaign
  const [actionError, setActionError] = useState("");

  if (ngo.loading || loading) return <Loading />;
  if (error || ngo.error) return <ErrorState message={error || ngo.error} onRetry={() => { ngo.reload(); reload(); }} />;

  const verified = ngo.data.verification_status === "VERIFIED";

  async function act(promise) {
    setActionError("");
    try { await promise; reload(); } catch (err) { setActionError(parseError(err).message); }
  }

  if (editing) {
    return <CampaignForm initial={editing === "new" ? null : editing} onCancel={() => setEditing(null)} onSaved={() => { setEditing(null); reload(); }} />;
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-bold text-slate-900">Campaigns</h1>
        <button className={primaryButton} disabled={!verified} onClick={() => setEditing("new")}>New campaign</button>
      </div>
      {!verified && <p className="rounded-lg bg-amber-50 px-3 py-2.5 text-sm text-amber-800">Campaigns can be created once your organisation is verified.</p>}
      {actionError && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{actionError}</p>}
      {data.items.length === 0 ? (
        <EmptyState title="No campaigns yet" hint="Create your first campaign to start recruiting volunteers." />
      ) : (
        <ul className="space-y-3">
          {data.items.map((c) => (
            <li key={c.id} className="surface-card flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="truncate font-display text-base font-bold text-slate-900">{c.title}</h3>
                  {c.is_emergency && <span className="rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-extrabold uppercase text-rose-600">Emergency</span>}
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-extrabold uppercase ${STATUS_STYLE[c.status]}`}>{c.status}</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">{c.location || "Anywhere"} · {c.start_date} → {c.end_date} · {c.required_volunteers} volunteers</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {NEXT_ACTIONS[c.status].map(([status, label]) => (
                  <button key={status} disabled={!verified} className={secondaryButton} onClick={() => act(changeCampaignStatus(c.id, status))}>{label}</button>
                ))}
                {!["COMPLETED", "ARCHIVED"].includes(c.status) && <button disabled={!verified} className={secondaryButton} onClick={() => setEditing(c)}>Edit</button>}
                {c.status !== "ARCHIVED" && (
                  <button disabled={!verified} className={secondaryButton} onClick={() => window.confirm(`Archive "${c.title}"?`) && act(archiveCampaign(c.id))}>Archive</button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

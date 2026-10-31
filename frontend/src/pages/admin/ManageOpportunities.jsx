import { useState } from "react";

import { listCampaigns } from "../../api/campaigns";
import { createOpportunity, deactivateOpportunity, listOpportunities, updateOpportunity } from "../../api/opportunities";
import { parseError } from "../../api/client";
import { EmptyState, ErrorState, Loading } from "../../components/AsyncState";
import { ChipList, DayPicker, toList } from "../../components/Chips";
import FormField, { inputClass, primaryButton, secondaryButton, textareaClass } from "../../components/FormField";
import useAsync from "../../hooks/useAsync";

function OpportunityForm({ initial, campaigns, onSaved, onCancel }) {
  const [form, setForm] = useState({
    title: initial?.title ?? "", description: initial?.description ?? "", location: initial?.location ?? "",
    campaign_id: initial?.campaign_id ?? "", skills: (initial?.required_skills ?? []).join(", "),
    interests: (initial?.interests ?? []).join(", "), availability: initial?.availability ?? [],
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState({ message: "", fields: {} });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setError({ message: "", fields: {} });
    const body = {
      title: form.title, description: form.description || null, location: form.location || null,
      campaign_id: form.campaign_id ? Number(form.campaign_id) : null,
      required_skills: toList(form.skills), interests: toList(form.interests), availability: form.availability,
    };
    try { await (initial ? updateOpportunity(initial.id, body) : createOpportunity(body)); onSaved(); }
    catch (err) { setError(parseError(err)); }
    finally { setSaving(false); }
  }

  return (
    <form onSubmit={submit} className="surface-card space-y-4 p-5" noValidate>
      <h2 className="font-display text-lg font-bold text-slate-900">{initial ? "Edit opportunity" : "New opportunity"}</h2>
      {error.message && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{error.message}</p>}
      <FormField label="Title" error={error.fields.title}><input className={inputClass} value={form.title} onChange={set("title")} required /></FormField>
      <FormField label="Description" error={error.fields.description}><textarea className={textareaClass} rows={3} value={form.description} onChange={set("description")} /></FormField>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Location (City, Region)" error={error.fields.location}><input className={inputClass} placeholder="Dhaka, Dhaka" value={form.location} onChange={set("location")} /></FormField>
        <FormField label="Campaign (optional)" error={error.fields.campaign_id}>
          <select className={inputClass} value={form.campaign_id} onChange={set("campaign_id")}>
            <option value="">— none —</option>
            {campaigns.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
        </FormField>
        <FormField label="Required skills (comma separated)" error={error.fields.required_skills}><input className={inputClass} value={form.skills} onChange={set("skills")} /></FormField>
        <FormField label="Interests (comma separated)" error={error.fields.interests}><input className={inputClass} value={form.interests} onChange={set("interests")} /></FormField>
      </div>
      <div>
        <span className="mb-1.5 block text-xs font-bold text-slate-700">Days needed</span>
        <DayPicker value={form.availability} onChange={(availability) => setForm((f) => ({ ...f, availability }))} />
        {error.fields.availability && <span role="alert" className="mt-1 block text-xs font-semibold text-rose-600">{error.fields.availability}</span>}
      </div>
      <div className="flex gap-3">
        <button className={primaryButton} disabled={saving}>{saving ? "Saving…" : "Save opportunity"}</button>
        <button type="button" className={secondaryButton} onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

export default function ManageOpportunities() {
  const opps = useAsync(() => listOpportunities({ mine: true, page_size: 100 }));
  const campaigns = useAsync(() => listCampaigns({ mine: true, page_size: 100 }));
  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  if (opps.loading || campaigns.loading) return <Loading />;
  const error = opps.error || campaigns.error;
  if (error) return <ErrorState message={error} onRetry={() => { opps.reload(); campaigns.reload(); }} />;

  const openCampaigns = campaigns.data.items.filter((c) => ["DRAFT", "ACTIVE"].includes(c.status));

  async function act(promise) {
    setActionError("");
    try { await promise; opps.reload(); } catch (err) { setActionError(parseError(err).message); }
  }

  if (editing) {
    return <OpportunityForm initial={editing === "new" ? null : editing} campaigns={openCampaigns} onCancel={() => setEditing(null)} onSaved={() => { setEditing(null); opps.reload(); }} />;
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-bold text-slate-900">Opportunities</h1>
        <button className={primaryButton} onClick={() => setEditing("new")}>New opportunity</button>
      </div>
      {actionError && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{actionError}</p>}
      {opps.data.items.length === 0 ? (
        <EmptyState title="No opportunities yet" hint="Post a role so volunteers can find and apply to it." />
      ) : (
        <ul className="space-y-3">
          {opps.data.items.map((o) => (
            <li key={o.id} className="surface-card flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 space-y-1.5">
                <div className="flex items-center gap-2">
                  <h3 className="truncate font-display text-base font-bold text-slate-900">{o.title}</h3>
                  {!o.is_active && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-extrabold uppercase text-slate-500">Inactive</span>}
                </div>
                <p className="text-xs text-slate-500">{o.location || "Anywhere"}{o.campaign_title ? ` · ${o.campaign_title}` : ""}</p>
                <ChipList items={o.required_skills} />
              </div>
              <div className="flex gap-2">
                <button className={secondaryButton} onClick={() => setEditing(o)}>Edit</button>
                {o.is_active
                  ? <button className={secondaryButton} onClick={() => window.confirm(`Close "${o.title}" to new applicants?`) && act(deactivateOpportunity(o.id))}>Close</button>
                  : <button className={secondaryButton} onClick={() => act(updateOpportunity(o.id, { is_active: true }))}>Reopen</button>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

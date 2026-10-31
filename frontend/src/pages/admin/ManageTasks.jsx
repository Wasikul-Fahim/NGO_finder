import { useState } from "react";

import { listCampaigns } from "../../api/campaigns";
import { assignTask, createTask, listTasks, reviewQueue } from "../../api/opportunities";
import { parseError } from "../../api/client";
import { EmptyState, ErrorState, Loading } from "../../components/AsyncState";
import { StatusPill } from "../../components/Chips";
import FormField, { inputClass, primaryButton, secondaryButton, textareaClass } from "../../components/FormField";
import useAsync from "../../hooks/useAsync";

/** Volunteers this NGO has accepted: the only people a task can be assigned to. */
function useEligible() {
  return useAsync(async () => {
    const page = await reviewQueue({ status: "ACCEPTED", page_size: 100 });
    const seen = new Map();
    page.items.forEach((a) => seen.set(a.volunteer_id, a.volunteer_name));
    return [...seen].map(([id, name]) => ({ id, name }));
  });
}

function TaskForm({ campaigns, eligible, onSaved, onCancel }) {
  const [form, setForm] = useState({ campaign_id: campaigns[0]?.id ?? "", task_name: "", description: "", deadline: "", volunteer_id: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState({ message: "", fields: {} });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setError({ message: "", fields: {} });
    try {
      await createTask({
        campaign_id: Number(form.campaign_id), task_name: form.task_name, description: form.description || null,
        deadline: form.deadline || null, volunteer_id: form.volunteer_id ? Number(form.volunteer_id) : null,
      });
      onSaved();
    } catch (err) { setError(parseError(err)); }
    finally { setSaving(false); }
  }

  return (
    <form onSubmit={submit} className="surface-card space-y-4 p-5" noValidate>
      <h2 className="font-display text-lg font-bold text-slate-900">New task</h2>
      {error.message && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{error.message}</p>}
      <FormField label="Campaign" error={error.fields.campaign_id}>
        <select className={inputClass} value={form.campaign_id} onChange={set("campaign_id")}>
          {campaigns.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
        </select>
      </FormField>
      <FormField label="Task name" error={error.fields.task_name}><input className={inputClass} value={form.task_name} onChange={set("task_name")} required /></FormField>
      <FormField label="Description" error={error.fields.description}><textarea className={textareaClass} rows={3} value={form.description} onChange={set("description")} /></FormField>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Deadline" error={error.fields.deadline}><input className={inputClass} type="date" value={form.deadline} onChange={set("deadline")} /></FormField>
        <FormField label="Assign to (optional)" error={error.fields.volunteer_id}>
          <select className={inputClass} value={form.volunteer_id} onChange={set("volunteer_id")}>
            <option value="">— assign later —</option>
            {eligible.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select>
        </FormField>
      </div>
      {eligible.length === 0 && <p className="text-xs text-slate-500">No volunteers can be assigned yet: accept an application first.</p>}
      <div className="flex gap-3">
        <button className={primaryButton} disabled={saving}>{saving ? "Saving…" : "Create task"}</button>
        <button type="button" className={secondaryButton} onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

export default function ManageTasks() {
  const tasks = useAsync(() => listTasks({ page_size: 100 }));
  const campaigns = useAsync(() => listCampaigns({ mine: true, page_size: 100 }));
  const eligible = useEligible();
  const [creating, setCreating] = useState(false);
  const [actionError, setActionError] = useState("");

  if (tasks.loading || campaigns.loading || eligible.loading) return <Loading />;
  const error = tasks.error || campaigns.error || eligible.error;
  if (error) return <ErrorState message={error} onRetry={() => { tasks.reload(); campaigns.reload(); eligible.reload(); }} />;

  const open = campaigns.data.items.filter((c) => ["DRAFT", "ACTIVE"].includes(c.status));

  async function assign(task, volunteerId) {
    if (!volunteerId) return;
    setActionError("");
    try { await assignTask(task.id, Number(volunteerId)); tasks.reload(); }
    catch (err) { setActionError(parseError(err).message); }
  }

  if (creating) return <TaskForm campaigns={open} eligible={eligible.data} onCancel={() => setCreating(false)} onSaved={() => { setCreating(false); tasks.reload(); }} />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-bold text-slate-900">Tasks</h1>
        <button className={primaryButton} disabled={open.length === 0} onClick={() => setCreating(true)}>New task</button>
      </div>
      {open.length === 0 && <p className="rounded-lg bg-amber-50 px-3 py-2.5 text-sm text-amber-800">Create a draft or active campaign first; tasks belong to a campaign.</p>}
      {actionError && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{actionError}</p>}
      {tasks.data.items.length === 0 ? (
        <EmptyState title="No tasks yet" hint="Create a task and assign it to a volunteer you've accepted." />
      ) : (
        <ul className="space-y-3">
          {tasks.data.items.map((t) => (
            <li key={t.id} className="surface-card flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-display text-base font-bold text-slate-900">{t.task_name}</h3>
                  <StatusPill status={t.status} />
                </div>
                <p className="mt-1 text-xs text-slate-500">{t.campaign_title}{t.deadline ? ` · due ${t.deadline}` : ""} · {t.volunteer_name ? `assigned to ${t.volunteer_name}` : "unassigned"}</p>
              </div>
              {["PENDING", "DECLINED"].includes(t.status) && eligible.data.length > 0 && (
                <select className={`${inputClass} !w-auto`} aria-label={`Assign ${t.task_name}`} value="" onChange={(e) => assign(t, e.target.value)}>
                  <option value="">{t.volunteer_name ? "Reassign…" : "Assign…"}</option>
                  {eligible.data.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
                </select>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

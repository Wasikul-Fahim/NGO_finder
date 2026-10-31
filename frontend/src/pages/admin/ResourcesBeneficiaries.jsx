import { useState } from "react";

import { listCampaigns } from "../../api/campaigns";
import { parseError } from "../../api/client";
import { addResource, deleteResource, distribute, enrollBeneficiary, listBeneficiaries, listResources, setSupportStatus } from "../../api/impact";
import { EmptyState, ErrorState, Loading } from "../../components/AsyncState";
import { StatusPill } from "../../components/Chips";
import FormField, { inputClass, primaryButton, secondaryButton } from "../../components/FormField";
import { ErrorNotice, SuccessNotice } from "../../components/Notice";
import useAsync from "../../hooks/useAsync";

function Resources({ campaign, beneficiaries }) {
  const resources = useAsync(() => listResources(campaign.id), [campaign.id]);
  const [form, setForm] = useState({ name: "", quantity_total: "", unit: "" });
  const [dist, setDist] = useState({});
  const [msg, setMsg] = useState({ ok: "", error: "" });
  const run = async (fn, ok) => {
    setMsg({ ok: "", error: "" });
    try { await fn(); setMsg({ ok, error: "" }); resources.reload(); } catch (err) { setMsg({ ok: "", error: parseError(err).message }); }
  };
  if (resources.loading) return <Loading rows={2} />;
  if (resources.error) return <ErrorState message={resources.error} onRetry={resources.reload} />;
  return (
    <section className="space-y-3">
      <h2 className="font-display text-lg font-bold text-slate-900">Resources</h2>
      <SuccessNotice>{msg.ok}</SuccessNotice><ErrorNotice>{msg.error}</ErrorNotice>
      <form className="surface-card grid gap-3 p-4 sm:grid-cols-4" onSubmit={(e) => { e.preventDefault(); run(async () => { await addResource(campaign.id, { name: form.name, quantity_total: Number(form.quantity_total), unit: form.unit || null }); setForm({ name: "", quantity_total: "", unit: "" }); }, "Resource added."); }}>
        <input className={inputClass} placeholder="Name (e.g. Rice)" aria-label="Resource name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <input className={inputClass} type="number" min="0" placeholder="Total quantity" aria-label="Total quantity" value={form.quantity_total} onChange={(e) => setForm({ ...form, quantity_total: e.target.value })} required />
        <input className={inputClass} placeholder="Unit (kg, pcs)" aria-label="Unit" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
        <button className={primaryButton}>Add resource</button>
      </form>
      {resources.data.length === 0 ? <EmptyState title="No resources tracked" hint="Add the supplies this campaign will hand out." /> : (
        <ul className="space-y-2">
          {resources.data.map((r) => (
            <li key={r.id} className="surface-card space-y-2 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm font-bold text-slate-900"><span>{r.name}</span><span className="flex items-center gap-3">{r.quantity_allocated} / {r.quantity_total} {r.unit} given out · {r.quantity_remaining} left{r.quantity_allocated === 0 && <button className="text-xs font-bold text-rose-600" onClick={() => window.confirm(`Delete "${r.name}"?`) && run(() => deleteResource(r.id), "Resource deleted.")}>Delete</button>}</span></div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${r.quantity_total ? (r.quantity_allocated / r.quantity_total) * 100 : 0}%` }} /></div>
              {beneficiaries.length > 0 && r.quantity_remaining > 0 && (
                <form className="flex flex-col gap-2 sm:flex-row" onSubmit={(e) => { e.preventDefault(); const d = dist[r.id] || {}; run(async () => { await distribute(r.id, { beneficiary_id: Number(d.beneficiary_id), quantity: Number(d.quantity) }); setDist({ ...dist, [r.id]: {} }); }, "Distribution recorded."); }}>
                  <select className={inputClass} aria-label={`Recipient for ${r.name}`} value={dist[r.id]?.beneficiary_id ?? ""} onChange={(e) => setDist({ ...dist, [r.id]: { ...dist[r.id], beneficiary_id: e.target.value } })} required>
                    <option value="">Give to…</option>{beneficiaries.map((b) => <option key={b.beneficiary_id} value={b.beneficiary_id}>{b.name}</option>)}
                  </select>
                  <input className={`${inputClass} sm:!w-32`} type="number" min="1" max={r.quantity_remaining} placeholder="Qty" aria-label={`Quantity of ${r.name}`} value={dist[r.id]?.quantity ?? ""} onChange={(e) => setDist({ ...dist, [r.id]: { ...dist[r.id], quantity: e.target.value } })} required />
                  <button className={secondaryButton}>Distribute</button>
                </form>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Beneficiaries({ campaign, list }) {
  const [form, setForm] = useState({ email: "", name: "", location: "", required_assistance: "" });
  const [msg, setMsg] = useState({ ok: "", error: "" });
  async function enrol(e) {
    e.preventDefault();
    setMsg({ ok: "", error: "" });
    const body = form.email ? { email: form.email } : { name: form.name, location: form.location || null, required_assistance: form.required_assistance || null };
    try { await enrollBeneficiary(campaign.id, body); setForm({ email: "", name: "", location: "", required_assistance: "" }); setMsg({ ok: "Enrolled.", error: "" }); list.reload(); }
    catch (err) { setMsg({ ok: "", error: parseError(err).message }); }
  }
  async function status(b, s) {
    setMsg({ ok: "", error: "" });
    try { await setSupportStatus(campaign.id, b.beneficiary_id, s); list.reload(); } catch (err) { setMsg({ ok: "", error: parseError(err).message }); }
  }
  return (
    <section className="space-y-3">
      <h2 className="font-display text-lg font-bold text-slate-900">Beneficiaries</h2>
      <p className="text-xs text-slate-500">Only your NGO can see these people. Enrol a registered beneficiary by email, or record someone new.</p>
      <SuccessNotice>{msg.ok}</SuccessNotice><ErrorNotice>{msg.error}</ErrorNotice>
      <form onSubmit={enrol} className="surface-card grid gap-3 p-4 sm:grid-cols-2" noValidate>
        <FormField label="Registered beneficiary's email"><input className={inputClass} type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></FormField>
        <div className="grid gap-3 sm:col-span-1">
          <FormField label="…or new person's name"><input className={inputClass} disabled={!!form.email} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></FormField>
        </div>
        <FormField label="Location"><input className={inputClass} disabled={!!form.email} value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} /></FormField>
        <FormField label="Assistance needed"><input className={inputClass} disabled={!!form.email} value={form.required_assistance} onChange={(e) => setForm({ ...form, required_assistance: e.target.value })} /></FormField>
        <button className={`${primaryButton} sm:col-span-2`}>Enrol</button>
      </form>
      {list.loading ? <Loading rows={2} /> : list.error ? <ErrorState message={list.error} onRetry={list.reload} /> : list.data.length === 0 ? <EmptyState title="Nobody enrolled yet" /> : (
        <ul className="space-y-2">
          {list.data.map((b) => (
            <li key={b.beneficiary_id} className="surface-card flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div><p className="font-bold text-slate-900">{b.name}</p><p className="text-xs text-slate-500">{[b.location, b.required_assistance].filter(Boolean).join(" · ") || "No details"}</p></div>
              <div className="flex items-center gap-2"><StatusPill status={b.support_status} />
                <select className={`${inputClass} !w-auto`} aria-label={`Status for ${b.name}`} value={b.support_status} onChange={(e) => status(b, e.target.value)}>
                  <option>PENDING</option><option>ACTIVE</option><option>COMPLETED</option>
                </select></div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function ResourcesBeneficiaries() {
  const campaigns = useAsync(() => listCampaigns({ mine: true, page_size: 100 }));
  const [cid, setCid] = useState("");
  const list = useAsync(() => (cid ? listBeneficiaries(cid) : Promise.resolve([])), [cid]);
  if (campaigns.loading) return <Loading />;
  if (campaigns.error) return <ErrorState message={campaigns.error} onRetry={campaigns.reload} />;
  const open = campaigns.data.items.filter((c) => c.status !== "ARCHIVED");
  const campaign = open.find((c) => String(c.id) === cid);
  return (
    <div className="space-y-5">
      <h1 className="font-display text-2xl font-bold text-slate-900">Resources &amp; beneficiaries</h1>
      <select className={inputClass} aria-label="Campaign" value={cid} onChange={(e) => setCid(e.target.value)}>
        <option value="">Choose a campaign…</option>{open.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
      </select>
      {campaign ? <><Beneficiaries campaign={campaign} list={list} /><Resources campaign={campaign} beneficiaries={list.data || []} /></> : open.length === 0 && <EmptyState title="No campaigns yet" hint="Create a campaign first." />}
    </div>
  );
}

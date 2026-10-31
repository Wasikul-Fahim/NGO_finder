import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { listCampaigns } from "../api/campaigns";
import { parseError } from "../api/client";
import { getUtilization, makeDonation, myDonations } from "../api/impact";
import { EmptyState, ErrorState, Loading } from "../components/AsyncState";
import { StatusPill } from "../components/Chips";
import FormField, { inputClass, primaryButton, secondaryButton, textareaClass } from "../components/FormField";
import { ErrorNotice, SuccessNotice, money } from "../components/Notice";
import Pager from "../components/Pager";
import useAsync from "../hooks/useAsync";

const TYPES = ["MONEY", "FOOD", "CLOTHES", "MEDICINE", "EDUCATIONAL", "OTHER"];

function DonateForm({ campaigns, initialCampaign, onDone }) {
  const [form, setForm] = useState({ campaign_id: initialCampaign || campaigns[0]?.id || "", donation_type: "MONEY", amount: "", note: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState({ message: "", fields: {} });
  const [ok, setOk] = useState("");
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const isMoney = form.donation_type === "MONEY";

  async function submit(e) {
    e.preventDefault();
    setSaving(true); setError({ message: "", fields: {} }); setOk("");
    try {
      await makeDonation({ campaign_id: Number(form.campaign_id), donation_type: form.donation_type, amount: Number(form.amount) || 0, note: form.note || null });
      setOk("Thank you! Your pledge is recorded and will be confirmed by the NGO once received.");
      setForm((f) => ({ ...f, amount: "", note: "" }));
      onDone();
    } catch (err) { setError(parseError(err)); }
    finally { setSaving(false); }
  }

  return (
    <form onSubmit={submit} className="surface-card space-y-4 p-5" noValidate>
      <h2 className="font-display text-lg font-bold text-slate-900">Make a donation</h2>
      <p className="text-xs text-slate-500">This records your pledge only. No payment details are collected or stored here.</p>
      <SuccessNotice>{ok}</SuccessNotice>
      <ErrorNotice>{error.message}</ErrorNotice>
      <FormField label="Campaign" error={error.fields.campaign_id}>
        <select className={inputClass} value={form.campaign_id} onChange={set("campaign_id")}>
          {campaigns.map((c) => <option key={c.id} value={c.id}>{c.title} — {c.ngo_name}</option>)}
        </select>
      </FormField>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Type" error={error.fields.donation_type}>
          <select className={inputClass} value={form.donation_type} onChange={set("donation_type")}>{TYPES.map((t) => <option key={t}>{t}</option>)}</select>
        </FormField>
        <FormField label={isMoney ? "Amount (৳)" : "Estimated value (৳, optional)"} error={error.fields.amount}>
          <input className={inputClass} type="number" min="0" step="0.01" value={form.amount} onChange={set("amount")} />
        </FormField>
      </div>
      <FormField label={isMoney ? "Note (optional)" : "What are you donating?"} error={error.fields.note}>
        <textarea className={textareaClass} rows={2} maxLength={1000} value={form.note} onChange={set("note")} />
      </FormField>
      <button className={primaryButton} disabled={saving || !form.campaign_id}>{saving ? "Saving…" : "Record donation"}</button>
    </form>
  );
}

function Utilization({ donations }) {
  const received = [...new Map(donations.filter((d) => d.status === "RECEIVED" && d.campaign_id).map((d) => [d.campaign_id, d.campaign_title]))];
  const [id, setId] = useState("");
  const state = useAsync(() => (id ? getUtilization(id) : Promise.resolve(null)), [id]);
  if (received.length === 0) return null;
  return (
    <section className="surface-card space-y-3 p-5">
      <h2 className="font-display text-lg font-bold text-slate-900">Where your donation went</h2>
      <select className={inputClass} value={id} aria-label="Campaign" onChange={(e) => setId(e.target.value)}>
        <option value="">Choose a campaign…</option>
        {received.map(([cid, title]) => <option key={cid} value={cid}>{title}</option>)}
      </select>
      {state.error && <ErrorNotice>{state.error}</ErrorNotice>}
      {state.data && (
        <div className="space-y-3">
          <p className="text-sm text-slate-600">Money received by this campaign: <strong>{money(state.data.money_received)}</strong></p>
          {state.data.resources.length === 0 ? <p className="text-sm text-slate-500">No resources tracked yet.</p> : state.data.resources.map((r) => (
            <div key={r.id}>
              <div className="flex justify-between text-xs font-bold text-slate-600"><span>{r.name}</span><span>{r.quantity_allocated} / {r.quantity_total} {r.unit} distributed</span></div>
              <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${r.quantity_total ? (r.quantity_allocated / r.quantity_total) * 100 : 0}%` }} /></div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default function Donations() {
  const [params] = useSearchParams();
  const [page, setPage] = useState(1);
  const history = useAsync(() => myDonations({ page, page_size: 10 }), [page]);
  const campaigns = useAsync(() => listCampaigns({ status: "ACTIVE", page_size: 100 }));
  const all = useAsync(() => myDonations({ page_size: 100 }));

  if (campaigns.loading) return <Loading />;
  if (campaigns.error) return <ErrorState message={campaigns.error} onRetry={campaigns.reload} />;
  const refresh = () => { history.reload(); all.reload(); };

  return (
    <div className="space-y-6">
      <h1 className="font-display text-2xl font-bold text-slate-900">Donations</h1>
      {campaigns.data.items.length === 0
        ? <EmptyState title="No campaigns are accepting donations" hint="Check back soon." />
        : <DonateForm campaigns={campaigns.data.items} initialCampaign={Number(params.get("campaign")) || null} onDone={refresh} />}
      {all.data && <Utilization donations={all.data.items} />}
      <section className="space-y-3">
        <h2 className="font-display text-lg font-bold text-slate-900">My donation history</h2>
        {history.loading ? <Loading rows={2} /> : history.error ? <ErrorState message={history.error} onRetry={history.reload} /> : history.data.items.length === 0 ? (
          <EmptyState title="No donations yet" />
        ) : (
          <ul className="space-y-2">
            {history.data.items.map((d) => (
              <li key={d.id} className="surface-card flex items-center justify-between gap-3 p-4">
                <div>
                  <p className="font-bold text-slate-900">{d.campaign_title} <span className="font-normal text-slate-500">· {d.ngo_name}</span></p>
                  <p className="text-xs text-slate-500">{d.donation_date} · {d.donation_type}{d.donation_type === "MONEY" ? ` · ${money(d.amount)}` : ""}{d.note ? ` · ${d.note}` : ""}</p>
                </div>
                <StatusPill status={d.status} />
              </li>
            ))}
          </ul>
        )}
        <Pager data={history.data} page={page} onPage={setPage} />
      </section>
    </div>
  );
}

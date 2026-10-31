import { useState } from "react";

import { listCampaigns } from "../../api/campaigns";
import { parseError } from "../../api/client";
import { sendAnnouncement } from "../../api/notifications";
import { ErrorState, Loading } from "../../components/AsyncState";
import FormField, { inputClass, primaryButton, textareaClass } from "../../components/FormField";
import { ErrorNotice, SuccessNotice } from "../../components/Notice";
import useAsync from "../../hooks/useAsync";

export default function Announcements() {
  const campaigns = useAsync(() => listCampaigns({ mine: true, page_size: 100 }));
  const [form, setForm] = useState({ title: "", message: "", audience: "ALL", priority: "NORMAL", campaign_id: "" });
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState("");
  const [error, setError] = useState({ message: "", fields: {} });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  if (campaigns.loading) return <Loading />;
  if (campaigns.error) return <ErrorState message={campaigns.error} onRetry={campaigns.reload} />;

  const emergency = form.priority === "HIGH";

  async function submit(e) {
    e.preventDefault();
    if (emergency && !window.confirm("Send this as an EMERGENCY ALERT? Recipients will see it as urgent.")) return;
    setSending(true); setResult(""); setError({ message: "", fields: {} });
    try {
      const r = await sendAnnouncement({ ...form, campaign_id: form.campaign_id ? Number(form.campaign_id) : null });
      setResult(r.audience_size === 0
        ? "Nobody to send to yet: you need accepted volunteers or donors."
        : r.recipients === 0 ? "Everyone in the audience already has an identical unread message." : `Sent to ${r.recipients} ${r.recipients === 1 ? "person" : "people"}.`);
      if (r.recipients > 0) setForm((f) => ({ ...f, title: "", message: "" }));
    } catch (err) { setError(parseError(err)); }
    finally { setSending(false); }
  }

  return (
    <form onSubmit={submit} className="surface-card mx-auto max-w-2xl space-y-4 p-6" noValidate>
      <div>
        <h1 className="font-display text-2xl font-bold text-slate-900">Announcements</h1>
        <p className="mt-1 text-sm text-slate-500">Message the volunteers and donors connected to your NGO. They get it instantly if online, and in their inbox otherwise.</p>
      </div>
      <SuccessNotice>{result}</SuccessNotice>
      <ErrorNotice>{error.message}</ErrorNotice>
      <div className="grid gap-4 sm:grid-cols-3">
        <FormField label="Send to" error={error.fields.audience}>
          <select className={inputClass} value={form.audience} onChange={set("audience")}><option value="ALL">Volunteers &amp; donors</option><option value="VOLUNTEERS">Volunteers only</option><option value="DONORS">Donors only</option></select>
        </FormField>
        <FormField label="Campaign (optional)" error={error.fields.campaign_id}>
          <select className={inputClass} value={form.campaign_id} onChange={set("campaign_id")}><option value="">Whole NGO</option>{campaigns.data.items.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}</select>
        </FormField>
        <FormField label="Priority" error={error.fields.priority}>
          <select className={inputClass} value={form.priority} onChange={set("priority")}><option value="NORMAL">Normal</option><option value="HIGH">Emergency alert</option></select>
        </FormField>
      </div>
      <FormField label="Title" error={error.fields.title}><input className={inputClass} maxLength={120} value={form.title} onChange={set("title")} required /></FormField>
      <FormField label="Message" error={error.fields.message}><textarea className={textareaClass} rows={4} maxLength={1000} value={form.message} onChange={set("message")} required /></FormField>
      {emergency && <p className="rounded-lg bg-rose-50 px-3 py-2.5 text-xs font-semibold text-rose-700">Emergency alerts are highlighted for recipients. Use them only when people need to act now.</p>}
      <button className={`${primaryButton} ${emergency ? "!bg-rose-600 hover:!bg-rose-700" : ""}`} disabled={sending}>{sending ? "Sending…" : emergency ? "Send emergency alert" : "Send announcement"}</button>
    </form>
  );
}

import { useState } from "react";

import { createNgoAdmin, listNgos, verifyNgo } from "../../api/admin";
import { parseError } from "../../api/client";
import { EmptyState, ErrorState, Loading } from "../../components/AsyncState";
import FormField, { inputClass, primaryButton, secondaryButton } from "../../components/FormField";
import { ErrorNotice, SuccessNotice } from "../../components/Notice";
import Pager from "../../components/Pager";
import useAsync from "../../hooks/useAsync";

const TONE = { VERIFIED: "bg-emerald-50 text-emerald-700", PENDING: "bg-amber-50 text-amber-700", REJECTED: "bg-rose-50 text-rose-700" };
const EMPTY = { name: "", email: "", password: "", ngo_name: "", verified: false };

function CreateNgoAdmin({ onCreated }) {
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState({ message: "", fields: {} });
  const [ok, setOk] = useState("");
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  async function submit(e) {
    e.preventDefault();
    setSaving(true); setError({ message: "", fields: {} }); setOk("");
    try { const u = await createNgoAdmin(form); setOk(`Created ${u.ngo_name} (${u.email}).`); setForm(EMPTY); onCreated(); }
    catch (err) { setError(parseError(err)); }
    finally { setSaving(false); }
  }
  return (
    <form onSubmit={submit} className="surface-card space-y-4 p-5" noValidate>
      <h2 className="font-display text-lg font-bold text-slate-900">Create an NGO admin account</h2>
      <p className="text-xs text-slate-500">NGO accounts can't be created through public signup. Share the password with the NGO securely; they can change it after logging in.</p>
      <SuccessNotice>{ok}</SuccessNotice><ErrorNotice>{error.message}</ErrorNotice>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="NGO name" error={error.fields.ngo_name}><input className={inputClass} value={form.ngo_name} onChange={set("ngo_name")} required /></FormField>
        <FormField label="Admin's name" error={error.fields.name}><input className={inputClass} value={form.name} onChange={set("name")} required /></FormField>
        <FormField label="Admin's email" error={error.fields.email}><input className={inputClass} type="email" value={form.email} onChange={set("email")} required /></FormField>
        <FormField label="Temporary password" error={error.fields.password}><input className={inputClass} type="password" autoComplete="new-password" value={form.password} onChange={set("password")} required /></FormField>
      </div>
      <label className="flex items-center gap-2 text-sm font-semibold text-slate-700"><input type="checkbox" checked={form.verified} onChange={(e) => setForm({ ...form, verified: e.target.checked })} /> Mark as verified immediately</label>
      <button className={primaryButton} disabled={saving}>{saving ? "Creating…" : "Create NGO admin"}</button>
    </form>
  );
}

export default function PlatformNgos() {
  const [status, setStatus] = useState("PENDING");
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(() => listNgos({ page, page_size: 10, ...(status ? { status } : {}) }), [status, page]);
  const [msg, setMsg] = useState({ ok: "", error: "" });

  async function decide(ngo, decision) {
    const reason = decision === "REJECTED" ? window.prompt(`Why is "${ngo.ngo_name}" being rejected? (optional)`) : "";
    if (reason === null) return;
    setMsg({ ok: "", error: "" });
    try { await verifyNgo(ngo.id, decision, reason); setMsg({ ok: `${ngo.ngo_name} is now ${decision.toLowerCase()}.`, error: "" }); reload(); }
    catch (err) { setMsg({ ok: "", error: parseError(err).message }); }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-bold text-slate-900">NGOs &amp; verification</h1>
        <select className={`${inputClass} !w-auto`} aria-label="Filter by status" value={status} onChange={(e) => { setPage(1); setStatus(e.target.value); }}>
          <option value="">All</option><option>PENDING</option><option>VERIFIED</option><option>REJECTED</option>
        </select>
      </div>
      <SuccessNotice>{msg.ok}</SuccessNotice><ErrorNotice>{msg.error}</ErrorNotice>
      {loading ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data.items.length === 0 ? <EmptyState title="No NGOs here" /> : (
        <ul className="space-y-3">
          {data.items.map((n) => (
            <li key={n.id} className="surface-card flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="flex items-center gap-2"><h3 className="font-display text-base font-bold text-slate-900">{n.ngo_name}</h3><span className={`rounded-full px-2 py-0.5 text-[10px] font-extrabold uppercase ${TONE[n.verification_status]}`}>{n.verification_status}</span></div>
                <p className="mt-1 text-xs text-slate-500">{[n.address, n.contact].filter(Boolean).join(" · ") || "No contact details"}</p>
                {n.description && <p className="mt-1 text-sm text-slate-600">{n.description}</p>}
              </div>
              <div className="flex gap-2">
                {n.verification_status !== "VERIFIED" && <button className={primaryButton} onClick={() => decide(n, "VERIFIED")}>Verify</button>}
                {n.verification_status !== "REJECTED" && <button className={secondaryButton} onClick={() => decide(n, "REJECTED")}>Reject</button>}
              </div>
            </li>
          ))}
        </ul>
      )}
      <Pager data={data} page={page} onPage={setPage} />
      <CreateNgoAdmin onCreated={reload} />
    </div>
  );
}

import { Link } from "react-router-dom";
import { useState } from "react";

import { getMyNgo, removeLogo, updateMyNgo, uploadLogo } from "../../api/campaigns";
import { apiBaseUrl, parseError } from "../../api/client";
import { ErrorState, Loading } from "../../components/AsyncState";
import FormField, { inputClass, primaryButton, textareaClass } from "../../components/FormField";
import useAsync from "../../hooks/useAsync";

const STATUS_STYLE = {
  VERIFIED: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  PENDING: "bg-amber-50 text-amber-700 ring-amber-200",
  REJECTED: "bg-rose-50 text-rose-700 ring-rose-200",
};

export default function OrganisationProfile() {
  const { data: ngo, loading, error, reload } = useAsync(getMyNgo);
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState({ ok: "", error: "", fields: {} });

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const form = draft ?? ngo;
  const set = (key) => (e) => setDraft({ ...form, [key]: e.target.value });

  async function save(e) {
    e.preventDefault();
    setSaving(true);
    setFeedback({ ok: "", error: "", fields: {} });
    try {
      await updateMyNgo({
        ngo_name: form.ngo_name, description: form.description || null,
        address: form.address || null, contact: form.contact || null,
        contact_number: form.contact_number || null, registration_info: form.registration_info || null,
      });
      setDraft(null);
      reload();
      setFeedback({ ok: "Organisation profile saved.", error: "", fields: {} });
    } catch (err) {
      const parsed = parseError(err);
      setFeedback({ ok: "", error: parsed.message, fields: parsed.fields });
    } finally {
      setSaving(false);
    }
  }

  async function onLogo(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setFeedback({ ok: "", error: "", fields: {} });
    try { await uploadLogo(file); reload(); setFeedback({ ok: "Logo updated.", error: "", fields: {} }); }
    catch (err) { const p = parseError(err); setFeedback({ ok: "", error: p.fields.file || p.message, fields: {} }); }
  }

  async function onRemoveLogo() {
    try { await removeLogo(); reload(); } catch (err) { setFeedback({ ok: "", error: parseError(err).message, fields: {} }); }
  }

  return (
    <div className="space-y-6">
      <section className="surface-card p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="font-display text-2xl font-bold text-slate-900">{ngo.ngo_name}</h1>
          <span className={`rounded-full px-3 py-1 text-[10px] font-extrabold uppercase tracking-wider ring-1 ${STATUS_STYLE[ngo.verification_status]}`}>{ngo.verification_status}</span>
        </div>
        {ngo.verification_remarks && <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2.5 text-sm text-slate-700"><strong>Note from the platform team:</strong> {ngo.verification_remarks}</p>}
        {ngo.verification_status !== "VERIFIED" && (
          <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2.5 text-sm text-amber-800">
            {ngo.verification_status === "PENDING"
              ? "Your organisation is awaiting verification by the platform team. You can edit your profile, but campaigns and events are locked until you are verified."
              : "Your organisation was not verified. Contact the platform team."}
          </p>
        )}
        <div className="mt-4 hidden flex-wrap gap-3 text-sm font-bold">
          <Link className="text-purple-700 hover:text-purple-900" to="/admin/campaigns">Manage campaigns →</Link>
          <Link className="text-purple-700 hover:text-purple-900" to="/admin/events">Manage events →</Link>
        </div>
      </section>

      <form onSubmit={save} className="surface-card space-y-4 p-6" noValidate>
        <h2 className="font-display text-lg font-bold text-slate-900">Organisation profile</h2>
        {feedback.ok && <p role="status" className="rounded-lg bg-emerald-50 px-3 py-2.5 text-sm font-semibold text-emerald-700">{feedback.ok}</p>}
        {feedback.error && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{feedback.error}</p>}
        <FormField label="Name" error={feedback.fields.ngo_name}><input className={inputClass} value={form.ngo_name} onChange={set("ngo_name")} required /></FormField>
        <div className="flex items-center gap-4">
          {ngo.logo_url ? <img src={`${apiBaseUrl}${ngo.logo_url}`} alt={`${ngo.ngo_name} logo`} className="h-16 w-16 rounded-xl border border-slate-200 object-cover" />
            : <span className="grid h-16 w-16 place-items-center rounded-xl bg-slate-100 text-[10px] font-bold text-slate-400">NO LOGO</span>}
          <div className="space-y-1">
            <label className="inline-block cursor-pointer rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700 hover:border-purple-300">
              {ngo.logo_url ? "Replace logo" : "Upload logo"}
              <input type="file" accept="image/png,image/jpeg,image/webp" className="sr-only" onChange={onLogo} />
            </label>
            {ngo.logo_url && <button type="button" onClick={onRemoveLogo} className="ml-2 text-xs font-bold text-rose-600">Remove</button>}
            <p className="text-[11px] text-slate-400">PNG, JPG or WEBP, up to 2 MB.</p>
          </div>
        </div>
        <FormField label="Description" error={feedback.fields.description}><textarea className={textareaClass} rows={3} value={form.description ?? ""} onChange={set("description")} /></FormField>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Address" error={feedback.fields.address}><input className={inputClass} value={form.address ?? ""} onChange={set("address")} /></FormField>
          <FormField label="Public contact email" error={feedback.fields.contact}><input className={inputClass} type="email" value={form.contact ?? ""} onChange={set("contact")} /></FormField>
          <FormField label="Contact number" error={feedback.fields.contact_number}><input className={inputClass} type="tel" value={form.contact_number ?? ""} onChange={set("contact_number")} /></FormField>
        </div>
        <FormField label="Registration information" error={feedback.fields.registration_info}>
          <textarea className={textareaClass} rows={2} value={form.registration_info ?? ""} onChange={set("registration_info")} />
        </FormField>
        <button className={primaryButton} disabled={saving || !draft}>{saving ? "Saving…" : "Save changes"}</button>
      </form>
    </div>
  );
}

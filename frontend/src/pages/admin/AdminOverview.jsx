import { Link } from "react-router-dom";
import { useState } from "react";

import { getMyNgo, updateMyNgo } from "../../api/campaigns";
import { parseError } from "../../api/client";
import { ErrorState, Loading } from "../../components/AsyncState";
import FormField, { inputClass, primaryButton, textareaClass } from "../../components/FormField";
import useAsync from "../../hooks/useAsync";

const STATUS_STYLE = {
  VERIFIED: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  PENDING: "bg-amber-50 text-amber-700 ring-amber-200",
  REJECTED: "bg-rose-50 text-rose-700 ring-rose-200",
};

export default function AdminOverview() {
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

  return (
    <div className="space-y-6">
      <section className="surface-card p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="font-display text-2xl font-bold text-slate-900">{ngo.ngo_name}</h1>
          <span className={`rounded-full px-3 py-1 text-[10px] font-extrabold uppercase tracking-wider ring-1 ${STATUS_STYLE[ngo.verification_status]}`}>{ngo.verification_status}</span>
        </div>
        {ngo.verification_status !== "VERIFIED" && (
          <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2.5 text-sm text-amber-800">
            {ngo.verification_status === "PENDING"
              ? "Your organisation is awaiting verification by the platform team. You can edit your profile, but campaigns and events are locked until you are verified."
              : "Your organisation was not verified. Contact the platform team."}
          </p>
        )}
        <div className="mt-4 flex flex-wrap gap-3 text-sm font-bold">
          <Link className="text-purple-700 hover:text-purple-900" to="/admin/campaigns">Manage campaigns →</Link>
          <Link className="text-purple-700 hover:text-purple-900" to="/admin/events">Manage events →</Link>
        </div>
      </section>

      <form onSubmit={save} className="surface-card space-y-4 p-6" noValidate>
        <h2 className="font-display text-lg font-bold text-slate-900">Organisation profile</h2>
        {feedback.ok && <p role="status" className="rounded-lg bg-emerald-50 px-3 py-2.5 text-sm font-semibold text-emerald-700">{feedback.ok}</p>}
        {feedback.error && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{feedback.error}</p>}
        <FormField label="Name" error={feedback.fields.ngo_name}><input className={inputClass} value={form.ngo_name} onChange={set("ngo_name")} required /></FormField>
        <FormField label="Description" error={feedback.fields.description}><textarea className={textareaClass} rows={3} value={form.description ?? ""} onChange={set("description")} /></FormField>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Address" error={feedback.fields.address}><input className={inputClass} value={form.address ?? ""} onChange={set("address")} /></FormField>
          <FormField label="Contact" error={feedback.fields.contact}><input className={inputClass} value={form.contact ?? ""} onChange={set("contact")} /></FormField>
        </div>
        <button className={primaryButton} disabled={saving || !draft}>{saving ? "Saving…" : "Save changes"}</button>
      </form>
    </div>
  );
}

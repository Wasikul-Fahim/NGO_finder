import { useEffect, useState } from "react";

import { getMyProfile, updateMyProfile } from "../api/opportunities";
import { parseError } from "../api/client";
import { ErrorState, Loading } from "../components/AsyncState";
import { DayPicker, toList } from "../components/Chips";
import FormField, { inputClass, primaryButton, textareaClass } from "../components/FormField";
import useAsync from "../hooks/useAsync";

export default function Profile() {
  const { data, loading, error, reload } = useAsync(getMyProfile);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState({ ok: "", error: "", fields: {} });

  useEffect(() => {
    if (data) setForm({
      location: data.location ?? "", skills: data.skills.join(", "), interests: data.interests.join(", "),
      availability: data.availability, experience: data.experience ?? "",
    });
  }, [data]);

  if (loading || !form) return error ? <ErrorState message={error} onRetry={reload} /> : <Loading />;
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function save(e) {
    e.preventDefault();
    setSaving(true);
    setFeedback({ ok: "", error: "", fields: {} });
    try {
      await updateMyProfile({
        location: form.location.trim() || null, skills: toList(form.skills), interests: toList(form.interests),
        availability: form.availability, experience: form.experience.trim() || null,
      });
      setFeedback({ ok: "Profile saved. Your recommendations are updated.", error: "", fields: {} });
    } catch (err) {
      const p = parseError(err);
      setFeedback({ ok: "", error: p.message, fields: p.fields });
    } finally { setSaving(false); }
  }

  return (
    <form onSubmit={save} className="surface-card mx-auto max-w-2xl space-y-5 p-6" noValidate>
      <div>
        <h1 className="font-display text-2xl font-bold text-slate-900">My volunteer profile</h1>
        <p className="mt-1 text-sm text-slate-500">This is what we use to rank opportunities for you.</p>
      </div>
      {feedback.ok && <p role="status" className="rounded-lg bg-emerald-50 px-3 py-2.5 text-sm font-semibold text-emerald-700">{feedback.ok}</p>}
      {feedback.error && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{feedback.error}</p>}
      <FormField label="Location" error={feedback.fields.location}>
        <input className={inputClass} placeholder="City, Region — e.g. Dhaka, Dhaka" value={form.location} onChange={set("location")} />
      </FormField>
      <FormField label="Skills (comma separated)" error={feedback.fields.skills}>
        <input className={inputClass} placeholder="Teaching, First Aid" value={form.skills} onChange={set("skills")} />
      </FormField>
      <FormField label="Interests (comma separated)" error={feedback.fields.interests}>
        <input className={inputClass} placeholder="Education, Health" value={form.interests} onChange={set("interests")} />
      </FormField>
      <div>
        <span className="mb-1.5 block text-xs font-bold text-slate-700">Days you are available</span>
        <DayPicker value={form.availability} onChange={(availability) => setForm((f) => ({ ...f, availability }))} />
        {feedback.fields.availability && <span role="alert" className="mt-1 block text-xs font-semibold text-rose-600">{feedback.fields.availability}</span>}
      </div>
      <FormField label="Experience" error={feedback.fields.experience}>
        <textarea className={textareaClass} rows={4} value={form.experience} onChange={set("experience")} />
      </FormField>
      <button className={primaryButton} disabled={saving}>{saving ? "Saving…" : "Save profile"}</button>
    </form>
  );
}

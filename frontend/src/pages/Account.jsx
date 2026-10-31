import { useState } from "react";

import { changePassword, updateProfile } from "../api/auth";
import { parseError } from "../api/client";
import FormField, { inputClass, primaryButton } from "../components/FormField";
import { ErrorNotice, SuccessNotice } from "../components/Notice";
import { useAuth } from "../context/AuthContext";

export default function Account() {
  const { user, refreshUser } = useAuth();
  const [form, setForm] = useState({ name: user.name, phone: user.phone ?? "", location: user.location ?? "" });
  const [pw, setPw] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [info, setInfo] = useState({ ok: "", error: "", fields: {} });
  const [pwState, setPwState] = useState({ ok: "", error: "", fields: {} });
  const [busy, setBusy] = useState(false);

  async function saveProfile(e) {
    e.preventDefault();
    setBusy(true); setInfo({ ok: "", error: "", fields: {} });
    try {
      await updateProfile({ name: form.name, phone: form.phone.trim() || null, location: form.location.trim() || null });
      await refreshUser();
      setInfo({ ok: "Account details saved.", error: "", fields: {} });
    } catch (err) { const p = parseError(err); setInfo({ ok: "", error: p.message, fields: p.fields }); }
    finally { setBusy(false); }
  }

  async function savePassword(e) {
    e.preventDefault();
    setBusy(true); setPwState({ ok: "", error: "", fields: {} });
    try {
      await changePassword(pw);
      setPw({ current_password: "", new_password: "", confirm_password: "" });
      setPwState({ ok: "Password changed. Other devices have been signed out.", error: "", fields: {} });
    } catch (err) { const p = parseError(err); setPwState({ ok: "", error: p.message, fields: p.fields }); }
    finally { setBusy(false); }
  }

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const setP = (k) => (e) => setPw((f) => ({ ...f, [k]: e.target.value }));
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <form onSubmit={saveProfile} className="surface-card space-y-4 p-6" noValidate>
        <div><h1 className="font-display text-2xl font-bold text-slate-900">My account</h1><p className="mt-1 text-sm text-slate-500">Signed in as {user.email} ({user.role.replace("_", " ").toLowerCase()}).</p></div>
        <SuccessNotice>{info.ok}</SuccessNotice><ErrorNotice>{info.error}</ErrorNotice>
        <FormField label="Full name" error={info.fields.name}><input className={inputClass} value={form.name} onChange={set("name")} required /></FormField>
        <FormField label="Mobile number" error={info.fields.phone}><input className={inputClass} type="tel" placeholder="01712345678" value={form.phone} onChange={set("phone")} /></FormField>
        <FormField label="Location" error={info.fields.location}><input className={inputClass} value={form.location} onChange={set("location")} /></FormField>
        <button className={primaryButton} disabled={busy}>Save details</button>
      </form>
      <form onSubmit={savePassword} className="surface-card space-y-4 p-6" noValidate>
        <h2 className="font-display text-lg font-bold text-slate-900">Change password</h2>
        <SuccessNotice>{pwState.ok}</SuccessNotice><ErrorNotice>{pwState.error}</ErrorNotice>
        <FormField label="Current password" error={pwState.fields.current_password}><input className={inputClass} type="password" autoComplete="current-password" value={pw.current_password} onChange={setP("current_password")} /></FormField>
        <FormField label="New password" error={pwState.fields.new_password}><input className={inputClass} type="password" autoComplete="new-password" value={pw.new_password} onChange={setP("new_password")} /></FormField>
        <FormField label="Confirm new password" error={pwState.fields.confirm_password}><input className={inputClass} type="password" autoComplete="new-password" value={pw.confirm_password} onChange={setP("confirm_password")} /></FormField>
        <button className={primaryButton} disabled={busy}>Change password</button>
      </form>
    </div>
  );
}

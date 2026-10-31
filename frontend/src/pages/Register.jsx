import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { parseError } from "../api/client";
import AuthLayout from "../components/AuthLayout";
import FormField, { inputClass, primaryButton } from "../components/FormField";
import { ROLE_HOME, useAuth } from "../context/AuthContext";

const ROLES = [
  { value: "VOLUNTEER", label: "Volunteer" },
  { value: "DONOR", label: "Donor" },
  { value: "BENEFICIARY", label: "Beneficiary" },
];

export default function Register() {
  const { register, login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm_password: "", role: "VOLUNTEER", location: "" });
  const [error, setError] = useState({ message: "", fields: {} });
  const [submitting, setSubmitting] = useState(false);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(e) {
    e.preventDefault();
    setError({ message: "", fields: {} });
    if (form.password !== form.confirm_password) {
      setError({ message: "", fields: { confirm_password: "Passwords do not match." } });
      return;
    }
    setSubmitting(true);
    try {
      await register({ ...form, location: form.location.trim() || null });
      const user = await login({ email: form.email, password: form.password });
      navigate(ROLE_HOME[user.role] || "/dashboard", { replace: true });
    } catch (err) {
      setError(parseError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Join as a volunteer, donor or beneficiary. NGO accounts are set up by the platform team."
      footer={<>Already registered? <Link className="font-bold text-purple-700 hover:text-purple-900" to="/login">Log in</Link></>}
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {error.message && <div role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{error.message}</div>}
        <FormField label="I am a…" error={error.fields.role}>
          <select className={inputClass} value={form.role} onChange={set("role")}>
            {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </FormField>
        <FormField label="Full name" error={error.fields.name}>
          <input className={inputClass} autoComplete="name" required value={form.name} onChange={set("name")} />
        </FormField>
        <FormField label="Email" error={error.fields.email}>
          <input className={inputClass} type="email" autoComplete="email" required value={form.email} onChange={set("email")} />
        </FormField>
        <FormField label="Location (city)" error={error.fields.location}>
          <input className={inputClass} autoComplete="address-level2" value={form.location} onChange={set("location")} />
        </FormField>
        <FormField label="Password" error={error.fields.password}>
          <input className={inputClass} type="password" autoComplete="new-password" required value={form.password} onChange={set("password")} />
          <span className="mt-1 block text-[11px] text-slate-400">At least 8 characters, with a letter and a number.</span>
        </FormField>
        <FormField label="Confirm password" error={error.fields.confirm_password}>
          <input className={inputClass} type="password" autoComplete="new-password" required value={form.confirm_password} onChange={set("confirm_password")} />
        </FormField>
        <button className={`${primaryButton} w-full`} disabled={submitting}>{submitting ? "Creating account…" : "Create account"}</button>
      </form>
    </AuthLayout>
  );
}

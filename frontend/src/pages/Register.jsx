import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { parseError } from "../api/client";
import AuthLayout from "../components/AuthLayout";
import FormField, { inputClass, primaryButton, textareaClass } from "../components/FormField";
import { ROLE_HOME, useAuth } from "../context/AuthContext";

const ROLES = [
  { value: "VOLUNTEER", label: "Volunteer: I want to help" },
  { value: "NGO", label: "NGO / organisation: I want to post campaigns and recruit" },
  { value: "DONOR", label: "Donor: I want to give" },
  { value: "BENEFICIARY", label: "Beneficiary: I need support" },
];

export default function Register() {
  const { register, registerNgo, login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "", email: "", password: "", confirm_password: "", role: "VOLUNTEER", location: "",
    ngo_name: "", description: "", address: "", contact: "", contact_number: "", registration_info: "", phone: "",
  });
  const [error, setError] = useState({ message: "", fields: {} });
  const [submitting, setSubmitting] = useState(false);

  const isNgo = form.role === "NGO";
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
      const base = { name: form.name, email: form.email, password: form.password, confirm_password: form.confirm_password, location: form.location.trim() || null, phone: form.phone.trim() || null };
      if (isNgo) {
        await registerNgo({ ...base, ngo_name: form.ngo_name, description: form.description.trim() || null, address: form.address.trim() || null, contact: form.contact.trim() || null, contact_number: form.contact_number.trim() || null, registration_info: form.registration_info.trim() || null });
      } else {
        await register({ ...base, role: form.role });
      }
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
      subtitle="Join as a volunteer, NGO, donor or beneficiary."
      footer={<>Already registered? <Link className="font-bold text-purple-700 hover:text-purple-900" to="/login">Log in</Link></>}
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {error.message && <div role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{error.message}</div>}
        <FormField label="I am a…" error={error.fields.role}>
          <select className={inputClass} value={form.role} onChange={set("role")}>
            {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </FormField>
        {isNgo && (
          <>
            <p className="rounded-lg bg-amber-50 px-3 py-2.5 text-xs leading-5 text-amber-800">
              After you sign up, the platform team verifies your organisation. You can log in and set up your profile straight away, but you can post campaigns, opportunities and events only once you are verified.
            </p>
            <FormField label="Organisation name" error={error.fields.ngo_name}>
              <input className={inputClass} required value={form.ngo_name} onChange={set("ngo_name")} />
            </FormField>
            <FormField label="What does your organisation do?" error={error.fields.description}>
              <textarea className={textareaClass} rows={3} value={form.description} onChange={set("description")} />
            </FormField>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="Address" error={error.fields.address}><input className={inputClass} value={form.address} onChange={set("address")} /></FormField>
              <FormField label="Public contact email" error={error.fields.contact}><input className={inputClass} type="email" value={form.contact} onChange={set("contact")} /></FormField>
              <FormField label="Contact number" error={error.fields.contact_number}><input className={inputClass} type="tel" placeholder="01712345678" value={form.contact_number} onChange={set("contact_number")} /></FormField>
            </div>
            <FormField label="Registration information" error={error.fields.registration_info}>
              <textarea className={textareaClass} rows={2} placeholder="Registration / licence number and issuing body" value={form.registration_info} onChange={set("registration_info")} />
            </FormField>
            <p className="text-[11px] text-slate-400">You can add your logo from the organisation profile after signing up.</p>
          </>
        )}
        <FormField label={isNgo ? "Your full name" : "Full name"} error={error.fields.name}>
          <input className={inputClass} autoComplete="name" required value={form.name} onChange={set("name")} />
        </FormField>
        <FormField label="Email" error={error.fields.email}>
          <input className={inputClass} type="email" autoComplete="email" required value={form.email} onChange={set("email")} />
        </FormField>
        <FormField label={isNgo ? "Your mobile number" : "Mobile number"} error={error.fields.phone}>
          <input className={inputClass} type="tel" autoComplete="tel" placeholder="01712345678" value={form.phone} onChange={set("phone")} />
          {form.role === "VOLUNTEER" && <span className="mt-1 block text-[11px] text-slate-400">NGOs use this to reach you. Required before you can apply to an opportunity.</span>}
        </FormField>
        <FormField label={isNgo ? "City (e.g. Dhaka, Dhaka)" : "Location (City, Region)"} error={error.fields.location}>
          <input className={inputClass} autoComplete="address-level2" value={form.location} onChange={set("location")} />
        </FormField>
        <FormField label="Password" error={error.fields.password}>
          <input className={inputClass} type="password" autoComplete="new-password" required value={form.password} onChange={set("password")} />
          <span className="mt-1 block text-[11px] text-slate-400">At least 8 characters, with a letter and a number.</span>
        </FormField>
        <FormField label="Confirm password" error={error.fields.confirm_password}>
          <input className={inputClass} type="password" autoComplete="new-password" required value={form.confirm_password} onChange={set("confirm_password")} />
        </FormField>
        <button className={`${primaryButton} w-full`} disabled={submitting}>{submitting ? "Creating account…" : isNgo ? "Register my organisation" : "Create account"}</button>
      </form>
    </AuthLayout>
  );
}

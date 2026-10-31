import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { parseError } from "../api/client";
import AuthLayout from "../components/AuthLayout";
import FormField, { inputClass, primaryButton } from "../components/FormField";
import { ROLE_HOME, useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, user, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState({ message: "", fields: {} });
  const [submitting, setSubmitting] = useState(false);

  const from = location.state?.from?.pathname;
  if (!isLoading && user) return <Navigate to={from || ROLE_HOME[user.role] || "/"} replace />;

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(e) {
    e.preventDefault();
    setError({ message: "", fields: {} });
    setSubmitting(true);
    try {
      const signedIn = await login(form);
      navigate(from || ROLE_HOME[signedIn.role] || "/", { replace: true });
    } catch (err) {
      setError(parseError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Log in"
      subtitle="Welcome back. Pick up where you left off."
      footer={<>New here? <Link className="font-bold text-purple-700 hover:text-purple-900" to="/register">Create an account</Link></>}
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {error.message && <div role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{error.message}</div>}
        <FormField label="Email" error={error.fields.email}>
          <input className={inputClass} type="email" autoComplete="email" required value={form.email} onChange={set("email")} />
        </FormField>
        <FormField label="Password" error={error.fields.password}>
          <input className={inputClass} type="password" autoComplete="current-password" required value={form.password} onChange={set("password")} />
        </FormField>
        <button className={`${primaryButton} w-full`} disabled={submitting}>{submitting ? "Logging in…" : "Log in"}</button>
      </form>
    </AuthLayout>
  );
}

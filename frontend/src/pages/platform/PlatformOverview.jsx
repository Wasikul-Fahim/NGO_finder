import { Link } from "react-router-dom";

import { getStats } from "../../api/admin";
import { ErrorState, Loading } from "../../components/AsyncState";
import { Stat, money } from "../../components/Notice";
import useAsync from "../../hooks/useAsync";

const sum = (o) => Object.values(o).reduce((a, b) => a + b, 0);
const breakdown = (o) => Object.entries(o).map(([k, v]) => `${v} ${k.toLowerCase().replaceAll("_", " ")}`).join(" · ") || "none";

export default function PlatformOverview() {
  const { data: s, loading, error, reload } = useAsync(getStats);
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const pending = s.ngos_by_status.PENDING ?? 0;
  return (
    <div className="space-y-6">
      <h1 className="font-display text-2xl font-bold text-slate-900">Platform overview</h1>
      {pending > 0 && (
        <Link to="/platform/ngos" className="surface-card flex items-center gap-4 border-amber-200 p-4">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-amber-50 font-display text-lg font-extrabold text-amber-700">{pending}</span>
          <span className="text-sm font-bold text-slate-800">NGO{pending === 1 ? "" : "s"} waiting for verification →</span>
        </Link>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Users" value={sum(s.users_by_role)} hint={`${s.active_users} active`} />
        <Stat label="NGOs" value={sum(s.ngos_by_status)} hint={breakdown(s.ngos_by_status)} />
        <Stat label="Campaigns" value={sum(s.campaigns_by_status)} hint={breakdown(s.campaigns_by_status)} />
        <Stat label="Open opportunities" value={s.opportunities_active} />
        <Stat label="Applications" value={sum(s.applications_by_status)} hint={breakdown(s.applications_by_status)} />
        <Stat label="Tasks" value={sum(s.tasks_by_status)} hint={breakdown(s.tasks_by_status)} />
        <Stat label="Volunteer hours" value={s.volunteer_hours} />
        <Stat label="Donations received" value={money(s.donations_received_money)} hint={`${s.donations_pending} pending`} />
      </div>
      <section className="surface-card p-5">
        <h2 className="font-display text-lg font-bold text-slate-900">Users by role</h2>
        <p className="mt-2 text-sm text-slate-600">{breakdown(s.users_by_role)}</p>
        <p className="mt-3 text-xs text-slate-500">{s.audit_entries} entries in the <Link className="font-bold text-purple-700" to="/platform/audit">audit log</Link>.</p>
      </section>
    </div>
  );
}

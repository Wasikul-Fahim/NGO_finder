import { AlertCircle, CalendarDays } from "lucide-react";
import { Link } from "react-router-dom";

import { ngoDashboard } from "../../api/admin";
import { ErrorState, Loading } from "../../components/AsyncState";
import { Stat, money } from "../../components/Notice";
import useAsync from "../../hooks/useAsync";

const sum = (obj) => Object.values(obj).reduce((a, b) => a + b, 0);
const label = (action) => action.toLowerCase().replaceAll("_", " ");

export default function AdminOverview() {
  const { data: d, loading, error, reload } = useAsync(ngoDashboard);
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const verified = d.verification_status === "VERIFIED";
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-bold text-slate-900">{d.ngo_name}</h1>
        <span className={`rounded-full px-3 py-1 text-[10px] font-extrabold uppercase tracking-wider ring-1 ${verified ? "bg-emerald-50 text-emerald-700 ring-emerald-200" : "bg-amber-50 text-amber-700 ring-amber-200"}`}>{d.verification_status}</span>
      </div>
      {!verified && (
        <p className="rounded-lg bg-amber-50 px-3 py-2.5 text-sm text-amber-800">
          {d.verification_status === "PENDING" ? "Your organisation is awaiting verification. You can complete your " : "Your organisation was not verified. Contact the platform team. You can still edit your "}
          <Link to="/admin/profile" className="font-bold underline">profile</Link>, but creating campaigns, opportunities and other records is locked until you are verified.
        </p>
      )}

      <section aria-labelledby="attention">
        <h2 id="attention" className="mb-3 font-display text-lg font-bold text-slate-900">Needs your attention</h2>
        {d.needs_attention.length === 0 ? (
          <p className="surface-card p-5 text-sm text-slate-500">Nothing is waiting on you. 🎉</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {d.needs_attention.map((c) => (
              <Link key={c.key} to={c.link} className="surface-card flex items-center gap-4 p-4 transition hover:border-purple-200">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-amber-50 font-display text-lg font-extrabold text-amber-700">{c.count}</span>
                <span className="flex items-center gap-2 text-sm font-bold text-slate-800"><AlertCircle size={15} className="text-amber-500" />{c.label}</span>
              </Link>
            ))}
          </div>
        )}
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Campaigns" value={sum(d.campaigns_by_status)} hint={`${d.campaigns_by_status.ACTIVE ?? 0} active`} />
        <Stat label="Opportunities" value={d.opportunities_active} hint={`${d.opportunities_inactive} closed`} />
        <Stat label="Volunteers" value={d.accepted_volunteers} hint={`${d.volunteer_hours} hours logged`} />
        <Stat label="Applications" value={sum(d.applications_by_status)} hint={`${d.applications_by_status.ACCEPTED ?? 0} accepted`} />
        <Stat label="Tasks" value={sum(d.tasks_by_status)} hint={`${d.tasks_by_status.COMPLETED ?? 0} completed`} />
        <Stat label="Money received" value={money(d.money_received)} hint={`${d.donations_pending} pledges to confirm`} />
        <Stat label="Resources given out" value={`${d.resources_distributed} / ${d.resources_total}`} />
        <Stat label="Beneficiaries" value={d.beneficiaries_enrolled} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="surface-card p-5">
          <h2 className="flex items-center gap-2 font-display text-lg font-bold text-slate-900"><CalendarDays size={18} />Upcoming events</h2>
          {d.upcoming_events.length === 0 ? <p className="mt-3 text-sm text-slate-500">No upcoming events. <Link className="font-bold text-purple-700" to="/admin/events">Schedule one</Link>.</p> : (
            <ul className="mt-3 divide-y divide-slate-100">
              {d.upcoming_events.map((e) => <li key={e.id} className="py-2.5 text-sm"><span className="font-bold text-slate-900">{e.event_name}</span><span className="block text-xs text-slate-500">{e.event_date} · {e.campaign_title}{e.location ? ` · ${e.location}` : ""}</span></li>)}
            </ul>
          )}
        </section>
        <section className="surface-card p-5">
          <h2 className="font-display text-lg font-bold text-slate-900">Recent activity</h2>
          {d.recent_activity.length === 0 ? <p className="mt-3 text-sm text-slate-500">Your actions will be listed here.</p> : (
            <ul className="mt-3 divide-y divide-slate-100">
              {d.recent_activity.map((a) => <li key={a.id} className="py-2.5 text-sm"><span className="font-bold capitalize text-slate-900">{label(a.action_type)}</span><span className="block text-xs text-slate-500">{a.entity_type} #{a.entity_id} · {new Date(`${a.timestamp}Z`).toLocaleString()}</span></li>)}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

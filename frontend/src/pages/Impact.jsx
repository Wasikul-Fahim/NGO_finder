import { myContributions } from "../api/impact";
import { EmptyState, ErrorState, Loading } from "../components/AsyncState";
import { Stat } from "../components/Notice";
import useAsync from "../hooks/useAsync";

export default function Impact() {
  const { data, loading, error, reload } = useAsync(myContributions);
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const max = Math.max(1, ...data.monthly_hours.map((m) => m.hours));
  return (
    <div className="space-y-6">
      <h1 className="font-display text-2xl font-bold text-slate-900">My impact</h1>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Volunteer hours" value={`${data.total_hours} hrs`} />
        <Stat label="Events attended" value={data.events_attended} />
        <Stat label="Tasks completed" value={data.tasks_completed} hint={`of ${data.tasks_total} assigned`} />
        <Stat label="Active months" value={data.monthly_hours.length} />
      </div>

      <section className="surface-card p-5">
        <h2 className="font-display text-lg font-bold text-slate-900">Hours by month</h2>
        {data.monthly_hours.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">No recorded hours yet.</p>
        ) : (
          <ul className="mt-4 space-y-2">
            {data.monthly_hours.map((m) => (
              <li key={m.month} className="flex items-center gap-3 text-xs font-semibold text-slate-600">
                <span className="w-16 shrink-0">{m.month}</span>
                <div className="h-3 flex-1 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-purple-600" style={{ width: `${(m.hours / max) * 100}%` }} /></div>
                <span className="w-14 shrink-0 text-right">{m.hours} h</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-lg font-bold text-slate-900">Participation history</h2>
        {data.history.length === 0 ? (
          <EmptyState title="No events yet" hint="After an NGO records your attendance it shows up here." />
        ) : (
          <ul className="space-y-2">
            {data.history.map((h) => (
              <li key={h.id} className="surface-card flex items-center justify-between gap-3 p-4">
                <div>
                  <p className="font-bold text-slate-900">{h.event_name}</p>
                  <p className="text-xs text-slate-500">{h.campaign_title} · {h.participation_date}</p>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-xs font-extrabold ${h.attendance ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                  {h.attendance ? `${h.hours} h` : "Absent"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

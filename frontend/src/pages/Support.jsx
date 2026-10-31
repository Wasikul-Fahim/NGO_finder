import { mySupport } from "../api/impact";
import { EmptyState, ErrorState, Loading } from "../components/AsyncState";
import { StatusPill } from "../components/Chips";
import useAsync from "../hooks/useAsync";

export default function Support() {
  const { data, loading, error, reload } = useAsync(mySupport);
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <div className="space-y-5">
      <h1 className="font-display text-2xl font-bold text-slate-900">My support</h1>
      {data.length === 0 ? (
        <EmptyState title="You are not enrolled in a campaign yet" hint="When an NGO enrols you in a campaign, your support status and what you received appear here." />
      ) : data.map((s) => (
        <section key={s.campaign_id} className="surface-card space-y-3 p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div><h2 className="font-display text-lg font-bold text-slate-900">{s.campaign_title}</h2><p className="text-xs font-semibold text-purple-700">{s.ngo_name}</p></div>
            <StatusPill status={s.support_status} />
          </div>
          {s.received.length === 0 ? <p className="text-sm text-slate-500">Nothing received yet.</p> : (
            <ul className="divide-y divide-slate-100 text-sm">
              {s.received.map((r, i) => <li key={i} className="flex justify-between py-2"><span>{r.resource}</span><span className="text-slate-500">{r.quantity} {r.unit} · {r.date}</span></li>)}
            </ul>
          )}
        </section>
      ))}
    </div>
  );
}

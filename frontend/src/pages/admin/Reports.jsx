import { useState } from "react";

import { donationSummary, volunteerPerformance } from "../../api/impact";
import { EmptyState, ErrorState, Loading } from "../../components/AsyncState";
import { money } from "../../components/Notice";
import Pager from "../../components/Pager";
import useAsync from "../../hooks/useAsync";

function Performance() {
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(() => volunteerPerformance({ page, page_size: 10 }), [page]);
  if (loading) return <Loading rows={2} />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <section className="space-y-3">
      <h2 className="font-display text-lg font-bold text-slate-900">Volunteer performance</h2>
      {data.items.length === 0 ? <EmptyState title="No activity yet" hint="Record attendance or complete tasks to build the ranking." /> : (
        <div className="surface-card overflow-x-auto">
          <table className="w-full min-w-[480px] text-left text-sm">
            <thead className="text-[10px] font-bold uppercase tracking-wider text-slate-400"><tr><th className="p-3">#</th><th className="p-3">Volunteer</th><th className="p-3 text-right">Hours</th><th className="p-3 text-right">Events</th><th className="p-3 text-right">Tasks done</th></tr></thead>
            <tbody>{data.items.map((r) => (
              <tr key={r.volunteer_id} className="border-t border-slate-100">
                <td className="p-3 font-extrabold text-purple-700">{r.rank}</td><td className="p-3 font-bold text-slate-900">{r.volunteer_name}<span className="block text-xs font-normal text-slate-500">{r.location}</span></td>
                <td className="p-3 text-right">{r.total_hours}</td><td className="p-3 text-right">{r.events_attended}</td><td className="p-3 text-right">{r.tasks_completed}</td>
              </tr>))}</tbody>
          </table>
        </div>
      )}
      <Pager data={data} page={page} onPage={setPage} />
    </section>
  );
}

function Donations() {
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(() => donationSummary({ page, page_size: 10 }), [page]);
  if (loading) return <Loading rows={2} />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <section className="space-y-3">
      <h2 className="font-display text-lg font-bold text-slate-900">Donations per campaign</h2>
      {data.items.length === 0 ? <EmptyState title="No donations yet" /> : (
        <div className="surface-card overflow-x-auto">
          <table className="w-full min-w-[480px] text-left text-sm">
            <thead className="text-[10px] font-bold uppercase tracking-wider text-slate-400"><tr><th className="p-3">Campaign</th><th className="p-3 text-right">Received</th><th className="p-3 text-right">Pending</th><th className="p-3 text-right">Donations</th><th className="p-3 text-right">Donors</th></tr></thead>
            <tbody>{data.items.map((r) => (
              <tr key={r.campaign_id ?? "none"} className="border-t border-slate-100">
                <td className="p-3 font-bold text-slate-900">{r.campaign_title}<span className="block text-xs font-normal text-slate-500">{Object.entries(r.by_type).map(([k, v]) => `${v} ${k.toLowerCase()}`).join(", ")}</span></td>
                <td className="p-3 text-right font-bold text-emerald-700">{money(r.money_received)}</td><td className="p-3 text-right text-amber-700">{money(r.money_pending)}</td>
                <td className="p-3 text-right">{r.donation_count}</td><td className="p-3 text-right">{r.donor_count}</td>
              </tr>))}</tbody>
          </table>
        </div>
      )}
      <Pager data={data} page={page} onPage={setPage} />
    </section>
  );
}

export default function Reports() {
  return (
    <div className="space-y-8">
      <h1 className="font-display text-2xl font-bold text-slate-900">Reports</h1>
      <Performance />
      <Donations />
    </div>
  );
}

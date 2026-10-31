import { useState } from "react";

import { campaignReport, donationSummary, resourceUtilization, volunteerPerformance } from "../../api/impact";
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

function Campaigns() {
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(() => campaignReport({ page, page_size: 10 }), [page]);
  if (loading) return <Loading rows={2} />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <section className="space-y-3">
      <h2 className="font-display text-lg font-bold text-slate-900">Campaigns</h2>
      {data.items.length === 0 ? <EmptyState title="No campaigns yet" /> : (
        <div className="surface-card overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-[10px] font-bold uppercase tracking-wider text-slate-400"><tr><th className="p-3">Campaign</th><th className="p-3 text-right">Volunteers</th><th className="p-3 text-right">Events</th><th className="p-3 text-right">Hours</th><th className="p-3 text-right">Raised</th><th className="p-3 text-right">Stock given</th></tr></thead>
            <tbody>{data.items.map((r) => (
              <tr key={r.campaign_id} className="border-t border-slate-100">
                <td className="p-3 font-bold text-slate-900">{r.campaign_title}{r.is_emergency && <span className="ml-2 rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-extrabold uppercase text-rose-600">Emergency</span>}<span className="block text-xs font-normal text-slate-500">{r.ngo_name} · {r.status.toLowerCase()}</span></td>
                <td className="p-3 text-right">{r.accepted_volunteers}/{r.required_volunteers}</td><td className="p-3 text-right">{r.events}</td><td className="p-3 text-right">{r.volunteer_hours}</td>
                <td className="p-3 text-right">{money(r.money_received)}{r.donation_progress != null && <span className="block text-xs text-emerald-600">{r.donation_progress}% of goal</span>}</td>
                <td className="p-3 text-right">{r.resources_distributed}/{r.resources_total}</td>
              </tr>))}</tbody>
          </table>
        </div>
      )}
      <Pager data={data} page={page} onPage={setPage} />
    </section>
  );
}

function Resources() {
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(() => resourceUtilization({ page, page_size: 10 }), [page]);
  if (loading) return <Loading rows={2} />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <section className="space-y-3">
      <h2 className="font-display text-lg font-bold text-slate-900">Resource utilization</h2>
      {data.items.length === 0 ? <EmptyState title="No resources tracked" /> : (
        <ul className="space-y-2">
          {data.items.map((r) => (
            <li key={r.resource_id} className="surface-card p-4">
              <div className="flex justify-between text-sm font-bold text-slate-900"><span>{r.name} <span className="font-normal text-slate-500">· {r.campaign_title}</span></span><span>{r.quantity_allocated}/{r.quantity_total} {r.unit} · {r.utilization_percent}%</span></div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${r.utilization_percent}%` }} /></div>
            </li>
          ))}
        </ul>
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
      <Campaigns />
      <Donations />
      <Resources />
    </div>
  );
}

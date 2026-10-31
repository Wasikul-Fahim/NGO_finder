import { useState } from "react";

import { auditActions, listAuditLogs } from "../../api/admin";
import { EmptyState, ErrorState, Loading } from "../../components/AsyncState";
import { inputClass, primaryButton, secondaryButton } from "../../components/FormField";
import Pager from "../../components/Pager";
import useAsync from "../../hooks/useAsync";

const EMPTY = { q: "", action_type: "", date_from: "", date_to: "" };

export default function AuditLog() {
  const [filters, setFilters] = useState(EMPTY);
  const [applied, setApplied] = useState(EMPTY);
  const [page, setPage] = useState(1);
  const actions = useAsync(auditActions);
  const params = { page, page_size: 20, ...Object.fromEntries(Object.entries(applied).filter(([, v]) => v)) };
  const { data, loading, error, reload } = useAsync(() => listAuditLogs(params), [applied, page]);
  const set = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-2xl font-bold text-slate-900">Audit log</h1>
        <p className="mt-1 text-sm text-slate-500">A permanent, read-only record of admin actions. Entries can't be edited or deleted.</p>
      </div>
      <form className="surface-card grid gap-3 p-4 sm:grid-cols-5" onSubmit={(e) => { e.preventDefault(); setPage(1); setApplied(filters); }}>
        <input className={inputClass} placeholder="Search actor or entity" aria-label="Search" value={filters.q} onChange={set("q")} />
        <select className={inputClass} aria-label="Action" value={filters.action_type} onChange={set("action_type")}>
          <option value="">Any action</option>{(actions.data ?? []).map((a) => <option key={a} value={a}>{a.toLowerCase().replaceAll("_", " ")}</option>)}
        </select>
        <input className={inputClass} type="date" aria-label="From date" value={filters.date_from} onChange={set("date_from")} />
        <input className={inputClass} type="date" aria-label="To date" value={filters.date_to} onChange={set("date_to")} />
        <div className="flex gap-2"><button className={`${primaryButton} flex-1`}>Filter</button><button type="button" className={secondaryButton} onClick={() => { setFilters(EMPTY); setApplied(EMPTY); setPage(1); }}>Reset</button></div>
      </form>
      {loading ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data.items.length === 0 ? <EmptyState title="No entries" hint="Nothing matches those filters." /> : (
        <div className="surface-card overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-[10px] font-bold uppercase tracking-wider text-slate-400"><tr><th className="p-3">When</th><th className="p-3">Who</th><th className="p-3">Action</th><th className="p-3">Target</th><th className="p-3">Details</th></tr></thead>
            <tbody>
              {data.items.map((a) => (
                <tr key={a.id} className="border-t border-slate-100 align-top">
                  <td className="whitespace-nowrap p-3 text-xs text-slate-500">{new Date(`${a.timestamp}Z`).toLocaleString()}</td>
                  <td className="p-3 font-bold text-slate-900">{a.actor_name ?? "—"}</td>
                  <td className="p-3 font-semibold capitalize text-purple-700">{a.action_type.toLowerCase().replaceAll("_", " ")}</td>
                  <td className="p-3 text-xs text-slate-600">{a.entity_type}{a.entity_id ? ` #${a.entity_id}` : ""}</td>
                  <td className="max-w-xs p-3 text-xs text-slate-500">{Object.entries(a.details).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : String(v)}`).join(" · ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pager data={data} page={page} onPage={setPage} />
    </div>
  );
}

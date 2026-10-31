import { useState } from "react";
import { Link } from "react-router-dom";

import { listNotifications } from "../api/notifications";
import { EmptyState, ErrorState, Loading } from "../components/AsyncState";
import { PriorityDot } from "../components/NotificationBell";
import { inputClass, secondaryButton } from "../components/FormField";
import Pager from "../components/Pager";
import { useNotifications } from "../context/NotificationContext";
import useAsync from "../hooks/useAsync";

const TYPES = ["APPLICATION_UPDATE", "TASK_ASSIGNED", "TASK_UPDATE", "EVENT_REMINDER", "ATTENDANCE", "CAMPAIGN_UPDATE", "DONATION_UPDATE", "ANNOUNCEMENT", "EMERGENCY_ALERT"];

export default function Notifications() {
  const { unread, read, readAll } = useNotifications();
  const [filters, setFilters] = useState({ status: "", priority: "", notification_type: "" });
  const [page, setPage] = useState(1);
  const params = { page, page_size: 15, ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)) };
  const { data, loading, error, reload } = useAsync(() => listNotifications(params), [page, filters.status, filters.priority, filters.notification_type, unread]);
  const set = (k) => (e) => { setPage(1); setFilters((f) => ({ ...f, [k]: e.target.value })); };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-bold text-slate-900">Notifications</h1>
        <button className={secondaryButton} disabled={unread === 0} onClick={async () => { await readAll(); reload(); }}>Mark all read ({unread})</button>
      </div>
      <div className="surface-card grid gap-3 p-4 sm:grid-cols-3">
        <select className={inputClass} aria-label="Status" value={filters.status} onChange={set("status")}><option value="">All</option><option value="UNREAD">Unread</option><option value="READ">Read</option></select>
        <select className={inputClass} aria-label="Priority" value={filters.priority} onChange={set("priority")}><option value="">Any priority</option><option value="HIGH">High</option><option value="NORMAL">Normal</option><option value="LOW">Low</option></select>
        <select className={inputClass} aria-label="Type" value={filters.notification_type} onChange={set("notification_type")}><option value="">Any type</option>{TYPES.map((t) => <option key={t} value={t}>{t.replaceAll("_", " ").toLowerCase()}</option>)}</select>
      </div>
      {loading ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data.items.length === 0 ? (
        <EmptyState title="Nothing here" hint="Try different filters." />
      ) : (
        <ul className="space-y-2">
          {data.items.map((n) => (
            <li key={n.id} className={`surface-card flex gap-3 p-4 ${n.status === "UNREAD" ? "border-purple-200 bg-purple-50/30" : ""}`}>
              <PriorityDot priority={n.priority} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-extrabold text-slate-900">{n.title}</p>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-500">{n.notification_type.replaceAll("_", " ")}</span>
                </div>
                <p className="mt-1 text-sm text-slate-600">{n.message}</p>
                <p className="mt-1 text-[11px] text-slate-400">{new Date(`${n.created_at}Z`).toLocaleString()}</p>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1 text-xs font-bold">
                {n.link && <Link className="text-purple-700 hover:text-purple-900" to={n.link} onClick={() => n.status === "UNREAD" && read(n.id)}>Open</Link>}
                {n.status === "UNREAD" && <button className="text-slate-500 hover:text-slate-800" onClick={async () => { await read(n.id); reload(); }}>Mark read</button>}
              </div>
            </li>
          ))}
        </ul>
      )}
      <Pager data={data} page={page} onPage={setPage} />
    </div>
  );
}

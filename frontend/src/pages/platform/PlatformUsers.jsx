import { useState } from "react";

import { listUsers, updateUser } from "../../api/admin";
import { parseError } from "../../api/client";
import { EmptyState, ErrorState, Loading } from "../../components/AsyncState";
import { inputClass, primaryButton, secondaryButton } from "../../components/FormField";
import { ErrorNotice } from "../../components/Notice";
import Pager from "../../components/Pager";
import { useAuth } from "../../context/AuthContext";
import useAsync from "../../hooks/useAsync";

const ROLES = ["", "VOLUNTEER", "DONOR", "BENEFICIARY", "NGO_ADMIN", "PLATFORM_ADMIN"];

export default function PlatformUsers() {
  const { user: me } = useAuth();
  const [filters, setFilters] = useState({ q: "", role: "", is_active: "" });
  const [applied, setApplied] = useState(filters);
  const [page, setPage] = useState(1);
  const params = { page, page_size: 15, ...Object.fromEntries(Object.entries(applied).filter(([, v]) => v !== "")) };
  const { data, loading, error, reload } = useAsync(() => listUsers(params), [applied, page]);
  const [actionError, setActionError] = useState("");

  async function toggle(u) {
    const next = !u.is_active;
    if (!next && !window.confirm(`Deactivate ${u.name}? They will be signed out and unable to log in.`)) return;
    setActionError("");
    try { await updateUser(u.id, { is_active: next }); reload(); } catch (err) { setActionError(parseError(err).message); }
  }

  return (
    <div className="space-y-5">
      <h1 className="font-display text-2xl font-bold text-slate-900">Users</h1>
      <form className="surface-card grid gap-3 p-4 sm:grid-cols-4" onSubmit={(e) => { e.preventDefault(); setPage(1); setApplied(filters); }}>
        <input className={inputClass} placeholder="Search name or email" aria-label="Search" value={filters.q} onChange={(e) => setFilters({ ...filters, q: e.target.value })} />
        <select className={inputClass} aria-label="Role" value={filters.role} onChange={(e) => setFilters({ ...filters, role: e.target.value })}>{ROLES.map((r) => <option key={r} value={r}>{r || "Any role"}</option>)}</select>
        <select className={inputClass} aria-label="Active" value={filters.is_active} onChange={(e) => setFilters({ ...filters, is_active: e.target.value })}><option value="">Active &amp; inactive</option><option value="true">Active</option><option value="false">Inactive</option></select>
        <button className={primaryButton}>Filter</button>
      </form>
      <ErrorNotice>{actionError}</ErrorNotice>
      {loading ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data.items.length === 0 ? <EmptyState title="No users match" /> : (
        <ul className="space-y-2">
          {data.items.map((u) => (
            <li key={u.id} className="surface-card flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="font-bold text-slate-900">{u.name} {!u.is_active && <span className="ml-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-extrabold uppercase text-slate-500">Inactive</span>}</p>
                <p className="truncate text-xs text-slate-500">{u.email} · {u.role.replace("_", " ")}{u.ngo_name ? ` · ${u.ngo_name} (${u.ngo_status.toLowerCase()})` : ""}</p>
              </div>
              <button className={secondaryButton} disabled={u.id === me.id} title={u.id === me.id ? "You can't deactivate yourself" : undefined} onClick={() => toggle(u)}>{u.is_active ? "Deactivate" : "Reactivate"}</button>
            </li>
          ))}
        </ul>
      )}
      <Pager data={data} page={page} onPage={setPage} />
    </div>
  );
}

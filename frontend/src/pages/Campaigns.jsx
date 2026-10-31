import { Calendar, Flame, MapPin, Users } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { listCampaigns } from "../api/campaigns";
import { EmptyState, ErrorState, Loading } from "../components/AsyncState";
import { inputClass, primaryButton } from "../components/FormField";
import { money } from "../components/Notice";
import Pager from "../components/Pager";
import { useAuth } from "../context/AuthContext";
import useAsync from "../hooks/useAsync";

export default function Campaigns() {
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(
    () => listCampaigns({ page, page_size: 12, ...(query ? { q: query } : {}) }), [page, query]);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-slate-900">Campaigns</h1>
        <p className="mt-1 text-sm text-slate-500">Causes run by verified NGOs.</p>
      </div>
      <form className="surface-card flex gap-3 p-4" onSubmit={(e) => { e.preventDefault(); setPage(1); setQuery(q); }}>
        <input className={inputClass} placeholder="Search campaigns" aria-label="Search campaigns" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className={primaryButton}>Search</button>
      </form>
      {loading ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data.items.length === 0 ? (
        <EmptyState title="No campaigns found" hint="Try a different search." />
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {data.items.map((c) => (
            <article key={c.id} className="surface-card flex flex-col p-5">
              <div className="flex items-center gap-2">
                {c.is_emergency && <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-extrabold uppercase text-rose-600"><Flame size={11} />Emergency</span>}
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-extrabold uppercase ${c.status === "ACTIVE" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>{c.status}</span>
              </div>
              <h3 className="mt-3 font-display text-base font-bold text-slate-900">{c.title}</h3>
              <p className="mt-0.5 text-xs font-semibold text-purple-700">{c.ngo_name}</p>
              {c.description && <p className="mt-3 line-clamp-3 text-sm text-slate-600">{c.description}</p>}
              <div className="mt-4 space-y-1.5 text-xs text-slate-500">
                {c.location && <p className="flex items-center gap-1.5"><MapPin size={13} />{c.location}</p>}
                <p className="flex items-center gap-1.5"><Calendar size={13} />{c.start_date} → {c.end_date}</p>
                <p className="flex items-center gap-1.5"><Users size={13} />{c.required_volunteers} volunteers needed</p>
              </div>
              {c.donation_goal ? (
                <div className="mt-4">
                  <div className="flex items-end justify-between text-xs font-bold text-slate-600"><span>{money(c.donations_received)} raised</span><span className="text-emerald-600">{c.donation_progress}%</span></div>
                  <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${c.donation_progress}%` }} /></div>
                  <p className="mt-1 text-[11px] text-slate-400">Goal {money(c.donation_goal)}</p>
                </div>
              ) : null}
              <div className="mt-auto flex gap-2 pt-5">
                {user.role === "DONOR" && c.status === "ACTIVE" && <Link to={`/donations?campaign=${c.id}`} className={`${primaryButton} flex-1`}>Donate</Link>}
                {user.role === "VOLUNTEER" && <Link to="/opportunities" className={`${primaryButton} flex-1`}>Find a role</Link>}
              </div>
            </article>
          ))}
        </div>
      )}
      <Pager data={data} page={page} onPage={setPage} />
    </div>
  );
}

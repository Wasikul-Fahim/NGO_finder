import { useState } from "react";
import { Link } from "react-router-dom";

import { applyTo, getRecommended, listOpportunities } from "../api/opportunities";
import { parseError } from "../api/client";
import { EmptyState, ErrorState, Loading } from "../components/AsyncState";
import { ChipList } from "../components/Chips";
import { inputClass, primaryButton, secondaryButton } from "../components/FormField";
import { useAuth } from "../context/AuthContext";
import useAsync from "../hooks/useAsync";

function MatchBadge({ match }) {
  const tone = match.percentage >= 70 ? "bg-emerald-50 text-emerald-700" : match.percentage >= 40 ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-500";
  return <span className={`rounded-full px-2.5 py-1 text-xs font-extrabold ${tone}`} title={Object.entries(match.breakdown).map(([k, v]) => `${k}: ${Math.round(v * 100)}%`).join(" · ")}>{match.percentage}% match</span>;
}

function OpportunityCard({ opportunity: o, match, applied, canApply }) {
  const [state, setState] = useState({ busy: false, error: "", done: applied, needsPhone: false });
  async function apply() {
    setState({ busy: true, error: "", done: false });
    try { await applyTo(o.id); setState({ busy: false, error: "", done: true }); }
    catch (err) { const e = parseError(err); setState({ busy: false, error: e.message, needsPhone: !!e.fields.phone, done: e.status === 409 && !e.fields.phone }); }
  }
  return (
    <article className="surface-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-display text-base font-bold text-slate-900">{o.title}</h3>
          <p className="mt-0.5 text-xs font-semibold text-purple-700">{o.ngo_name}{o.campaign_title ? ` · ${o.campaign_title}` : ""}</p>
        </div>
        {match && <MatchBadge match={match} />}
      </div>
      {o.description && <p className="mt-3 text-sm leading-6 text-slate-600">{o.description}</p>}
      <p className="mt-3 text-xs text-slate-500">{o.location || "Location flexible"}{o.availability.length ? ` · ${o.availability.join(", ")}` : ""}</p>
      <div className="mt-3"><ChipList items={o.required_skills} /></div>
      {match && <p className="mt-3 text-xs text-slate-500"><span className="font-bold text-slate-600">Why: </span>{match.reasons.join(" · ")}</p>}
      {canApply && (
        <div className="mt-4 flex items-center gap-3">
          <button className={state.done ? secondaryButton : primaryButton} disabled={state.busy || state.done} onClick={apply}>
            {state.done ? "Applied ✓" : state.busy ? "Applying…" : "Apply"}
          </button>
          {state.error && <span role="alert" className="text-xs font-semibold text-rose-600">{state.error}{state.needsPhone && <> <Link className="underline" to="/profile">Add it now</Link></>}</span>}
        </div>
      )}
    </article>
  );
}

function Recommended() {
  const { data, loading, error, reload } = useAsync(() => getRecommended(9));
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (data.length === 0) return <EmptyState title="Nothing to recommend yet" hint="No open opportunities right now. Check back soon." />;
  const noProfile = data.every((r) => r.match.percentage === 0);
  return (
    <div className="space-y-4">
      {noProfile && <p className="rounded-lg bg-amber-50 px-3 py-2.5 text-sm text-amber-800">Add skills, interests, availability and your city in <Link className="font-bold underline" to="/profile">your profile</Link> to get ranked matches.</p>}
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {data.map((r) => <OpportunityCard key={r.opportunity.id} opportunity={r.opportunity} match={r.match} applied={r.has_applied} canApply />)}
      </div>
    </div>
  );
}

function Browse({ canApply }) {
  const [filters, setFilters] = useState({ q: "", location: "", skill: "" });
  const [applied, setApplied] = useState(filters);
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(
    () => listOpportunities({ ...Object.fromEntries(Object.entries(applied).filter(([, v]) => v)), page, page_size: 12 }),
    [applied, page],
  );
  const set = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value }));
  return (
    <div className="space-y-5">
      <form className="surface-card grid gap-3 p-4 sm:grid-cols-4" onSubmit={(e) => { e.preventDefault(); setPage(1); setApplied(filters); }}>
        <input className={inputClass} placeholder="Search title or description" value={filters.q} onChange={set("q")} aria-label="Search" />
        <input className={inputClass} placeholder="Location" value={filters.location} onChange={set("location")} aria-label="Location" />
        <input className={inputClass} placeholder="Skill" value={filters.skill} onChange={set("skill")} aria-label="Skill" />
        <button className={primaryButton}>Search</button>
      </form>
      {loading ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data.items.length === 0 ? (
        <EmptyState title="No opportunities match" hint="Try clearing a filter." />
      ) : (
        <>
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {data.items.map((o) => <OpportunityCard key={o.id} opportunity={o} canApply={canApply} />)}
          </div>
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-3">
              <button className={secondaryButton} disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
              <span className="text-xs font-bold text-slate-500">Page {data.page} of {data.pages}</span>
              <button className={secondaryButton} disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Next</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function Opportunities() {
  const { user } = useAuth();
  const isVolunteer = user.role === "VOLUNTEER";
  const [tab, setTab] = useState(isVolunteer ? "recommended" : "browse");
  const tabClass = (name) => `rounded-lg px-4 py-2 text-sm font-bold transition ${tab === name ? "bg-[#6b21a8] text-white" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:ring-purple-300"}`;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="font-display text-2xl font-bold text-slate-900">Volunteer opportunities</h1>
        {isVolunteer && (
          <div className="flex gap-2">
            <button className={tabClass("recommended")} onClick={() => setTab("recommended")}>Recommended for you</button>
            <button className={tabClass("browse")} onClick={() => setTab("browse")}>Browse all</button>
          </div>
        )}
      </div>
      {tab === "recommended" && isVolunteer ? <Recommended /> : <Browse canApply={isVolunteer} />}
    </div>
  );
}

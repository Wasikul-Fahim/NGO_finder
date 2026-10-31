import { Filter, Search, SlidersHorizontal, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";

import OpportunityCard from "../components/OpportunityCard";
import { opportunities } from "../data/dashboardData";

const locations = ["All locations", "Dhaka", "Sylhet", "Rangpur", "Online"];

export default function Opportunities() {
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("All locations");
  const [highMatch, setHighMatch] = useState(false);
  const filtered = useMemo(() => opportunities.filter((opportunity) => {
    const searchable = `${opportunity.title} ${opportunity.ngo} ${opportunity.skills.join(" ")}`.toLowerCase();
    const matchesQuery = searchable.includes(query.toLowerCase());
    const matchesLocation = location === "All locations" || opportunity.location.toLowerCase().includes(location.toLowerCase());
    const matchesScore = !highMatch || opportunity.match >= 94;
    return matchesQuery && matchesLocation && matchesScore;
  }), [query, location, highMatch]);

  return <div className="space-y-7"><section className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end"><div><div className="mb-3 inline-flex items-center gap-2 rounded-full bg-purple-50 px-3 py-1.5 text-[10px] font-extrabold uppercase tracking-wider text-purple-700"><Sparkles size={12} />12 opportunities matched to you</div><h1 className="font-display text-3xl font-bold tracking-[-0.05em] text-slate-900">Find your next impact</h1><p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">Explore volunteer roles where your skills, interests, and availability can make a meaningful difference.</p></div><button className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs font-extrabold text-slate-700 shadow-sm hover:border-purple-200 hover:text-purple-700"><SlidersHorizontal size={16} /> Saved preferences</button></section>
    <section className="surface-card flex flex-col gap-3 p-4 md:flex-row"><label className="relative min-w-0 flex-1"><Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" /><input value={query} onChange={(event) => setQuery(event.target.value)} className="h-11 w-full rounded-lg border border-slate-200 bg-slate-50 pl-10 pr-3 text-sm outline-none focus:border-purple-400 focus:bg-white" placeholder="Search by role, NGO, or skill" /></label><label className="relative"><Filter size={15} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" /><select value={location} onChange={(event) => setLocation(event.target.value)} className="h-11 w-full appearance-none rounded-lg border border-slate-200 bg-slate-50 pl-10 pr-9 text-xs font-bold text-slate-600 outline-none focus:border-purple-400 md:w-44">{locations.map((item) => <option key={item}>{item}</option>)}</select></label><button onClick={() => setHighMatch((value) => !value)} className={`rounded-lg px-4 text-xs font-extrabold transition ${highMatch ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200" : "border border-slate-200 bg-white text-slate-600 hover:border-purple-200"}`}>{highMatch ? "High matches only ✓" : "98%+ matches"}</button></section>
    <div className="flex items-center justify-between"><p className="text-xs font-semibold text-slate-500"><strong className="text-slate-800">{filtered.length}</strong> roles available</p><p className="text-[11px] font-bold text-slate-400">Sorted by match score</p></div>
    {filtered.length > 0 ? <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{filtered.map((opportunity) => <OpportunityCard key={opportunity.id} opportunity={opportunity} />)}</div> : <div className="surface-card flex min-h-60 flex-col items-center justify-center p-8 text-center"><span className="mb-3 grid h-12 w-12 place-items-center rounded-full bg-slate-100 text-slate-400"><Search size={20} /></span><h2 className="font-display text-lg font-bold text-slate-800">No matching roles found</h2><p className="mt-2 max-w-sm text-sm text-slate-500">Try a different search term or clear one of the filters.</p></div>}
  </div>;
}

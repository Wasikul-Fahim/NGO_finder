import { useState } from "react";
import { Clock3, MapPin, MoreHorizontal, Sparkles } from "lucide-react";

export default function OpportunityCard({ opportunity, compact = false }) {
  const [applied, setApplied] = useState(false);

  return (
    <article className={`surface-card group flex h-full flex-col p-5 transition duration-300 hover:-translate-y-1 hover:border-purple-200 hover:shadow-xl hover:shadow-purple-900/7 ${compact ? "min-w-[290px]" : ""}`}>
      <div className="flex items-start justify-between gap-3">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1.5 text-[10px] font-extrabold uppercase tracking-wider text-emerald-700 ring-1 ring-emerald-200/70"><Sparkles size={12} />{opportunity.match}% match</span>
        <button className="rounded-lg p-1 text-slate-300 transition hover:bg-slate-50 hover:text-slate-600" aria-label="More opportunity options"><MoreHorizontal size={18} /></button>
      </div>
      <div className="mt-4 flex-1">
        <h3 className="font-display text-[16px] font-bold leading-6 tracking-[-0.025em] text-slate-900">{opportunity.title}</h3>
        <p className="mt-1 text-xs font-semibold text-purple-700">{opportunity.ngo}</p>
        {!compact && <p className="mt-3 text-xs leading-5 text-slate-500">{opportunity.description}</p>}
        <div className="mt-4 flex flex-wrap gap-x-3 gap-y-2 text-[11px] font-semibold text-slate-500"><span className="inline-flex items-center gap-1"><MapPin size={13} className="text-slate-400" />{opportunity.location}</span><span className="inline-flex items-center gap-1"><Clock3 size={13} className="text-slate-400" />{opportunity.commitment}</span></div>
        <div className="mt-4 flex flex-wrap gap-1.5">{opportunity.skills.map((skill) => <span key={skill} className="rounded-md bg-slate-100 px-2 py-1 text-[10px] font-bold text-slate-600">{skill}</span>)}</div>
      </div>
      <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4"><span className={`text-[10px] font-bold ${opportunity.urgent ? "text-amber-600" : "text-slate-400"}`}>{opportunity.urgent ? "Urgent response role" : "Recommended for you"}</span><button onClick={() => setApplied((value) => !value)} className={`rounded-lg px-3.5 py-2 text-[11px] font-extrabold transition ${applied ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200" : "bg-[#f59e0b] text-[#3b1d06] shadow-sm shadow-amber-200 hover:bg-[#fbbf24]"}`}>{applied ? "Application sent" : "Apply now"}</button></div>
    </article>
  );
}

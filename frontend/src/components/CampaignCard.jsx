import { Flame, HeartHandshake, Users } from "lucide-react";

export default function CampaignCard({ campaign }) {
  const percentage = Math.round((campaign.raised / campaign.goal) * 100);
  return (
    <article className="surface-card overflow-hidden p-5 transition duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-purple-900/5">
      <div className="flex items-start justify-between gap-3"><div><div className="flex items-center gap-2">{campaign.urgent && <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-1 text-[9px] font-extrabold uppercase tracking-wider text-rose-600"><Flame size={11} />Urgent</span>}<span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{campaign.days} days left</span></div><h3 className="mt-3 font-display text-[16px] font-bold tracking-[-0.03em] text-slate-900">{campaign.title}</h3><p className="mt-1 text-[11px] font-semibold text-purple-700">{campaign.ngo}</p></div><div className={`grid h-10 w-10 place-items-center rounded-xl ${campaign.color === "purple" ? "bg-purple-50 text-purple-700" : campaign.color === "teal" ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"}`}><HeartHandshake size={18} /></div></div>
      <div className="mt-6 flex items-end justify-between"><div><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Raised so far</p><p className="mt-1 font-display text-lg font-extrabold tracking-[-0.04em] text-slate-900">৳{campaign.raised.toLocaleString()}</p></div><span className="font-display text-sm font-extrabold text-emerald-600">{percentage}%</span></div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full ${campaign.color === "purple" ? "bg-purple-600" : campaign.color === "teal" ? "bg-emerald-500" : "bg-amber-400"}`} style={{ width: `${percentage}%` }} /></div>
      <div className="mt-4 flex items-center justify-between text-[11px] font-semibold text-slate-500"><span className="flex items-center gap-1.5"><Users size={14} className="text-slate-400" />{campaign.volunteers} volunteers</span><span>Goal ৳{campaign.goal.toLocaleString()}</span></div>
      <div className="mt-5 flex gap-2"><button className="flex-1 rounded-lg bg-[#6b21a8] py-2.5 text-[11px] font-extrabold text-white transition hover:bg-[#581c87]">Donate funds</button><button className="flex-1 rounded-lg border border-slate-200 bg-white py-2.5 text-[11px] font-extrabold text-slate-700 transition hover:border-purple-300 hover:text-purple-700">Volunteer</button></div>
    </article>
  );
}

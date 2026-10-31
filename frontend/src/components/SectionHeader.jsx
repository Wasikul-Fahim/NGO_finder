import { ArrowUpRight } from "lucide-react";

export default function SectionHeader({ eyebrow, title, action, onAction }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">{eyebrow}</p><h2 className="mt-1.5 font-display text-[19px] font-bold tracking-[-0.035em] text-slate-900">{title}</h2></div>
      {action && <button onClick={onAction} className="group flex shrink-0 items-center gap-1 text-xs font-bold text-purple-700 hover:text-purple-900">{action}<ArrowUpRight size={14} className="transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" /></button>}
    </div>
  );
}

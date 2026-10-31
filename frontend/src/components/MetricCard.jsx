const toneStyles = {
  purple: { icon: "bg-purple-50 text-purple-700", line: "bg-purple-500" },
  amber: { icon: "bg-amber-50 text-amber-600", line: "bg-amber-400" },
  blue: { icon: "bg-blue-50 text-blue-600", line: "bg-blue-500" },
  teal: { icon: "bg-emerald-50 text-emerald-600", line: "bg-emerald-500" },
};

export default function MetricCard({ metric }) {
  const Icon = metric.icon;
  const styles = toneStyles[metric.tone] || toneStyles.purple;

  return (
    <article className="surface-card group relative overflow-hidden p-5 transition duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-purple-900/5">
      <div className="flex items-start justify-between gap-3">
        <div><p className="text-[11px] font-bold uppercase tracking-[0.12em] text-slate-400">{metric.label}</p><p className="mt-3 font-display text-[29px] font-extrabold tracking-[-0.05em] text-slate-900">{metric.value}</p></div>
        <span className={`grid h-10 w-10 place-items-center rounded-xl ${styles.icon}`}><Icon size={19} strokeWidth={2} /></span>
      </div>
      <p className="mt-3 flex items-center gap-1.5 text-[11px] font-bold text-emerald-600"><span className="text-emerald-500">↗</span>{metric.delta}</p>
      <span className={`absolute bottom-0 left-0 h-0.5 w-0 ${styles.line} transition-all duration-500 group-hover:w-full`} />
    </article>
  );
}

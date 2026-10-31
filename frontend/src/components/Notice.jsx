export function ErrorNotice({ children }) {
  return children ? <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{children}</p> : null;
}

export function SuccessNotice({ children }) {
  return children ? <p role="status" className="rounded-lg bg-emerald-50 px-3 py-2.5 text-sm font-semibold text-emerald-700">{children}</p> : null;
}

export function Stat({ label, value, hint }) {
  return (
    <div className="surface-card p-5">
      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</p>
      <p className="mt-2 font-display text-3xl font-extrabold tracking-tight text-slate-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

export const money = (n) => `৳${Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

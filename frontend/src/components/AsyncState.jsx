export function Loading({ rows = 3 }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-100" />)}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div role="alert" className="surface-card flex flex-col items-center gap-3 p-8 text-center">
      <p className="text-sm font-semibold text-rose-700">{message}</p>
      {onRetry && <button onClick={onRetry} className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-bold text-slate-700 hover:border-purple-300">Try again</button>}
    </div>
  );
}

export function EmptyState({ title, hint, action }) {
  return (
    <div className="surface-card p-10 text-center">
      <p className="font-display text-base font-bold text-slate-900">{title}</p>
      {hint && <p className="mt-1 text-sm text-slate-500">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

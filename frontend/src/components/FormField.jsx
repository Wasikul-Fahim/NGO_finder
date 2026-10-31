export default function FormField({ label, error, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-bold text-slate-700">{label}</span>
      {children}
      {error && <span role="alert" className="mt-1 block text-xs font-semibold text-rose-600">{error}</span>}
    </label>
  );
}

export const inputClass =
  "h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none transition focus:border-purple-400 focus:ring-4 focus:ring-purple-100";
export const textareaClass =
  "w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-purple-400 focus:ring-4 focus:ring-purple-100";
export const primaryButton =
  "inline-flex h-11 items-center justify-center rounded-lg bg-[#6b21a8] px-5 text-sm font-bold text-white transition hover:bg-[#581c87] disabled:opacity-60";
export const secondaryButton =
  "inline-flex h-11 items-center justify-center rounded-lg border border-slate-200 bg-white px-5 text-sm font-bold text-slate-700 transition hover:border-purple-300 hover:text-purple-700 disabled:opacity-60";

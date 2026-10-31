export const DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];

/** Comma-separated text <-> string[]. */
export const toList = (text) => text.split(",").map((s) => s.trim()).filter(Boolean);

export function ChipList({ items, tone = "purple" }) {
  if (!items?.length) return null;
  const color = tone === "slate" ? "bg-slate-100 text-slate-600" : "bg-purple-50 text-purple-700";
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => <span key={item} className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${color}`}>{item}</span>)}
    </div>
  );
}

export function DayPicker({ value, onChange }) {
  const toggle = (day) => onChange(value.includes(day) ? value.filter((d) => d !== day) : [...value, day]);
  return (
    <div className="flex flex-wrap gap-2">
      {DAYS.map((day) => (
        <button type="button" key={day} onClick={() => toggle(day)} aria-pressed={value.includes(day)}
          className={`h-9 rounded-lg px-3 text-xs font-bold ring-1 transition ${value.includes(day) ? "bg-[#6b21a8] text-white ring-[#6b21a8]" : "bg-white text-slate-600 ring-slate-200 hover:ring-purple-300"}`}>
          {day}
        </button>
      ))}
    </div>
  );
}

const STATUS_TONE = {
  SUBMITTED: "bg-slate-100 text-slate-600", UNDER_REVIEW: "bg-amber-50 text-amber-700",
  ACCEPTED: "bg-emerald-50 text-emerald-700", REJECTED: "bg-rose-50 text-rose-700",
  PENDING: "bg-amber-50 text-amber-700", IN_PROGRESS: "bg-blue-50 text-blue-700",
  COMPLETED: "bg-emerald-50 text-emerald-700", ACTIVE: "bg-blue-50 text-blue-700", RECEIVED: "bg-emerald-50 text-emerald-700", DECLINED: "bg-rose-50 text-rose-700",
};

export function StatusPill({ status }) {
  return <span className={`rounded-full px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wider ${STATUS_TONE[status] || "bg-slate-100 text-slate-600"}`}>{status.replace("_", " ")}</span>;
}

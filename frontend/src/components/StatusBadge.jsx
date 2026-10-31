const statusStyles = {
  Pending: "bg-amber-50 text-amber-700 ring-amber-200/70",
  "In Progress": "bg-blue-50 text-blue-700 ring-blue-200/70",
  Completed: "bg-emerald-50 text-emerald-700 ring-emerald-200/70",
};

export default function StatusBadge({ status }) {
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wider ring-1 ${statusStyles[status] || "bg-slate-50 text-slate-600 ring-slate-200"}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{status}</span>;
}

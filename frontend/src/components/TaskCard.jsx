import { Check, Clock3, MoreHorizontal } from "lucide-react";

import StatusBadge from "./StatusBadge";

export default function TaskCard({ task, onComplete, compact = false }) {
  const completed = task.status === "Completed";
  return (
    <article className={`rounded-xl border border-slate-100 bg-white p-4 transition hover:border-purple-100 hover:shadow-md hover:shadow-purple-900/5 ${compact ? "" : "p-5"}`}>
      <div className="flex items-start justify-between gap-3"><div className="min-w-0"><h3 className="truncate text-[13px] font-bold text-slate-800">{task.title}</h3><p className="mt-1 text-[11px] font-semibold text-purple-700">{task.ngo}</p></div><button className="shrink-0 text-slate-300 hover:text-slate-600" aria-label="More task options"><MoreHorizontal size={17} /></button></div>
      <div className="mt-4 flex items-center justify-between gap-3"><StatusBadge status={task.status} /><span className="flex items-center gap-1 text-[10px] font-semibold text-slate-400"><Clock3 size={12} />{task.due}</span></div>
      <div className="mt-4"><div className="mb-1.5 flex justify-between text-[10px] font-bold text-slate-400"><span>Progress</span><span className={completed ? "text-emerald-600" : "text-slate-500"}>{task.progress}%</span></div><div className="h-1.5 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full transition-all ${completed ? "bg-emerald-500" : task.status === "In Progress" ? "bg-blue-500" : "bg-amber-400"}`} style={{ width: `${task.progress}%` }} /></div></div>
      {compact ? <button disabled={completed} onClick={() => onComplete?.(task.id)} className={`mt-3 ml-auto flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-extrabold transition ${completed ? "cursor-default bg-emerald-50 text-emerald-700" : "bg-slate-50 text-slate-500 hover:bg-emerald-50 hover:text-emerald-700"}`} aria-label={completed ? "Task completed" : "Mark task completed"}>{completed ? <><Check size={12} />Done</> : "Mark done"}</button> : <button disabled={completed} onClick={() => onComplete?.(task.id)} className={`mt-4 flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-[11px] font-extrabold transition ${completed ? "cursor-default bg-emerald-50 text-emerald-700" : "bg-slate-900 text-white hover:bg-purple-800"}`}>{completed ? <><Check size={14} />Done</> : "Mark completed"}</button>}
    </article>
  );
}

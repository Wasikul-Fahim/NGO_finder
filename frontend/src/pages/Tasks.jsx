import { CheckCircle2, CircleDashed, ListFilter, TimerReset } from "lucide-react";
import { useMemo, useState } from "react";

import TaskCard from "../components/TaskCard";
import { tasks } from "../data/dashboardData";

const filters = ["All tasks", "Pending", "In Progress", "Completed"];

export default function Tasks() {
  const [filter, setFilter] = useState("All tasks");
  const [taskList, setTaskList] = useState(tasks);
  const filtered = useMemo(() => filter === "All tasks" ? taskList : taskList.filter((task) => task.status === filter), [filter, taskList]);
  const completeTask = (taskId) => setTaskList((current) => current.map((task) => task.id === taskId ? { ...task, status: "Completed", progress: 100 } : task));
  const count = (status) => taskList.filter((task) => task.status === status).length;
  return <div className="space-y-7"><section className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end"><div><h1 className="font-display text-3xl font-bold tracking-[-0.05em] text-slate-900">Your task board</h1><p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">Stay on top of the small actions that create a big community impact.</p></div><div className="flex items-center gap-2 text-xs font-bold text-slate-400"><TimerReset size={16} /> 2 due this week</div></section><section className="grid gap-4 sm:grid-cols-3"><div className="surface-card flex items-center gap-3 p-4"><span className="grid h-10 w-10 place-items-center rounded-xl bg-amber-50 text-amber-600"><CircleDashed size={18} /></span><div><p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Pending</p><p className="mt-1 font-display text-xl font-bold text-slate-900">{count("Pending")}</p></div></div><div className="surface-card flex items-center gap-3 p-4"><span className="grid h-10 w-10 place-items-center rounded-xl bg-blue-50 text-blue-600"><ListFilter size={18} /></span><div><p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">In progress</p><p className="mt-1 font-display text-xl font-bold text-slate-900">{count("In Progress")}</p></div></div><div className="surface-card flex items-center gap-3 p-4"><span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 text-emerald-600"><CheckCircle2 size={18} /></span><div><p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Completed</p><p className="mt-1 font-display text-xl font-bold text-slate-900">{count("Completed")}</p></div></div></section><div className="flex flex-wrap gap-2">{filters.map((item) => <button key={item} onClick={() => setFilter(item)} className={`rounded-full px-4 py-2 text-[11px] font-extrabold transition ${filter === item ? "bg-[#6b21a8] text-white shadow-md shadow-purple-200" : "bg-white text-slate-500 ring-1 ring-slate-200 hover:text-purple-700"}`}>{item}</button>)}</div><div className="grid gap-4 md:grid-cols-2">{filtered.map((task) => <TaskCard key={task.id} task={task} onComplete={completeTask} />)}</div>{filtered.length === 0 && <div className="surface-card p-12 text-center text-sm font-semibold text-slate-500">No tasks in this group yet.</div>}</div>;
}

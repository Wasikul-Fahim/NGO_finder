import { ArrowRight, CalendarDays, Sparkles, WalletCards } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useState } from "react";

import CampaignCard from "../components/CampaignCard";
import MetricCard from "../components/MetricCard";
import OpportunityCard from "../components/OpportunityCard";
import SectionHeader from "../components/SectionHeader";
import TaskCard from "../components/TaskCard";
import { campaigns, metrics, opportunities, tasks } from "../data/dashboardData";

export default function Dashboard() {
  const navigate = useNavigate();
  const [taskList, setTaskList] = useState(tasks);

  const completeTask = (taskId) => {
    setTaskList((current) => current.map((task) => task.id === taskId ? { ...task, status: "Completed", progress: 100 } : task));
  };

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#4c176f] via-[#6b21a8] to-[#8b3fc1] px-6 py-7 text-white shadow-xl shadow-purple-900/15 sm:px-8 sm:py-8">
        <div className="absolute -right-10 -top-20 h-64 w-64 rounded-full border-[28px] border-white/5" /><div className="absolute -bottom-36 right-24 h-72 w-72 rounded-full border-[34px] border-white/5" />
        <div className="relative z-10 flex flex-col justify-between gap-7 md:flex-row md:items-end"><div><p className="mb-3 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.15em] text-purple-100"><Sparkles size={12} />Tuesday, October 01, 2024</p><h1 className="max-w-xl font-display text-[27px] font-bold leading-tight tracking-[-0.045em] sm:text-[31px]">Good morning, Wasikul <span className="text-amber-300">👋</span></h1><p className="mt-3 max-w-lg text-sm leading-6 text-purple-100">You have <strong className="text-white">4 assigned tasks</strong> and <strong className="text-white">3 new high-match opportunities</strong> waiting for you today.</p></div><button onClick={() => navigate("/opportunities")} className="group inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-[#f59e0b] px-5 py-3 text-xs font-extrabold text-[#3b1d06] shadow-lg shadow-amber-950/20 transition hover:bg-[#fbbf24]">Find opportunities <ArrowRight size={15} className="transition group-hover:translate-x-1" /></button></div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map((metric) => <MetricCard key={metric.label} metric={metric} />)}</section>

      <section>
        <SectionHeader eyebrow="Personalized for your profile" title="Smart volunteer matching" action="View all opportunities" onAction={() => navigate("/opportunities")} />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{opportunities.slice(0, 4).map((opportunity) => <OpportunityCard key={opportunity.id} opportunity={opportunity} compact />)}</div>
      </section>

      <section className="grid gap-8 xl:grid-cols-[1.05fr_1.5fr]">
        <div><SectionHeader eyebrow="Keep your momentum going" title="Assigned tasks" action="View all tasks" onAction={() => navigate("/tasks")} /><div className="space-y-3">{taskList.slice(0, 3).map((task) => <TaskCard key={task.id} task={task} compact onComplete={completeTask} />)}</div></div>
        <div><SectionHeader eyebrow="Support the causes you care about" title="Active campaigns & relief" action="Explore campaigns" onAction={() => navigate("/campaigns")} /><div className="grid gap-4 md:grid-cols-2">{campaigns.slice(0, 2).map((campaign) => <CampaignCard key={campaign.id} campaign={campaign} />)}</div></div>
      </section>

      <section className="grid gap-4 md:grid-cols-3"><div className="surface-card flex items-center gap-4 p-5 md:col-span-2"><div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-purple-50 text-purple-700"><CalendarDays size={21} /></div><div><p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Next on your calendar</p><h3 className="mt-1 text-sm font-bold text-slate-800">Volunteer orientation · Thursday, 10:00 AM</h3><p className="mt-1 text-xs font-medium text-slate-400">Shobuj Foundation · Online session</p></div><button className="ml-auto hidden text-xs font-bold text-purple-700 hover:text-purple-900 sm:block">View event</button></div><div className="surface-card flex items-center gap-4 p-5"><div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-600"><WalletCards size={21} /></div><div><p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Your impact</p><h3 className="mt-1 text-sm font-bold text-slate-800">340+ people reached</h3><p className="mt-1 text-xs font-medium text-emerald-600">Keep making a difference ↗</p></div></div></section>
    </div>
  );
}

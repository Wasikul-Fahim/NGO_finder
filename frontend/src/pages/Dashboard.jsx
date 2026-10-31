import { ArrowRight, CalendarDays, CheckCircle2, Clock, HeartHandshake, ListTodo, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { myEvents } from "../api/campaigns";
import { myContributions } from "../api/impact";
import { getMyProfile, getRecommended, myTasks } from "../api/opportunities";
import { listNotifications } from "../api/notifications";
import { ErrorState, Loading } from "../components/AsyncState";
import { StatusPill } from "../components/Chips";
import { Stat } from "../components/Notice";
import { useAuth } from "../context/AuthContext";
import useAsync from "../hooks/useAsync";

/** Volunteer home: everything comes from the API (no demo numbers). */
export default function Dashboard() {
  const { user } = useAuth();
  const { data, loading, error, reload } = useAsync(async () => {
    const [profile, impact, tasks, picks, events, alerts] = await Promise.all([
      getMyProfile(), myContributions(), myTasks({ page_size: 20 }), getRecommended(3), myEvents({ page_size: 3 }),
      listNotifications({ priority: "HIGH", status: "UNREAD", page_size: 3 }),
    ]);
    return { profile, impact, tasks, picks, events, alerts };
  });
  if (loading) return <Loading rows={4} />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const { profile, impact, tasks, picks, events, alerts } = data;
  const open = tasks.items.filter((t) => ["PENDING", "ACCEPTED", "IN_PROGRESS"].includes(t.status));

  return (
    <div className="space-y-6">
      <section className="rounded-2xl bg-gradient-to-br from-[#3b1d5a] to-[#6b21a8] p-6 text-white sm:p-8">
        <p className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.15em]"><Sparkles size={12} />Welcome back</p>
        <h1 className="mt-3 font-display text-2xl font-bold sm:text-3xl">Hello, {user.name.split(" ")[0]} 👋</h1>
        <p className="mt-2 text-sm text-purple-100">
          You have <strong className="text-white">{open.length} open {open.length === 1 ? "task" : "tasks"}</strong>
          {picks.length > 0 && <> and <strong className="text-white">{picks.filter((p) => p.match.percentage >= 40).length} strong matches</strong> waiting</>}.
        </p>
        <Link to="/opportunities" className="mt-5 inline-flex items-center gap-2 rounded-xl bg-[#f59e0b] px-5 py-3 text-xs font-extrabold text-[#3b1d06] hover:bg-[#fbbf24]">Find opportunities <ArrowRight size={15} /></Link>
      </section>

      {!profile.profile_complete && (
        <p className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Your profile is incomplete. Add your <strong>mobile number</strong>, city and skills to get better matches and be able to apply. <Link className="font-bold underline" to="/profile">Complete profile</Link>
        </p>
      )}
      {alerts.items.map((a) => (
        <div key={a.id} role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          <strong>{a.title}.</strong> {a.message} {a.link && <Link className="font-bold underline" to={a.link}>Open</Link>}
        </div>
      ))}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Volunteer hours" value={`${impact.total_hours} hrs`} />
        <Stat label="Events attended" value={impact.events_attended} />
        <Stat label="Tasks completed" value={impact.tasks_completed} hint={`of ${impact.tasks_total} assigned`} />
        <Stat label="People reached" value={impact.people_reached} hint={`${impact.ngos_supported} NGO${impact.ngos_supported === 1 ? "" : "s"} supported`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="surface-card p-5">
          <div className="flex items-center justify-between"><h2 className="flex items-center gap-2 font-display text-lg font-bold text-slate-900"><HeartHandshake size={18} />Recommended for you</h2><Link to="/opportunities" className="text-xs font-bold text-purple-700">See all</Link></div>
          {picks.length === 0 ? <p className="mt-3 text-sm text-slate-500">No open opportunities right now.</p> : (
            <ul className="mt-3 divide-y divide-slate-100">
              {picks.map((p) => (
                <li key={p.opportunity.id} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0"><p className="truncate text-sm font-bold text-slate-900">{p.opportunity.title}</p><p className="truncate text-xs text-slate-500">{p.opportunity.ngo_name} · {p.opportunity.location || "Flexible"}</p></div>
                  <span className="shrink-0 rounded-full bg-purple-50 px-2.5 py-1 text-xs font-extrabold text-purple-700">{p.match.percentage}%</span>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="surface-card p-5">
          <div className="flex items-center justify-between"><h2 className="flex items-center gap-2 font-display text-lg font-bold text-slate-900"><ListTodo size={18} />My open tasks</h2><Link to="/tasks" className="text-xs font-bold text-purple-700">All tasks</Link></div>
          {open.length === 0 ? <p className="mt-3 text-sm text-slate-500">No open tasks. Tasks appear once an NGO accepts you and assigns one.</p> : (
            <ul className="mt-3 divide-y divide-slate-100">
              {open.slice(0, 4).map((t) => (
                <li key={t.id} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0"><p className="truncate text-sm font-bold text-slate-900">{t.task_name}</p><p className="flex items-center gap-1 text-xs text-slate-500"><Clock size={12} />{t.deadline ? `due ${t.deadline}` : "no deadline"} · {t.campaign_title}</p></div>
                  <StatusPill status={t.status} />
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="surface-card p-5 lg:col-span-2">
          <div className="flex items-center justify-between"><h2 className="flex items-center gap-2 font-display text-lg font-bold text-slate-900"><CalendarDays size={18} />Upcoming events</h2><Link to="/events" className="text-xs font-bold text-purple-700">Browse events</Link></div>
          {events.items.length === 0 ? <p className="mt-3 text-sm text-slate-500">Nothing on your roster yet. <Link className="font-bold text-purple-700" to="/events">Join an event</Link>.</p> : (
            <ul className="mt-3 divide-y divide-slate-100">
              {events.items.map((e) => <li key={e.id} className="flex items-center gap-3 py-3 text-sm"><CheckCircle2 size={16} className="text-emerald-500" /><span className="font-bold text-slate-900">{e.event_name}</span><span className="text-xs text-slate-500">{e.event_date} · {e.campaign_title}</span></li>)}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

import { Bell } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useNotifications } from "../context/NotificationContext";

const ago = (iso) => {
  const mins = Math.max(0, Math.round((Date.now() - new Date(`${iso}Z`).getTime()) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  if (mins < 1440) return `${Math.round(mins / 60)}h ago`;
  return `${Math.round(mins / 1440)}d ago`;
};

export function PriorityDot({ priority }) {
  const color = priority === "HIGH" ? "bg-rose-500" : priority === "LOW" ? "bg-slate-300" : "bg-purple-400";
  return <span title={`${priority} priority`} className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${color}`} />;
}

export default function NotificationBell() {
  const { unread, highUnread, recent, live, read, readAll } = useNotifications();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return undefined;
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  async function openItem(n) {
    setOpen(false);
    if (n.status === "UNREAD") read(n.id);
    if (n.link) navigate(n.link);
  }

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((o) => !o)} aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`} aria-expanded={open}
        className="relative grid h-10 w-10 place-items-center rounded-xl text-slate-500 transition hover:bg-white hover:text-purple-700 hover:shadow-sm">
        <Bell size={19} />
        {unread > 0 && (
          <span className={`absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full px-1 text-[9px] font-bold text-white ${highUnread ? "animate-pulse bg-rose-500" : "bg-[#6b21a8]"}`}>
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 top-12 z-30 w-[min(92vw,22rem)] rounded-xl border border-slate-200 bg-white shadow-xl shadow-slate-900/10">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div>
              <p className="text-sm font-bold text-slate-900">Notifications</p>
              <p className="text-[10px] font-semibold text-slate-400">{live ? "● Live" : "○ Checking periodically"}</p>
            </div>
            {unread > 0 && <button onClick={readAll} className="text-xs font-bold text-purple-700 hover:text-purple-900">Mark all read</button>}
          </div>
          <ul className="max-h-80 overflow-y-auto">
            {recent.length === 0 && <li className="px-4 py-8 text-center text-sm text-slate-500">You're all caught up.</li>}
            {recent.map((n) => (
              <li key={n.id}>
                <button onClick={() => openItem(n)} className={`flex w-full gap-3 px-4 py-3 text-left transition hover:bg-slate-50 ${n.status === "UNREAD" ? "bg-purple-50/40" : ""}`}>
                  <PriorityDot priority={n.priority} />
                  <span className="min-w-0 flex-1">
                    <span className="flex justify-between gap-2"><span className={`truncate text-xs ${n.status === "UNREAD" ? "font-extrabold" : "font-semibold"} text-slate-900`}>{n.title}</span><span className="shrink-0 text-[10px] text-slate-400">{ago(n.created_at)}</span></span>
                    <span className="mt-0.5 block text-xs leading-5 text-slate-600">{n.message}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <Link to="/notifications" onClick={() => setOpen(false)} className="block border-t border-slate-100 px-4 py-3 text-center text-xs font-bold text-purple-700 hover:bg-slate-50">View all notifications</Link>
        </div>
      )}
    </div>
  );
}

export function NotificationToast() {
  const { toast, dismissToast } = useNotifications();
  const navigate = useNavigate();
  if (!toast) return null;
  const high = toast.priority === "HIGH";
  return (
    <div role={high ? "alert" : "status"} className={`fixed bottom-5 right-5 z-50 w-[min(92vw,22rem)] rounded-xl p-4 shadow-2xl ${high ? "bg-rose-600 text-white" : "bg-slate-900 text-white"}`}>
      <div className="flex items-start justify-between gap-3">
        <button className="text-left" onClick={() => { dismissToast(); if (toast.link) navigate(toast.link); }}>
          <p className="text-xs font-extrabold uppercase tracking-wider opacity-80">{high ? "Urgent" : "New notification"}</p>
          <p className="mt-1 text-sm font-bold">{toast.title}</p>
          <p className="mt-0.5 text-xs opacity-90">{toast.message}</p>
        </button>
        <button onClick={dismissToast} aria-label="Dismiss" className="text-lg leading-none opacity-70 hover:opacity-100">×</button>
      </div>
    </div>
  );
}

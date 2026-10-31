import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Bell,
  ChevronDown,
  HeartHandshake,
  Menu,
  MessageSquare,
  Search,
  Siren,
  X,
} from "lucide-react";

import api from "../api/client";
import { useAuth } from "../context/AuthContext";
import { adminNavigation, navigation } from "../data/dashboardData";

const ROLE_LABELS = {
  NGO_ADMIN: "NGO Admin",
  PLATFORM_ADMIN: "Platform Admin",
  VOLUNTEER: "Volunteer",
  DONOR: "Donor",
  BENEFICIARY: "Beneficiary",
};

const initials = (name) => name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("");

const pageTitles = {
  "/dashboard": "Dashboard Overview",
  "/admin": "NGO Overview",
  "/admin/campaigns": "Manage Campaigns",
  "/admin/events": "Manage Events",
  "/opportunities": "Volunteer Opportunities",
  "/campaigns": "Active Campaigns",
  "/tasks": "My Assigned Tasks",
  "/donations": "Donation & Resources",
  "/impact": "Impact & Analytics",
};

function SideNav({ onNavigate, mobile = false, items }) {
  return (
    <aside className={`${mobile ? "flex w-[286px]" : "hidden w-[274px] lg:flex"} shrink-0 flex-col bg-[#20152d] text-white`}>
      <div className="flex h-[82px] items-center justify-between border-b border-white/10 px-7">
        <NavLink to="/" onClick={onNavigate} className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-[#a855f7] to-[#6b21a8] shadow-lg shadow-purple-950/30">
            <HeartHandshake size={22} strokeWidth={2.4} />
          </span>
          <span className="font-display text-[20px] font-bold tracking-[-0.04em]">VolunteerSync</span>
        </NavLink>
        {mobile && (
          <button className="rounded-lg p-2 text-white/60 hover:bg-white/10 hover:text-white" onClick={onNavigate} aria-label="Close navigation">
            <X size={20} />
          </button>
        )}
      </div>

      <div className="flex flex-1 flex-col px-4 py-7">
        <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.2em] text-white/35">Workspace</p>
        <nav className="space-y-1">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/dashboard" || item.path === "/admin"}
                onClick={onNavigate}
                className={({ isActive }) => `group flex items-center justify-between rounded-xl px-3 py-3 text-[13px] font-semibold transition ${isActive ? "bg-white/12 text-white shadow-inner" : "text-white/55 hover:bg-white/7 hover:text-white"}`}
              >
                <span className="flex items-center gap-3">
                  <Icon size={18} strokeWidth={1.9} className="transition group-hover:text-[#d8b4fe]" />
                  {item.label}
                </span>
                {item.badge && <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] font-bold text-white/70">{item.badge}</span>}
              </NavLink>
            );
          })}
        </nav>

        <div className="mt-auto rounded-2xl border border-amber-200/10 bg-gradient-to-br from-[#42205b] to-[#2b183d] p-4 shadow-xl shadow-black/10">
          <div className="mb-3 flex items-center justify-between">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-[#f59e0b]/15 text-[#fbbf24]"><Siren size={18} /></span>
            <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-[#fbbf24]"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#f59e0b]" /> Live alert</span>
          </div>
          <h3 className="text-sm font-bold text-white">Sylhet Flood Relief</h3>
          <p className="mt-1.5 text-[11px] leading-5 text-white/50">The response team is active and needs more hands.</p>
          <button className="mt-4 flex w-full items-center justify-center rounded-lg bg-[#f59e0b] px-3 py-2.5 text-[11px] font-bold text-[#3b1d06] transition hover:bg-[#fbbf24]">
            Join response team
          </button>
        </div>
      </div>

      <div className="border-t border-white/10 px-7 py-5">
        <div className="flex items-center gap-2 text-[11px] text-white/40"><span className="h-2 w-2 rounded-full bg-emerald-400" /> Local preview mode</div>
      </div>
    </aside>
  );
}

function TopNav({ onMenu, profileOpen, onProfileToggle, apiStatus, user, onLogout }) {
  return (
    <header className="sticky top-0 z-20 flex h-[82px] items-center justify-between border-b border-slate-200/80 bg-[#fbfaff]/90 px-5 backdrop-blur-xl sm:px-8 lg:px-10">
      <div className="flex min-w-0 items-center gap-4">
        <button className="rounded-xl border border-slate-200 bg-white p-2.5 text-slate-600 shadow-sm hover:border-purple-200 hover:text-purple-700 lg:hidden" onClick={onMenu} aria-label="Open navigation">
          <Menu size={20} />
        </button>
        <div className="hidden min-w-0 sm:block">
          <p className="truncate text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">{ROLE_LABELS[user.role]} workspace</p>
          <p className="mt-0.5 text-sm font-bold text-slate-800">Welcome, {user.name.split(" ")[0]}</p>
        </div>
      </div>

      <div className="mx-4 hidden max-w-[380px] flex-1 md:block">
        <label className="relative block">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={17} />
          <input className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-4 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-purple-400 focus:ring-4 focus:ring-purple-100" placeholder="Search causes, tasks, NGOs..." />
        </label>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <div className="mr-1 hidden items-center gap-2 rounded-full bg-white px-3 py-2 text-[10px] font-bold text-slate-500 shadow-sm ring-1 ring-slate-200/70 xl:flex">
          <span className={`h-2 w-2 rounded-full ${apiStatus === "online" ? "bg-emerald-500" : apiStatus === "checking" ? "animate-pulse bg-amber-400" : "bg-slate-300"}`} />
          {apiStatus === "online" ? "API connected" : apiStatus === "checking" ? "Checking API" : "Preview mode"}
        </div>
        <button className="relative grid h-10 w-10 place-items-center rounded-xl text-slate-500 transition hover:bg-white hover:text-purple-700 hover:shadow-sm" aria-label="Emergency alerts">
          <Bell size={19} />
          <span className="absolute right-2 top-1.5 h-2 w-2 animate-pulse rounded-full bg-rose-500 ring-2 ring-[#fbfaff]" />
        </button>
        <button className="relative hidden h-10 w-10 place-items-center rounded-xl text-slate-500 transition hover:bg-white hover:text-purple-700 hover:shadow-sm sm:grid" aria-label="Messages">
          <MessageSquare size={18} />
          <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-[#6b21a8] px-1 text-[9px] font-bold text-white">3</span>
        </button>
        <div className="relative ml-1 border-l border-slate-200 pl-3 sm:pl-4">
          <button onClick={onProfileToggle} className="flex items-center gap-2 rounded-xl p-1 transition hover:bg-white" aria-expanded={profileOpen}>
            <span className="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-[#c084fc] to-[#6b21a8] text-xs font-extrabold text-white shadow-sm">{initials(user.name)}</span>
            <span className="hidden text-left sm:block"><span className="block text-xs font-bold text-slate-800">{user.name}</span><span className="block text-[10px] text-slate-400">{ROLE_LABELS[user.role]}</span></span>
            <ChevronDown size={15} className={`hidden text-slate-400 transition sm:block ${profileOpen ? "rotate-180" : ""}`} />
          </button>
          {profileOpen && <div className="absolute right-0 top-14 w-48 rounded-xl border border-slate-200 bg-white p-2 shadow-xl shadow-slate-900/10"><p className="px-3 py-2 text-[11px] font-semibold text-slate-400">Account menu</p><p className="truncate px-3 pb-2 text-xs font-semibold text-slate-600">{user.email}</p><button onClick={onLogout} className="w-full rounded-lg px-3 py-2 text-left text-xs font-semibold text-rose-600 hover:bg-rose-50">Log out</button></div>}
        </div>
      </div>
    </header>
  );
}

export default function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const items = user.role === "NGO_ADMIN" ? adminNavigation : navigation;
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [apiStatus, setApiStatus] = useState("checking");

  useEffect(() => {
    setMobileOpen(false);
    setProfileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    let active = true;
    api.get("/api/v1/health").then(() => active && setApiStatus("online")).catch(() => active && setApiStatus("offline"));
    return () => { active = false; };
  }, []);

  const pageTitle = useMemo(() => pageTitles[location.pathname] || "Volunteer workspace", [location.pathname]);

  return (
    <div className="flex min-h-screen bg-[#fbfaff] text-slate-900">
      <SideNav items={items} />
      {mobileOpen && <div className="fixed inset-0 z-40 flex lg:hidden"><button className="flex-1 cursor-default bg-slate-950/45" onClick={() => setMobileOpen(false)} aria-label="Close navigation overlay" /><SideNav mobile items={items} onNavigate={() => setMobileOpen(false)} /></div>}
      <div className="min-w-0 flex-1">
        <TopNav onMenu={() => setMobileOpen(true)} profileOpen={profileOpen} onProfileToggle={() => setProfileOpen((value) => !value)} apiStatus={apiStatus} user={user} onLogout={async () => { await logout(); navigate("/login", { replace: true }); }} />
        <main className="mx-auto w-full max-w-[1600px] p-5 sm:p-8 lg:px-10 lg:py-9">
          <div className="mb-7 flex items-end justify-between gap-4"><div><p className="mb-1 text-[11px] font-bold uppercase tracking-[0.2em] text-purple-600">{pageTitle}</p><div className="h-px w-9 bg-[#f59e0b]" /></div><p className="hidden text-xs font-medium text-slate-400 sm:block">Tuesday, October 01, 2024</p></div>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

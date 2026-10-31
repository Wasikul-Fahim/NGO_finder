import { useState } from "react";

import { myTasks, setTaskStatus } from "../api/opportunities";
import { parseError } from "../api/client";
import { EmptyState, ErrorState, Loading } from "../components/AsyncState";
import { StatusPill } from "../components/Chips";
import { primaryButton, secondaryButton } from "../components/FormField";
import useAsync from "../hooks/useAsync";

// Mirrors the server state machine; the server is the authority (409 otherwise).
const ACTIONS = {
  PENDING: [["ACCEPTED", "Accept", true], ["DECLINED", "Decline", false]],
  ACCEPTED: [["IN_PROGRESS", "Start", true]],
  IN_PROGRESS: [["COMPLETED", "Mark complete", true]],
  COMPLETED: [],
  DECLINED: [],
};

export default function Tasks() {
  const { data, loading, error, reload } = useAsync(() => myTasks({ page_size: 100 }));
  const [busy, setBusy] = useState(null);
  const [actionError, setActionError] = useState("");
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  async function move(task, status) {
    setBusy(task.id);
    setActionError("");
    try { await setTaskStatus(task.id, status); reload(); }
    catch (err) { setActionError(parseError(err).message); }
    finally { setBusy(null); }
  }

  return (
    <div className="space-y-5">
      <h1 className="font-display text-2xl font-bold text-slate-900">My tasks</h1>
      {actionError && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2.5 text-sm font-semibold text-rose-700">{actionError}</p>}
      {data.items.length === 0 ? (
        <EmptyState title="No tasks assigned" hint="Once an NGO accepts your application, tasks they assign appear here." />
      ) : (
        <ul className="space-y-3">
          {data.items.map((t) => (
            <li key={t.id} className="surface-card flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-display text-base font-bold text-slate-900">{t.task_name}</h3>
                  <StatusPill status={t.status} />
                </div>
                <p className="mt-1 text-xs text-slate-500">{t.campaign_title}{t.deadline ? ` · due ${t.deadline}` : ""}</p>
                {t.description && <p className="mt-1 text-sm text-slate-600">{t.description}</p>}
              </div>
              <div className="flex gap-2">
                {ACTIONS[t.status].map(([status, label, primary]) => (
                  <button key={status} className={primary ? primaryButton : secondaryButton} disabled={busy === t.id} onClick={() => move(t, status)}>{label}</button>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";

import { parseError } from "../api/client";
import { getNotificationSettings, saveNotificationSettings } from "../api/notifications";
import { ErrorState, Loading } from "../components/AsyncState";
import { primaryButton } from "../components/FormField";
import { ErrorNotice, SuccessNotice } from "../components/Notice";
import useAsync from "../hooks/useAsync";

const TYPES = [
  ["APPLICATION_UPDATE", "Application updates"], ["TASK_ASSIGNED", "Task assignments"], ["TASK_UPDATE", "Task status changes"],
  ["EVENT_REMINDER", "Event reminders"], ["ATTENDANCE", "Attendance recorded"], ["CAMPAIGN_UPDATE", "Campaign updates"],
  ["DONATION_UPDATE", "Donation updates"], ["ANNOUNCEMENT", "NGO announcements"], ["DIRECT_MESSAGE", "Direct messages"],
];

export default function NotificationSettings() {
  const { data, loading, error, reload } = useAsync(getNotificationSettings);
  const [muted, setMuted] = useState([]);
  const [state, setState] = useState({ ok: "", error: "", busy: false });
  useEffect(() => { if (data) setMuted(data.muted_types); }, [data]);
  if (loading) return <Loading rows={2} />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const toggle = (type) => setMuted((m) => (m.includes(type) ? m.filter((t) => t !== type) : [...m, type]));
  async function save() {
    setState({ ok: "", error: "", busy: true });
    try { await saveNotificationSettings(muted); setState({ ok: "Preferences saved.", error: "", busy: false }); }
    catch (err) { setState({ ok: "", error: parseError(err).message, busy: false }); }
  }
  return (
    <div className="surface-card mx-auto max-w-xl space-y-4 p-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-slate-900">Notification settings</h1>
        <p className="mt-1 text-sm text-slate-500">Switch off the kinds of notifications you don't want. Urgent alerts and emergency announcements always reach you.</p>
      </div>
      <SuccessNotice>{state.ok}</SuccessNotice><ErrorNotice>{state.error}</ErrorNotice>
      <ul className="divide-y divide-slate-100">
        {TYPES.map(([type, label]) => (
          <li key={type}>
            <label className="flex cursor-pointer items-center justify-between py-3 text-sm font-semibold text-slate-800">
              {label}
              <input type="checkbox" className="h-4 w-4" checked={!muted.includes(type)} onChange={() => toggle(type)} aria-label={`Receive ${label}`} />
            </label>
          </li>
        ))}
      </ul>
      <button className={primaryButton} disabled={state.busy} onClick={save}>{state.busy ? "Saving…" : "Save preferences"}</button>
    </div>
  );
}

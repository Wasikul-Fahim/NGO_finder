import { Printer } from "lucide-react";
import { Link } from "react-router-dom";

import { myContributions } from "../api/impact";
import { ErrorState, Loading } from "../components/AsyncState";
import { primaryButton } from "../components/FormField";
import { useAuth } from "../context/AuthContext";
import useAsync from "../hooks/useAsync";

/** A printable volunteer certificate based on recorded attendance. Use the browser's print / save-as-PDF. */
export default function Certificate() {
  const { user } = useAuth();
  const { data, loading, error, reload } = useAsync(myContributions);
  if (loading) return <Loading rows={1} />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  if (data.total_hours <= 0) {
    return (
      <div className="surface-card mx-auto max-w-xl p-8 text-center">
        <h1 className="font-display text-xl font-bold text-slate-900">No certificate yet</h1>
        <p className="mt-2 text-sm text-slate-500">Certificates are based on volunteer hours that an NGO has recorded. Attend an event and ask the NGO to record your attendance.</p>
        <Link to="/events" className="mt-4 inline-block text-sm font-bold text-purple-700">Find an event</Link>
      </div>
    );
  }
  const issued = new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
  return (
    <div className="space-y-4">
      <style>{"@media print { body * { visibility: hidden; } #certificate, #certificate * { visibility: visible; } #certificate { position: absolute; inset: 0; margin: 0; box-shadow: none; } .no-print { display: none !important; } }"}</style>
      <div className="no-print flex justify-end"><button className={primaryButton} onClick={() => window.print()}><Printer size={16} className="mr-2" />Print / save as PDF</button></div>
      <div id="certificate" className="mx-auto max-w-3xl rounded-2xl border-[6px] border-double border-purple-300 bg-white p-10 text-center shadow-sm sm:p-14">
        <p className="text-xs font-bold uppercase tracking-[0.3em] text-purple-600">VolunteerSync</p>
        <h1 className="mt-4 font-display text-3xl font-bold text-slate-900 sm:text-4xl">Certificate of Volunteer Service</h1>
        <p className="mt-8 text-sm text-slate-500">This certifies that</p>
        <p className="mt-2 font-display text-3xl font-bold text-purple-800">{user.name}</p>
        <p className="mx-auto mt-6 max-w-lg text-sm leading-7 text-slate-600">
          volunteered <strong>{data.total_hours} hours</strong> across <strong>{data.events_attended} event{data.events_attended === 1 ? "" : "s"}</strong>
          {data.ngos_supported > 0 && <>, supporting <strong>{data.ngos_supported} organisation{data.ngos_supported === 1 ? "" : "s"}</strong></>}
          {data.tasks_completed > 0 && <>, and completed <strong>{data.tasks_completed} task{data.tasks_completed === 1 ? "" : "s"}</strong></>}.
        </p>
        <p className="mt-10 text-xs text-slate-400">Issued {issued} · based on attendance recorded by the participating NGOs</p>
      </div>
    </div>
  );
}

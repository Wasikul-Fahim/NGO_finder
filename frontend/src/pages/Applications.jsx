import { useState } from "react";

import { myApplications } from "../api/opportunities";
import { EmptyState, ErrorState, Loading } from "../components/AsyncState";
import { StatusPill } from "../components/Chips";
import { secondaryButton } from "../components/FormField";
import useAsync from "../hooks/useAsync";

export default function Applications() {
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(() => myApplications({ page, page_size: 10 }), [page]);
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <div className="space-y-5">
      <h1 className="font-display text-2xl font-bold text-slate-900">My applications</h1>
      {data.items.length === 0 ? (
        <EmptyState title="You haven't applied yet" hint="Find an opportunity that fits you and hit Apply." />
      ) : (
        <ul className="space-y-3">
          {data.items.map((a) => (
            <li key={a.id} className="surface-card flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="font-display text-base font-bold text-slate-900">{a.opportunity_title}</h3>
                <p className="text-xs text-slate-500">{a.ngo_name} · applied {new Date(a.application_date + "Z").toLocaleDateString()}</p>
                {a.review_note && <p className="mt-1 text-xs text-slate-600">Note from NGO: {a.review_note}</p>}
              </div>
              <StatusPill status={a.status} />
            </li>
          ))}
        </ul>
      )}
      {data.pages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button className={secondaryButton} disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
          <span className="text-xs font-bold text-slate-500">Page {data.page} of {data.pages}</span>
          <button className={secondaryButton} disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      )}
    </div>
  );
}

import { useState } from "react";

import { parseError } from "../../api/client";
import { ngoDonations, setDonationStatus } from "../../api/impact";
import { EmptyState, ErrorState, Loading } from "../../components/AsyncState";
import { StatusPill } from "../../components/Chips";
import { inputClass, primaryButton, secondaryButton } from "../../components/FormField";
import { ErrorNotice, money } from "../../components/Notice";
import Pager from "../../components/Pager";
import useAsync from "../../hooks/useAsync";

export default function IncomingDonations() {
  const [status, setStatus] = useState("PENDING");
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(
    () => ngoDonations({ page, page_size: 10, ...(status ? { status } : {}) }), [status, page]);
  const [actionError, setActionError] = useState("");

  async function act(d, next) {
    setActionError("");
    try { await setDonationStatus(d.id, next); reload(); } catch (err) { setActionError(parseError(err).message); }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-bold text-slate-900">Donations</h1>
        <select className={`${inputClass} !w-auto`} aria-label="Filter by status" value={status} onChange={(e) => { setPage(1); setStatus(e.target.value); }}>
          <option value="">All statuses</option><option>PENDING</option><option>RECEIVED</option><option>REJECTED</option>
        </select>
      </div>
      <p className="text-sm text-slate-500">Confirm a donation once you have actually received it. Nothing is paid through this site.</p>
      <ErrorNotice>{actionError}</ErrorNotice>
      {loading ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data.items.length === 0 ? (
        <EmptyState title="No donations here" />
      ) : (
        <ul className="space-y-3">
          {data.items.map((d) => (
            <li key={d.id} className="surface-card flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-bold text-slate-900">{d.donor_name}</p><StatusPill status={d.status} />
                </div>
                <p className="mt-1 text-xs text-slate-500">{d.campaign_title} · {d.donation_date} · {d.donation_type}{d.donation_type === "MONEY" ? ` · ${money(d.amount)}` : ""}{d.note ? ` · ${d.note}` : ""}</p>
              </div>
              {d.status === "PENDING" && (
                <div className="flex gap-2">
                  <button className={primaryButton} onClick={() => act(d, "RECEIVED")}>Mark received</button>
                  <button className={secondaryButton} onClick={() => act(d, "REJECTED")}>Reject</button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      <Pager data={data} page={page} onPage={setPage} />
    </div>
  );
}

import { secondaryButton } from "./FormField";

export default function Pager({ data, page, onPage }) {
  if (!data || data.pages <= 1) return null;
  return (
    <div className="flex items-center justify-center gap-3">
      <button className={secondaryButton} disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button>
      <span className="text-xs font-bold text-slate-500">Page {data.page} of {data.pages}</span>
      <button className={secondaryButton} disabled={page >= data.pages} onClick={() => onPage(page + 1)}>Next</button>
    </div>
  );
}

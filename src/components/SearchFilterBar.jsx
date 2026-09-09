import { STATUS, STATUS_LABELS, PRIORITY, PRIORITY_LABELS } from '../constants';

// NOTE: filter params (`search`, `status`, `priority`) are an ASSUMPTION —
// see docs/INTEGRATION_CHECKLIST.md for what must be confirmed with the backend.

export default function SearchFilterBar({ filters, onChange, showStatusFilter = true }) {
  const update = (patch) => onChange({ ...filters, ...patch });

  return (
    <div className="panel flex flex-col gap-3 p-3 sm:flex-row sm:items-center">
      <input
        type="search"
        className="field-input sm:max-w-xs"
        placeholder="Search by title or description"
        value={filters.search || ''}
        onChange={(e) => update({ search: e.target.value })}
        aria-label="Search complaints"
      />
      {showStatusFilter && (
        <select
          className="field-input sm:max-w-[10rem]"
          value={filters.status || ''}
          onChange={(e) => update({ status: e.target.value })}
          aria-label="Filter by status"
        >
          <option value="">All statuses</option>
          {Object.values(STATUS).map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
      )}
      <select
        className="field-input sm:max-w-[10rem]"
        value={filters.priority || ''}
        onChange={(e) => update({ priority: e.target.value })}
        aria-label="Filter by priority"
      >
        <option value="">All priorities</option>
        {Object.values(PRIORITY).map((p) => (
          <option key={p} value={p}>
            {PRIORITY_LABELS[p]}
          </option>
        ))}
      </select>
    </div>
  );
}

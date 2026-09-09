import StatusBadge from './StatusBadge';

function formatDateTime(isoString) {
  if (!isoString) return '—';
  return new Date(isoString).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function HistoryTimeline({ entries }) {
  if (!entries || entries.length === 0) {
    return <div className="panel p-4 text-sm text-ink-500">No history recorded yet.</div>;
  }

  return (
    <div className="panel p-4">
      <h3 className="text-sm font-semibold text-ink-900">History</h3>
      <ol className="mt-3 space-y-4 border-l border-ink-200 pl-4">
        {entries.map((entry) => (
          <li key={entry.history_id} className="relative">
            <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-campus-500" />
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={entry.new_status} />
              <span className="text-xs text-ink-400">{formatDateTime(entry.changed_at)}</span>
            </div>
            {entry.note && <p className="mt-1 text-sm text-ink-700">{entry.note}</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}

import { Link } from 'react-router-dom';
import StatusBadge from './StatusBadge';
import PriorityBadge from './PriorityBadge';
import { ROUTES } from '../constants';

function formatDate(isoString) {
  if (!isoString) return '—';
  return new Date(isoString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export default function ComplaintCard({ complaint }) {
  return (
    <Link
      to={ROUTES.COMPLAINT_DETAILS(complaint.complaint_id)}
      className="panel flex flex-col gap-3 p-4 transition-shadow hover:shadow-md sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-ink-900">{complaint.title}</p>
        <p className="mt-1 text-xs text-ink-500">
          {complaint.department || 'Unrouted'} · Submitted {formatDate(complaint.created_at)}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <PriorityBadge priority={complaint.priority} />
        <StatusBadge status={complaint.status} />
      </div>
    </Link>
  );
}

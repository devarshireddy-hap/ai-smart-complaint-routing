import { STATUS, STATUS_LABELS } from '../constants';

const STYLES = {
  [STATUS.SUBMITTED]: 'bg-ink-100 text-ink-700',
  [STATUS.AI_ANALYZED]: 'bg-purple-100 text-purple-800',
  [STATUS.ASSIGNED]: 'bg-sky-100 text-sky-800',
  [STATUS.IN_PROGRESS]: 'bg-amber-100 text-amber-800',
  [STATUS.RESOLVED]: 'bg-emerald-100 text-emerald-800',
  [STATUS.CLOSED]: 'bg-ink-200 text-ink-700',
  [STATUS.REJECTED]: 'bg-red-100 text-red-800',
};

export default function StatusBadge({ status }) {
  const style = STYLES[status] || 'bg-ink-100 text-ink-700';
  const label = STATUS_LABELS[status] || status;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}>
      {label}
    </span>
  );
}

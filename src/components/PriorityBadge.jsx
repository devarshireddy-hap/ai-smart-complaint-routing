import { PRIORITY, PRIORITY_LABELS } from '../constants';

const STYLES = {
  [PRIORITY.LOW]: 'bg-ink-100 text-ink-600',
  [PRIORITY.MEDIUM]: 'bg-sky-100 text-sky-800',
  [PRIORITY.HIGH]: 'bg-amber-100 text-amber-900',
  [PRIORITY.CRITICAL]: 'bg-red-100 text-red-800',
};

export default function PriorityBadge({ priority }) {
  const style = STYLES[priority] || 'bg-ink-100 text-ink-600';
  const label = PRIORITY_LABELS[priority] || priority || 'Unset';
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}>
      {label}
    </span>
  );
}

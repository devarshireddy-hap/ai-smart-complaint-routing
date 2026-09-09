export default function EmptyState({ title, description, action }) {
  return (
    <div className="panel flex flex-col items-center gap-2 p-10 text-center">
      <p className="text-sm font-semibold text-ink-800">{title}</p>
      {description && <p className="max-w-sm text-sm text-ink-500">{description}</p>}
      {action}
    </div>
  );
}

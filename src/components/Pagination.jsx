// NOTE: pagination query params/response shape are an ASSUMPTION — the
// locked API contract does not define them. See docs/INTEGRATION_CHECKLIST.md.

export default function Pagination({ page, pageSize, total, onPageChange }) {
  const totalPages = Math.max(1, Math.ceil((total || 0) / pageSize));
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between border-t border-ink-100 pt-3">
      <p className="text-xs text-ink-500">
        Page {page} of {totalPages} · {total} total
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          className="btn-secondary px-3 py-1 text-xs"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          Previous
        </button>
        <button
          type="button"
          className="btn-secondary px-3 py-1 text-xs"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
        >
          Next
        </button>
      </div>
    </div>
  );
}

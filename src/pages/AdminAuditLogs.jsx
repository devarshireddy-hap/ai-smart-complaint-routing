import { useCallback, useEffect, useState } from 'react';
import { adminApi, ApiError } from '../services/api';
import { DEFAULT_PAGE_SIZE } from '../constants';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';
import ErrorBanner from '../components/ErrorBanner';
import Pagination from '../components/Pagination';

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

export default function AdminAuditLogs() {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [entityType, setEntityType] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminApi.listAuditLogs({
        page,
        page_size: DEFAULT_PAGE_SIZE,
        entity_type: entityType || undefined,
      });
      setLogs(result?.items ?? []);
      setTotal(result?.total ?? (result?.items?.length ?? 0));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load audit logs.');
    } finally {
      setLoading(false);
    }
  }, [page, entityType]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-ink-900">Audit logs</h1>
        <p className="text-sm text-ink-500">
          Read-only record of authentication, role changes, assignments, status changes, resolutions, and
          administrative actions.
        </p>
      </div>

      <input
        type="text"
        className="field-input max-w-xs"
        placeholder="Filter by entity type (e.g. complaint, user)"
        value={entityType}
        onChange={(e) => {
          setPage(1);
          setEntityType(e.target.value);
        }}
      />

      {error && <ErrorBanner message={error} onRetry={load} />}

      {loading ? (
        <LoadingState label="Loading audit logs…" />
      ) : logs.length === 0 ? (
        <EmptyState title="No audit entries match this filter" />
      ) : (
        <div className="panel overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink-100 text-xs uppercase tracking-wide text-ink-400">
              <tr>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Actor</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Entity</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.audit_id} className="border-b border-ink-50 last:border-0 align-top">
                  <td className="whitespace-nowrap px-4 py-3 text-ink-500">{formatDateTime(log.created_at)}</td>
                  <td className="px-4 py-3 text-ink-700">{log.actor_user_id || 'System'}</td>
                  <td className="px-4 py-3 font-mono text-xs text-ink-700">{log.action}</td>
                  <td className="px-4 py-3 text-ink-500">
                    {log.entity_type}
                    {log.entity_id ? ` · ${log.entity_id}` : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 pb-3">
            <Pagination page={page} pageSize={DEFAULT_PAGE_SIZE} total={total} onPageChange={setPage} />
          </div>
        </div>
      )}
    </div>
  );
}

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { complaintsApi, ApiError } from '../services/api';
import { STATUS, STATUS_LABELS, ROUTES } from '../constants';
import LoadingState from '../components/LoadingState';
import ErrorBanner from '../components/ErrorBanner';

// NOTE: there is no dedicated analytics/summary endpoint in the locked API
// contract. This page derives counts client-side from a full complaint
// listing, which does not scale — see INTEGRATION_CHECKLIST.md for the
// aggregate endpoint this should be replaced with (e.g. GET /admin/analytics).
export default function AdminDashboard() {
  const [counts, setCounts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await complaintsApi.list({ page: 1, page_size: 200 });
      const items = result?.items ?? [];
      const tally = Object.fromEntries(Object.values(STATUS).map((s) => [s, 0]));
      items.forEach((c) => {
        if (tally[c.status] !== undefined) tally[c.status] += 1;
      });
      setCounts({ total: result?.total ?? items.length, byStatus: tally });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load analytics.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-ink-900">Admin overview</h1>
        <p className="text-sm text-ink-500">System-wide complaint analytics and management shortcuts.</p>
      </div>

      {error && <ErrorBanner message={error} onRetry={load} />}
      {loading ? (
        <LoadingState label="Loading analytics…" />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          <div className="panel p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-400">Total complaints</p>
            <p className="mt-1 text-2xl font-semibold text-ink-900">{counts?.total ?? 0}</p>
          </div>
          {Object.values(STATUS).map((s) => (
            <div key={s} className="panel p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-ink-400">{STATUS_LABELS[s]}</p>
              <p className="mt-1 text-2xl font-semibold text-ink-900">{counts?.byStatus?.[s] ?? 0}</p>
            </div>
          ))}
        </div>
      )}

      <div className="panel p-5">
        <h2 className="text-sm font-semibold text-ink-900">Manage</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link to={ROUTES.ADMIN_USERS} className="btn-secondary">
            Users
          </Link>
          <Link to={ROUTES.ADMIN_DEPARTMENTS} className="btn-secondary">
            Departments
          </Link>
          <Link to={ROUTES.ADMIN_AUDIT_LOGS} className="btn-secondary">
            Audit logs
          </Link>
          <Link to={ROUTES.ADMIN_BACKUP_RESTORE} className="btn-secondary">
            Backup & restore
          </Link>
        </div>
      </div>
    </div>
  );
}

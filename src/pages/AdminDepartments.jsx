import { useCallback, useEffect, useState } from 'react';
import { adminApi, ApiError } from '../services/api';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';
import ErrorBanner from '../components/ErrorBanner';

// Departments are a frozen/immutable seeded set (Final PSD Section 8;
// database_design.md "Department Immutability"). The frontend never offers
// create/delete controls — only the active/inactive state the backend
// exposes, since that is the only department mutation the design allows.
export default function AdminDepartments() {
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminApi.listDepartments();
      setDepartments(result?.items ?? result ?? []);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load departments.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-ink-900">Departments</h1>
        <p className="text-sm text-ink-500">
          Departments are a fixed set defined at the database level. They cannot be created or removed here —
          only activated or deactivated by the backend's controlled data-configuration process.
        </p>
      </div>

      {error && <ErrorBanner message={error} onRetry={load} />}

      {loading ? (
        <LoadingState label="Loading departments…" />
      ) : departments.length === 0 ? (
        <EmptyState title="No departments returned by the backend" />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {departments.map((d) => (
            <div key={d.department_id} className="panel flex items-center justify-between p-4">
              <div>
                <p className="text-sm font-semibold text-ink-900">{d.department_name}</p>
                {d.description && <p className="text-xs text-ink-500">{d.description}</p>}
              </div>
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  d.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-ink-100 text-ink-500'
                }`}
              >
                {d.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

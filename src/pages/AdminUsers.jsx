import { useCallback, useEffect, useState } from 'react';
import { adminApi, ApiError } from '../services/api';
import { ROLES, DEFAULT_PAGE_SIZE } from '../constants';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';
import ErrorBanner from '../components/ErrorBanner';
import Pagination from '../components/Pagination';
import ConfirmDialog from '../components/ConfirmDialog';

const ROLE_LABELS = {
  [ROLES.STUDENT]: 'Student',
  [ROLES.MANAGEMENT_OFFICER]: 'Management officer',
  [ROLES.ADMIN]: 'Admin',
};

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pendingChange, setPendingChange] = useState(null); // { userId, roleName, name }
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminApi.listUsers({ page, page_size: DEFAULT_PAGE_SIZE, search });
      setUsers(result?.items ?? []);
      setTotal(result?.total ?? (result?.items?.length ?? 0));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load users.');
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    load();
  }, [load]);

  const confirmRoleChange = async () => {
    if (!pendingChange) return;
    setBusy(true);
    try {
      await adminApi.updateUserRole(pendingChange.userId, pendingChange.roleName);
      setPendingChange(null);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not update this user\u2019s role.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-ink-900">Users</h1>
        <p className="text-sm text-ink-500">
          All users, regardless of role, live in a single account list. Role changes apply the principle of
          least privilege — grant only what's needed.
        </p>
      </div>

      <input
        type="search"
        className="field-input max-w-sm"
        placeholder="Search by name or email"
        value={search}
        onChange={(e) => {
          setPage(1);
          setSearch(e.target.value);
        }}
      />

      {error && <ErrorBanner message={error} onRetry={load} />}

      {loading ? (
        <LoadingState label="Loading users…" />
      ) : users.length === 0 ? (
        <EmptyState title="No users found" />
      ) : (
        <div className="panel overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink-100 text-xs uppercase tracking-wide text-ink-400">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Active</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.user_id} className="border-b border-ink-50 last:border-0">
                  <td className="px-4 py-3 text-ink-800">{u.full_name}</td>
                  <td className="px-4 py-3 text-ink-500">{u.email}</td>
                  <td className="px-4 py-3">
                    <select
                      className="field-input py-1 text-xs"
                      value={u.role_name}
                      onChange={(e) =>
                        setPendingChange({ userId: u.user_id, roleName: e.target.value, name: u.full_name })
                      }
                    >
                      {Object.values(ROLES).map((r) => (
                        <option key={r} value={r}>
                          {ROLE_LABELS[r]}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3 text-ink-500">{u.is_active ? 'Yes' : 'No'}</td>
                  <td className="px-4 py-3" />
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 pb-3">
            <Pagination page={page} pageSize={DEFAULT_PAGE_SIZE} total={total} onPageChange={setPage} />
          </div>
        </div>
      )}

      <ConfirmDialog
        open={Boolean(pendingChange)}
        title="Change this user's role?"
        description={
          pendingChange
            ? `${pendingChange.name} will become ${ROLE_LABELS[pendingChange.roleName]}. This changes what they can access immediately.`
            : ''
        }
        confirmLabel="Change role"
        busy={busy}
        onCancel={() => setPendingChange(null)}
        onConfirm={confirmRoleChange}
      />
    </div>
  );
}

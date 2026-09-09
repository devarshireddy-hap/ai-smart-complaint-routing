import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { complaintsApi, ApiError } from '../services/api';
import { getSelectedDepartmentPortal, clearSelectedDepartmentPortal } from '../auth/officerPortal';
import { DEFAULT_PAGE_SIZE, ROUTES } from '../constants';
import ComplaintCard from '../components/ComplaintCard';
import SearchFilterBar from '../components/SearchFilterBar';
import Pagination from '../components/Pagination';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';
import ErrorBanner from '../components/ErrorBanner';

export default function OfficerDashboard() {
  const navigate = useNavigate();
  const portal = getSelectedDepartmentPortal();

  const [complaints, setComplaints] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ search: '', status: '', priority: '' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // The backend already scopes this list to complaints assigned to the
      // current officer (Final PSD Section 4). `department_id` here is an
      // additional client-side filter on top of that -- a display/scoping
      // convenience for the chosen portal, not a substitute for backend
      // authorization. It is a no-op until the backend department lookup
      // (see departmentsApi.list) returns real IDs -- see
      // INTEGRATION_CHECKLIST.md.
      const result = await complaintsApi.list({
        page,
        page_size: DEFAULT_PAGE_SIZE,
        department_id: portal?.department_id || undefined,
        ...filters,
      });
      setComplaints(result?.items ?? []);
      setTotal(result?.total ?? (result?.items?.length ?? 0));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load assigned complaints.');
    } finally {
      setLoading(false);
    }
  }, [page, filters, portal?.department_id]);

  useEffect(() => {
    load();
  }, [load]);

  const handleFilterChange = (next) => {
    setPage(1);
    setFilters(next);
  };

  const switchPortal = () => {
    clearSelectedDepartmentPortal();
    navigate(ROUTES.OFFICER_SELECT_DEPARTMENT);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-ink-900">
            {portal?.department_name ? `${portal.department_name} Department Portal` : 'Assigned complaints'}
          </h1>
          <p className="text-sm text-ink-500">
            Complaints authorized to you, with AI routing context and similar historical cases.
          </p>
        </div>
        <button type="button" className="btn-secondary" onClick={switchPortal}>
          Switch department portal
        </button>
      </div>

      <SearchFilterBar filters={filters} onChange={handleFilterChange} />

      {error && <ErrorBanner message={error} onRetry={load} />}

      {loading ? (
        <LoadingState label="Loading assigned complaints…" />
      ) : complaints.length === 0 ? (
        <EmptyState
          title="Nothing assigned to you right now"
          description="New assignments from an administrator will appear here."
        />
      ) : (
        <div className="space-y-3">
          {complaints.map((complaint) => (
            <ComplaintCard key={complaint.complaint_id} complaint={complaint} />
          ))}
          <Pagination page={page} pageSize={DEFAULT_PAGE_SIZE} total={total} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}

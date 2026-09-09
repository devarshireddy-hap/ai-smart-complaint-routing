import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { complaintsApi, ApiError } from '../services/api';
import { DEFAULT_PAGE_SIZE, ROUTES } from '../constants';
import ComplaintCard from '../components/ComplaintCard';
import SearchFilterBar from '../components/SearchFilterBar';
import Pagination from '../components/Pagination';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';
import ErrorBanner from '../components/ErrorBanner';

export default function StudentDashboard() {
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
      const result = await complaintsApi.list({
        page,
        page_size: DEFAULT_PAGE_SIZE,
        ...filters,
      });
      setComplaints(result?.items ?? []);
      setTotal(result?.total ?? (result?.items?.length ?? 0));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load your complaints.');
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => {
    load();
  }, [load]);

  const handleFilterChange = (next) => {
    setPage(1);
    setFilters(next);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-ink-900">My complaints</h1>
          <p className="text-sm text-ink-500">Track the complaints you've submitted and their AI-assisted routing.</p>
        </div>
        <Link to={ROUTES.CREATE_COMPLAINT()} className="btn-primary">
          New complaint
        </Link>
      </div>

      <SearchFilterBar filters={filters} onChange={handleFilterChange} />

      {error && <ErrorBanner message={error} onRetry={load} />}

      {loading ? (
        <LoadingState label="Loading your complaints…" />
      ) : complaints.length === 0 ? (
        <EmptyState
          title="No complaints yet"
          description="When you submit a complaint, it will show up here along with its status and AI routing details."
          action={
            <Link to={ROUTES.CREATE_COMPLAINT()} className="btn-primary">
              Submit your first complaint
            </Link>
          }
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

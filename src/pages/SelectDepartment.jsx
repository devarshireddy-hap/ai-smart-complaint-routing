import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { departmentsApi, ApiError } from '../services/api';
import { setSelectedDepartmentPortal } from '../auth/officerPortal';
import { BASELINE_DEPARTMENT_DESCRIPTIONS, ROUTES } from '../constants';
import LoadingState from '../components/LoadingState';
import ErrorBanner from '../components/ErrorBanner';

// Shown once per browser session before a MANAGEMENT_OFFICER reaches their
// dashboard. This is a frontend scoping/display convenience, NOT a security
// boundary — see src/auth/officerPortal.js and INTEGRATION_CHECKLIST.md.
export default function SelectDepartment() {
  const navigate = useNavigate();
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await departmentsApi.list();
        if (mounted) setDepartments(result);
      } catch (err) {
        if (mounted) setError(err instanceof ApiError ? err.message : 'Could not load departments.');
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const choose = (department) => {
    setSelectedDepartmentPortal(department);
    navigate(ROUTES.OFFICER_DASHBOARD, { replace: true });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-50 px-4 py-10">
      <div className="w-full max-w-2xl">
        <div className="mb-6 text-center">
          <h1 className="text-lg font-semibold text-ink-900">Choose your department portal</h1>
          <p className="mt-1 text-sm text-ink-500">
            Select the department you're signing in for. You can switch portals at any time from the navigation
            bar. This only affects what's shown first — you'll still only see complaints actually assigned to
            you, regardless of which portal you pick.
          </p>
        </div>

        {error && <ErrorBanner message={error} />}

        {loading ? (
          <LoadingState label="Loading departments…" />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {departments.map((dept) => (
              <button
                key={dept.department_name}
                type="button"
                onClick={() => choose(dept)}
                className="panel flex flex-col items-start gap-1 p-5 text-left transition-shadow hover:shadow-md focus-visible:ring-2 focus-visible:ring-campus-500"
              >
                <span className="text-sm font-semibold text-ink-900">{dept.department_name}</span>
                <span className="text-xs text-ink-500">
                  {dept.description || BASELINE_DEPARTMENT_DESCRIPTIONS[dept.department_name] || ''}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

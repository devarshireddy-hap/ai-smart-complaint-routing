import { Link } from 'react-router-dom';
import { ROUTES } from '../constants';

export default function Forbidden() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-ink-50 px-4 text-center">
      <p className="text-4xl font-semibold text-ink-300">403</p>
      <h1 className="text-lg font-semibold text-ink-900">You don't have access to this page</h1>
      <p className="max-w-sm text-sm text-ink-500">
        Your role doesn't permit this action. If you believe this is a mistake, contact an administrator.
      </p>
      <Link to={ROUTES.LOGIN} className="btn-secondary">
        Back to sign in
      </Link>
    </div>
  );
}

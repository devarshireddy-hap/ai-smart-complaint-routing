import { Link } from 'react-router-dom';
import { ROUTES } from '../constants';

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-ink-50 px-4 text-center">
      <p className="text-4xl font-semibold text-ink-300">404</p>
      <h1 className="text-lg font-semibold text-ink-900">Page not found</h1>
      <p className="max-w-sm text-sm text-ink-500">The page you're looking for doesn't exist or has moved.</p>
      <Link to={ROUTES.LOGIN} className="btn-secondary">
        Back to sign in
      </Link>
    </div>
  );
}

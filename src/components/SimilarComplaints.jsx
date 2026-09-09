import { Link } from 'react-router-dom';
import { ROUTES } from '../constants';

export default function SimilarComplaints({ retrievedComplaintIds }) {
  if (!retrievedComplaintIds || retrievedComplaintIds.length === 0) {
    return (
      <div className="panel p-4 text-sm text-ink-500">No semantically similar historical complaints were retrieved.</div>
    );
  }

  return (
    <div className="panel p-4">
      <h3 className="text-sm font-semibold text-ink-900">Similar historical complaints</h3>
      <p className="mt-1 text-xs text-ink-500">Retrieved by vector similarity search, not keyword matching.</p>
      <ul className="mt-3 space-y-1">
        {retrievedComplaintIds.map((id) => (
          <li key={id}>
            <Link to={ROUTES.COMPLAINT_DETAILS(id)} className="font-mono text-xs text-campus-600 hover:underline">
              {id}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

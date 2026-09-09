import { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { complaintsApi, ApiError } from '../services/api';
import { ROLES, ROUTES, STATUS, STATUS_LABELS, STATUS_ORDER, FEEDBACK_RATING_MIN, FEEDBACK_RATING_MAX } from '../constants';
import StatusBadge from '../components/StatusBadge';
import PriorityBadge from '../components/PriorityBadge';
import AiRecommendationPanel from '../components/AiRecommendationPanel';
import SimilarComplaints from '../components/SimilarComplaints';
import HistoryTimeline from '../components/HistoryTimeline';
import LoadingState from '../components/LoadingState';
import ErrorBanner from '../components/ErrorBanner';
import ConfirmDialog from '../components/ConfirmDialog';

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

// Statuses a MANAGEMENT_OFFICER/ADMIN may move a complaint forward to from
// its current status. REJECTED is reachable from any non-terminal status by
// an authorized actor with a reason (Final PSD Section 5). The backend is
// the final authority on which transitions are actually permitted — this
// only limits which options the UI offers, matching Zero Trust guidance.
function nextStatusOptions(currentStatus) {
  const idx = STATUS_ORDER.indexOf(currentStatus);
  if (idx === -1 || idx === STATUS_ORDER.length - 1) return [];
  return [STATUS_ORDER[idx + 1]];
}

export default function ComplaintDetails() {
  const { complaintId } = useParams();
  const { role } = useAuth();
  const navigate = useNavigate();

  const [complaint, setComplaint] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notFoundOrForbidden, setNotFoundOrForbidden] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotFoundOrForbidden(false);
    try {
      const [complaintData, historyData] = await Promise.all([
        complaintsApi.get(complaintId),
        complaintsApi.history(complaintId),
      ]);
      setComplaint(complaintData);
      setHistory(historyData?.items ?? historyData ?? []);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 403 || err.status === 404)) {
        setNotFoundOrForbidden(true);
      } else {
        setError(err instanceof ApiError ? err.message : 'Could not load this complaint.');
      }
    } finally {
      setLoading(false);
    }
  }, [complaintId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <LoadingState label="Loading complaint…" />;

  if (notFoundOrForbidden) {
    return (
      <div className="panel p-8 text-center">
        <p className="text-sm font-semibold text-ink-800">This complaint isn't available</p>
        <p className="mt-1 text-sm text-ink-500">
          It may not exist, or you may not have permission to view it.
        </p>
        <button type="button" className="btn-secondary mt-4" onClick={() => navigate(-1)}>
          Go back
        </button>
      </div>
    );
  }

  if (error) return <ErrorBanner message={error} onRetry={load} />;
  if (!complaint) return null;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-2">
        <div className="panel p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-lg font-semibold text-ink-900">{complaint.title}</h1>
              <p className="mt-1 text-xs text-ink-500">
                Submitted {formatDateTime(complaint.created_at)} · {complaint.department || 'Not yet routed'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <PriorityBadge priority={complaint.priority} />
              <StatusBadge status={complaint.status} />
            </div>
          </div>
          <p className="mt-4 whitespace-pre-wrap text-sm text-ink-700">{complaint.description}</p>
        </div>

        <AiRecommendationPanel ai={complaint.ai} />
        <SimilarComplaints retrievedComplaintIds={complaint.ai?.retrieved_complaint_ids} />
        <HistoryTimeline entries={history} />

        {complaint.resolution?.resolution_text && (
          <div className="panel p-5">
            <h3 className="text-sm font-semibold text-ink-900">Resolution</h3>
            <p className="mt-2 whitespace-pre-wrap text-sm text-ink-700">{complaint.resolution.resolution_text}</p>
          </div>
        )}
      </div>

      <div className="space-y-4">
        {(role === ROLES.MANAGEMENT_OFFICER || role === ROLES.ADMIN) && (
          <ManagementActions complaint={complaint} role={role} onUpdated={load} />
        )}
        {role === ROLES.STUDENT && <StudentFeedbackForm complaint={complaint} onUpdated={load} />}
      </div>
    </div>
  );
}

function ManagementActions({ complaint, role, onUpdated }) {
  const [nextStatus, setNextStatus] = useState('');
  const [note, setNote] = useState('');
  const [resolutionText, setResolutionText] = useState('');
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [confirmReject, setConfirmReject] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const forwardOptions = nextStatusOptions(complaint.status);
  const requiresResolution = nextStatus === STATUS.RESOLVED;
  const canReject = role === ROLES.ADMIN && complaint.status !== STATUS.CLOSED && complaint.status !== STATUS.REJECTED;

  const submitStatusChange = async (e) => {
    e.preventDefault();
    if (!nextStatus) return;
    setBusy(true);
    setActionError(null);
    try {
      if (requiresResolution && resolutionText.trim()) {
        await complaintsApi.addResolution(complaint.complaint_id, resolutionText.trim());
      }
      await complaintsApi.update(complaint.complaint_id, { status: nextStatus, note: note.trim() || undefined });
      setNote('');
      setResolutionText('');
      setNextStatus('');
      onUpdated();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not update this complaint.');
    } finally {
      setBusy(false);
    }
  };

  const submitReject = async () => {
    setBusy(true);
    setActionError(null);
    try {
      await complaintsApi.update(complaint.complaint_id, { status: STATUS.REJECTED, note: rejectReason.trim() });
      setConfirmReject(false);
      setRejectReason('');
      onUpdated();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not reject this complaint.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel space-y-4 p-5">
      <h3 className="text-sm font-semibold text-ink-900">Manage this complaint</h3>
      {actionError && <ErrorBanner message={actionError} />}

      {forwardOptions.length > 0 ? (
        <form onSubmit={submitStatusChange} className="space-y-3">
          <div>
            <label htmlFor="next-status" className="field-label">
              Move to
            </label>
            <select
              id="next-status"
              className="field-input"
              value={nextStatus}
              onChange={(e) => setNextStatus(e.target.value)}
            >
              <option value="">Select a status…</option>
              {forwardOptions.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>
          </div>

          {requiresResolution && (
            <div>
              <label htmlFor="resolution-text" className="field-label">
                Resolution details (required to resolve)
              </label>
              <textarea
                id="resolution-text"
                className="field-input min-h-[100px]"
                value={resolutionText}
                onChange={(e) => setResolutionText(e.target.value)}
                placeholder="What was done to fix this?"
                required
              />
            </div>
          )}

          <div>
            <label htmlFor="status-note" className="field-label">
              Note (optional)
            </label>
            <input
              id="status-note"
              className="field-input"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Context for this status change"
            />
          </div>

          <button type="submit" className="btn-primary w-full" disabled={busy || !nextStatus}>
            {busy ? 'Updating…' : 'Update status'}
          </button>
        </form>
      ) : (
        <p className="text-sm text-ink-500">This complaint has reached a final status.</p>
      )}

      {canReject && (
        <button type="button" className="btn-danger w-full" onClick={() => setConfirmReject(true)}>
          Reject complaint
        </button>
      )}

      <ConfirmDialog
        open={confirmReject}
        title="Reject this complaint?"
        description="Provide a reason. This will be recorded in the audit log and visible in the complaint history."
        confirmLabel="Reject"
        danger
        busy={busy}
        onCancel={() => setConfirmReject(false)}
        onConfirm={submitReject}
      />
      {confirmReject && (
        <textarea
          className="field-input mt-2 min-h-[80px]"
          placeholder="Reason for rejection (required)"
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
        />
      )}
    </div>
  );
}

function StudentFeedbackForm({ complaint, onUpdated }) {
  const [rating, setRating] = useState(5);
  const [comments, setComments] = useState('');
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  const eligible = complaint.status === STATUS.RESOLVED || complaint.status === STATUS.CLOSED;

  if (!eligible) {
    return (
      <div className="panel p-5 text-sm text-ink-500">
        Feedback becomes available once this complaint is resolved.
      </div>
    );
  }

  if (submitted) {
    return <div className="panel p-5 text-sm text-emerald-700">Thanks — your feedback has been recorded.</div>;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setSubmitError(null);
    try {
      await complaintsApi.submitFeedback(complaint.complaint_id, rating, comments.trim() || undefined);
      setSubmitted(true);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : 'Could not submit feedback.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="panel space-y-3 p-5">
      <h3 className="text-sm font-semibold text-ink-900">Leave feedback</h3>
      {submitError && <ErrorBanner message={submitError} />}
      <div>
        <label htmlFor="rating" className="field-label">
          Rating ({FEEDBACK_RATING_MIN}–{FEEDBACK_RATING_MAX})
        </label>
        <input
          id="rating"
          type="number"
          min={FEEDBACK_RATING_MIN}
          max={FEEDBACK_RATING_MAX}
          className="field-input"
          value={rating}
          onChange={(e) => setRating(Number(e.target.value))}
        />
      </div>
      <div>
        <label htmlFor="comments" className="field-label">
          Comments (optional)
        </label>
        <textarea
          id="comments"
          className="field-input min-h-[80px]"
          value={comments}
          onChange={(e) => setComments(e.target.value)}
        />
      </div>
      <button type="submit" className="btn-primary w-full" disabled={busy}>
        {busy ? 'Submitting…' : 'Submit feedback'}
      </button>
    </form>
  );
}

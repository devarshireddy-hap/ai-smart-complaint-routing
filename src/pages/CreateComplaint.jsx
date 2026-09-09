import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { complaintsApi, ApiError } from '../services/api';
import { ROUTES } from '../constants';
import ErrorBanner from '../components/ErrorBanner';

const TITLE_MAX = 200;
const DESCRIPTION_MAX = 4000;

function validate({ title, description }) {
  const errors = {};
  if (!title.trim()) {
    errors.title = 'Title is required.';
  } else if (title.length > TITLE_MAX) {
    errors.title = `Title must be ${TITLE_MAX} characters or fewer.`;
  }
  if (!description.trim()) {
    errors.description = 'Description is required.';
  } else if (description.length > DESCRIPTION_MAX) {
    errors.description = `Description must be ${DESCRIPTION_MAX} characters or fewer.`;
  }
  return errors;
}

export default function CreateComplaint() {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errors = validate({ title, description });
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    setSubmitError(null);
    try {
      const created = await complaintsApi.create({ title: title.trim(), description: description.trim() });
      navigate(ROUTES.COMPLAINT_DETAILS(created.complaint_id));
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : 'Could not submit your complaint. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-ink-900">Submit a complaint</h1>
        <p className="text-sm text-ink-500">
          Describe the issue in your own words. The system will analyze it semantically and route it to the
          right department — no need to guess a department yourself.
        </p>
      </div>

      {submitError && <ErrorBanner message={submitError} />}

      <form onSubmit={handleSubmit} className="panel space-y-4 p-5" noValidate>
        <div>
          <label htmlFor="title" className="field-label">
            Title
          </label>
          <input
            id="title"
            className="field-input"
            value={title}
            maxLength={TITLE_MAX}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Street lamp outside Block C is not working"
            aria-invalid={Boolean(fieldErrors.title)}
            aria-describedby={fieldErrors.title ? 'title-error' : undefined}
          />
          {fieldErrors.title && (
            <p id="title-error" className="mt-1 text-xs text-red-600">
              {fieldErrors.title}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="description" className="field-label">
            Description
          </label>
          <textarea
            id="description"
            className="field-input min-h-[140px] resize-y"
            value={description}
            maxLength={DESCRIPTION_MAX}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Explain what's wrong, where it is, and since when — as much detail as helps."
            aria-invalid={Boolean(fieldErrors.description)}
            aria-describedby={fieldErrors.description ? 'description-error' : undefined}
          />
          <div className="mt-1 flex items-center justify-between">
            {fieldErrors.description ? (
              <p id="description-error" className="text-xs text-red-600">
                {fieldErrors.description}
              </p>
            ) : (
              <span />
            )}
            <span className="text-xs text-ink-400">
              {description.length}/{DESCRIPTION_MAX}
            </span>
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={() => navigate(ROUTES.STUDENT_DASHBOARD)}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? 'Submitting…' : 'Submit complaint'}
          </button>
        </div>
      </form>
    </div>
  );
}

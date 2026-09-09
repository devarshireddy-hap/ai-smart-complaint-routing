// Renders AI analysis returned by the backend. The recommendation text and
// any retrieved content are treated as untrusted (Final PSD Section 14 / 36):
// we only render them as plain text via JSX text nodes — never via
// dangerouslySetInnerHTML — so HTML/script the LLM might echo cannot execute.

function ConfidenceBar({ value }) {
  const pct = Math.round((value ?? 0) * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-ink-100">
        <div className="h-full rounded-full bg-campus-500" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-ink-500">{pct}%</span>
    </div>
  );
}

export default function AiRecommendationPanel({ ai }) {
  if (!ai) {
    return <div className="panel p-4 text-sm text-ink-500">AI analysis has not run for this complaint yet.</div>;
  }

  return (
    <div className="panel space-y-4 p-4">
      <h3 className="text-sm font-semibold text-ink-900">AI analysis</h3>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-400">Department confidence</p>
          <ConfidenceBar value={ai.department_confidence} />
        </div>
        {typeof ai.duplicate_score === 'number' && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-ink-400">Duplicate likelihood</p>
            <ConfidenceBar value={ai.duplicate_score} />
          </div>
        )}
      </div>

      {ai.recommendation && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-400">Suggested action</p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-ink-700">{ai.recommendation}</p>
          <p className="mt-1 text-xs text-ink-400">
            This is an AI-generated recommendation. Management review and approval decide the final action.
          </p>
        </div>
      )}
    </div>
  );
}

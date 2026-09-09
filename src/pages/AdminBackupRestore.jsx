import { useState } from 'react';
import { adminApi, ApiError } from '../services/api';
import ConfirmDialog from '../components/ConfirmDialog';
import ErrorBanner from '../components/ErrorBanner';

// This page NEVER performs the actual recovery/rollback in the browser. It
// only triggers the backend's controlled, authorized operation and reports
// the result (Final PSD Section 25 — Admin Rollback/Recovery distinguishes
// business rollback, DB transaction rollback, and disaster recovery; this
// page covers only the disaster-recovery and business-rollback triggers a
// human admin explicitly authorizes).
export default function AdminBackupRestore() {
  const [confirmBackup, setConfirmBackup] = useState(false);
  const [restoreBackupId, setRestoreBackupId] = useState('');
  const [confirmRestore, setConfirmRestore] = useState(false);
  const [rollbackId, setRollbackId] = useState('');
  const [rollbackReason, setRollbackReason] = useState('');
  const [confirmRollback, setConfirmRollback] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const runBackup = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await adminApi.createBackup();
      setMessage(`Backup initiated${result?.backup_id ? ` (ID: ${result.backup_id})` : ''}.`);
      setConfirmBackup(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not start a backup.');
    } finally {
      setBusy(false);
    }
  };

  const runRestore = async () => {
    setBusy(true);
    setError(null);
    try {
      await adminApi.restoreBackup(restoreBackupId.trim());
      setMessage('Restore initiated. This is a disaster-recovery operation and may take time to complete.');
      setConfirmRestore(false);
      setRestoreBackupId('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not start a restore.');
    } finally {
      setBusy(false);
    }
  };

  const runRollback = async () => {
    setBusy(true);
    setError(null);
    try {
      await adminApi.rollback(rollbackId.trim(), rollbackReason.trim());
      setMessage('Business rollback initiated and recorded in the audit log.');
      setConfirmRollback(false);
      setRollbackId('');
      setRollbackReason('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not initiate rollback.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-xl space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-ink-900">Backup, restore & rollback</h1>
        <p className="text-sm text-ink-500">
          These are three distinct mechanisms: database backup/restore is disaster recovery; business rollback
          compensates for an authorized prior action via a new transaction. Both require explicit confirmation
          because they are high-impact operations executed by the backend, not the browser.
        </p>
      </div>

      {message && <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</div>}
      {error && <ErrorBanner message={error} />}

      <div className="panel space-y-3 p-5">
        <h2 className="text-sm font-semibold text-ink-900">Backup</h2>
        <p className="text-sm text-ink-500">Trigger a PostgreSQL logical backup (pg_dump) on the server.</p>
        <button type="button" className="btn-primary" onClick={() => setConfirmBackup(true)}>
          Start backup
        </button>
      </div>

      <div className="panel space-y-3 p-5">
        <h2 className="text-sm font-semibold text-ink-900">Restore</h2>
        <p className="text-sm text-ink-500">Restore the database from a specific backup. This is disaster recovery.</p>
        <input
          type="text"
          className="field-input"
          placeholder="Backup ID"
          value={restoreBackupId}
          onChange={(e) => setRestoreBackupId(e.target.value)}
        />
        <button
          type="button"
          className="btn-danger"
          disabled={!restoreBackupId.trim()}
          onClick={() => setConfirmRestore(true)}
        >
          Start restore
        </button>
      </div>

      <div className="panel space-y-3 p-5">
        <h2 className="text-sm font-semibold text-ink-900">Business rollback</h2>
        <p className="text-sm text-ink-500">
          Compensate for a prior authorized action via a new audited transaction — not a database restore.
        </p>
        <input
          type="text"
          className="field-input"
          placeholder="Rollback target ID"
          value={rollbackId}
          onChange={(e) => setRollbackId(e.target.value)}
        />
        <textarea
          className="field-input min-h-[80px]"
          placeholder="Reason (required, recorded in audit log)"
          value={rollbackReason}
          onChange={(e) => setRollbackReason(e.target.value)}
        />
        <button
          type="button"
          className="btn-danger"
          disabled={!rollbackId.trim() || !rollbackReason.trim()}
          onClick={() => setConfirmRollback(true)}
        >
          Initiate rollback
        </button>
      </div>

      <ConfirmDialog
        open={confirmBackup}
        title="Start a database backup?"
        description="This triggers a backend pg_dump operation."
        confirmLabel="Start backup"
        busy={busy}
        onCancel={() => setConfirmBackup(false)}
        onConfirm={runBackup}
      />
      <ConfirmDialog
        open={confirmRestore}
        title="Restore the database?"
        description={`This will restore from backup ${restoreBackupId || '(unspecified)'}. This is a disaster-recovery action and cannot be undone from the UI.`}
        confirmLabel="Restore"
        danger
        busy={busy}
        onCancel={() => setConfirmRestore(false)}
        onConfirm={runRestore}
      />
      <ConfirmDialog
        open={confirmRollback}
        title="Initiate business rollback?"
        description="A compensating transaction will be created and audited."
        confirmLabel="Rollback"
        danger
        busy={busy}
        onCancel={() => setConfirmRollback(false)}
        onConfirm={runRollback}
      />
    </div>
  );
}

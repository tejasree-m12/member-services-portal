import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client.js";
import { useApi } from "../api/useApi.js";
import { EmptyState, ErrorMessage, Field, Loading, Modal, StatusBadge } from "../components/ui.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { formatDate, formatDateTime, formatFileSize, formatMoney, formatStatus } from "../utils/format.js";

// Button label for each status a claim can move to.
const ACTION_LABELS = {
  in_review: "Start review",
  approved: "Approve",
  denied: "Deny",
  paid: "Mark as paid",
};

function TransitionDialog({ claim, toStatus, onDone, onClose }) {
  const [approvedAmount, setApprovedAmount] = useState(claim.billed_amount);
  const [denialReason, setDenialReason] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const body = { to_status: toStatus, note };
      if (toStatus === "approved") body.approved_amount = approvedAmount;
      if (toStatus === "denied") body.denial_reason = denialReason;
      onDone(await api.post(`/claims/${claim.id}/transition`, body));
    } catch (err) {
      setError(err);
      setSaving(false);
    }
  }

  const isAppeal = toStatus === "in_review" && claim.status === "denied";
  const title = isAppeal ? "Reopen for review" : ACTION_LABELS[toStatus];

  return (
    <Modal title={`${title} — ${claim.claim_number}`} onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <ErrorMessage error={error} />
        {toStatus === "approved" && (
          <Field label={`Approved amount (billed ${formatMoney(claim.billed_amount)})`} error={error?.details?.approved_amount}>
            <input
              inputMode="decimal"
              value={approvedAmount}
              onChange={(event) => setApprovedAmount(event.target.value)}
              required
            />
          </Field>
        )}
        {toStatus === "denied" && (
          <Field label="Reason for denial" error={error?.details?.denial_reason}>
            <input value={denialReason} onChange={(event) => setDenialReason(event.target.value)} required maxLength={255} />
          </Field>
        )}
        <Field label="Note (optional)">
          <textarea value={note} onChange={(event) => setNote(event.target.value)} maxLength={500} rows={3} />
        </Field>
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className={`btn ${toStatus === "denied" ? "btn-danger" : "btn-primary"}`} disabled={saving}>
            {saving ? "Saving…" : title}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export default function ClaimDetailPage() {
  const { claimId } = useParams();
  const { canEdit } = useAuth();
  const { data: claim, error, loading, reload } = useApi(() => api.get(`/claims/${claimId}`), [claimId]);
  const [pendingStatus, setPendingStatus] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef(null);

  if (loading && !claim) return <Loading />;
  if (error) return <ErrorMessage error={error} />;

  async function handleUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    setUploading(true);
    setActionError(null);
    try {
      await api.upload(`/claims/${claim.id}/documents`, file);
      reload();
    } catch (err) {
      setActionError(err);
    } finally {
      setUploading(false);
      fileInput.current.value = ""; // allow choosing the same file again
    }
  }

  async function handleDownload(document) {
    setActionError(null);
    try {
      await api.download(`/claims/${claim.id}/documents/${document.id}`, document.filename);
    } catch (err) {
      setActionError(err);
    }
  }

  return (
    <>
      <p>
        <Link to="/claims">← All claims</Link>
      </p>
      <div className="page-header">
        <h1>
          {claim.claim_number} <StatusBadge status={claim.status} />
        </h1>
        <div className="button-row">
          {/* The server tells us which moves this user may make for this claim. */}
          {claim.allowed_transitions.map((status) => (
            <button
              key={status}
              className={`btn ${status === "denied" ? "btn-danger" : "btn-primary"}`}
              onClick={() => setPendingStatus(status)}
            >
              {status === "in_review" && claim.status === "denied" ? "Reopen for review" : ACTION_LABELS[status]}
            </button>
          ))}
        </div>
      </div>

      <ErrorMessage error={actionError} />

      <section className="card">
        <dl className="details">
          <div>
            <dt>Member</dt>
            <dd>
              <Link to={`/members/${claim.member.id}`}>{claim.member.full_name}</Link> ({claim.member.member_number})
            </dd>
          </div>
          <div><dt>Provider</dt><dd>{claim.provider.name}</dd></div>
          <div><dt>Service date</dt><dd>{formatDate(claim.service_date)}</dd></div>
          <div><dt>Procedure code</dt><dd>{claim.procedure_code}</dd></div>
          <div><dt>Diagnosis code</dt><dd>{claim.diagnosis_code}</dd></div>
          <div><dt>Billed amount</dt><dd>{formatMoney(claim.billed_amount)}</dd></div>
          <div><dt>Approved amount</dt><dd>{formatMoney(claim.approved_amount)}</dd></div>
          {claim.denial_reason && (
            <div><dt>Denial reason</dt><dd>{claim.denial_reason}</dd></div>
          )}
        </dl>
      </section>

      <div className="two-column">
        <section className="card">
          <h2>Status history</h2>
          <ol className="timeline">
            {claim.history.map((entry) => (
              <li key={entry.id}>
                <div>
                  <StatusBadge status={entry.to_status} />
                  {entry.from_status && <span className="muted small"> from {formatStatus(entry.from_status)}</span>}
                </div>
                <div className="muted small">
                  {formatDateTime(entry.changed_at)}
                  {entry.changed_by && ` · ${entry.changed_by}`}
                </div>
                {entry.note && <div>{entry.note}</div>}
              </li>
            ))}
          </ol>
        </section>

        <section className="card">
          <h2>Documents</h2>
          {claim.documents.length === 0 ? (
            <EmptyState>No documents attached.</EmptyState>
          ) : (
            <ul className="document-list">
              {claim.documents.map((document) => (
                <li key={document.id}>
                  <button className="btn btn-link" onClick={() => handleDownload(document)}>
                    {document.filename}
                  </button>
                  <span className="muted small">
                    {formatFileSize(document.size_bytes)} · {formatDateTime(document.uploaded_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {canEdit && (
            <label className="upload">
              <span className="btn">{uploading ? "Uploading…" : "Attach a file"}</span>
              <input
                ref={fileInput}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.txt"
                onChange={handleUpload}
                disabled={uploading}
                hidden
              />
              <span className="muted small"> PDF, PNG, JPG or TXT, up to 5 MB</span>
            </label>
          )}
        </section>
      </div>

      {pendingStatus && (
        <TransitionDialog
          claim={claim}
          toStatus={pendingStatus}
          onClose={() => setPendingStatus(null)}
          onDone={() => {
            setPendingStatus(null);
            reload();
          }}
        />
      )}
    </>
  );
}

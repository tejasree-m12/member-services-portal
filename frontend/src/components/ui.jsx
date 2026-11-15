// Small building blocks shared by the pages.
import { formatStatus } from "../utils/format.js";

export function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{formatStatus(status)}</span>;
}

export function ErrorMessage({ error }) {
  if (!error) return null;
  return (
    <div className="alert alert-error" role="alert">
      {error.message || String(error)}
    </div>
  );
}

export function Loading() {
  return <p className="muted">Loading…</p>;
}

export function EmptyState({ children }) {
  return <p className="empty">{children}</p>;
}

export function Pagination({ page, pages, total, onChange }) {
  if (!total) return null;
  return (
    <div className="pagination">
      <span className="muted">
        Page {page} of {Math.max(pages, 1)} · {total} total
      </span>
      <div>
        <button className="btn" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          Previous
        </button>
        <button className="btn" disabled={page >= pages} onClick={() => onChange(page + 1)}>
          Next
        </button>
      </div>
    </div>
  );
}

// A labelled form input that can show a validation message from the API.
export function Field({ label, error, children }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {error && <span className="field-error">{error}</span>}
    </label>
  );
}

export function Modal({ title, onClose, children }) {
  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-header">
          <h2>{title}</h2>
          <button className="btn btn-plain" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

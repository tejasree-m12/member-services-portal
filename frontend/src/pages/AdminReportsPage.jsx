import { useState } from "react";
import { api } from "../api/client.js";
import { ErrorMessage, Field } from "../components/ui.jsx";
import { formatStatus } from "../utils/format.js";

const STATUSES = ["submitted", "in_review", "approved", "denied", "paid"];

export default function AdminReportsPage() {
  const [status, setStatus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setDownloading(true);
    setError(null);
    try {
      await api.download("/admin/reports/claims.csv", "claims_report.csv", {
        status,
        date_from: dateFrom,
        date_to: dateTo,
      });
    } catch (err) {
      setError(err);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Reports</h1>
      </div>
      <form className="card narrow" onSubmit={handleSubmit}>
        <h2>Claims export (CSV)</h2>
        <p className="muted">Download claims as a spreadsheet file. Leave the filters empty to export everything.</p>
        <ErrorMessage error={error} />
        <Field label="Status">
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">All statuses</option>
            {STATUSES.map((value) => (
              <option key={value} value={value}>
                {formatStatus(value)}
              </option>
            ))}
          </select>
        </Field>
        <div className="form-grid">
          <Field label="Service date from">
            <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          </Field>
          <Field label="Service date to">
            <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          </Field>
        </div>
        <button className="btn btn-primary" disabled={downloading}>
          {downloading ? "Preparing…" : "Download CSV"}
        </button>
      </form>
    </>
  );
}

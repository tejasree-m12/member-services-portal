import { useState } from "react";
import { api } from "../api/client.js";
import { useApi } from "../api/useApi.js";
import { EmptyState, ErrorMessage, Loading, Pagination } from "../components/ui.jsx";
import { formatDateTime } from "../utils/format.js";

const ENTITY_TYPES = ["user", "member", "provider", "claim", "report"];

function describeDetails(details) {
  if (!details) return "";
  return Object.entries(details)
    .map(([key, value]) => {
      if (value && typeof value === "object" && "from" in value && "to" in value) {
        return `${key}: ${value.from ?? "—"} → ${value.to ?? "—"}`;
      }
      return `${key}: ${value ?? "—"}`;
    })
    .join("; ");
}

export default function AuditLogPage() {
  const [entityType, setEntityType] = useState("");
  const [page, setPage] = useState(1);
  const { data, error, loading } = useApi(
    () => api.get("/admin/audit-logs", { entity_type: entityType, page, per_page: 25 }),
    [entityType, page]
  );

  return (
    <>
      <div className="page-header">
        <h1>Audit log</h1>
      </div>
      <p className="muted">Every sign-in and every change to a record, newest first.</p>
      <div className="filters">
        <select
          value={entityType}
          onChange={(event) => {
            setEntityType(event.target.value);
            setPage(1);
          }}
          aria-label="Record type"
        >
          <option value="">All record types</option>
          {ENTITY_TYPES.map((type) => (
            <option key={type}>{type}</option>
          ))}
        </select>
      </div>
      <ErrorMessage error={error} />
      <div className="card">
        {loading && !data ? (
          <Loading />
        ) : data && data.items.length === 0 ? (
          <EmptyState>No activity recorded.</EmptyState>
        ) : (
          data && (
            <table>
              <thead>
                <tr>
                  <th>When</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Record</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((entry) => (
                  <tr key={entry.id}>
                    <td>{formatDateTime(entry.created_at)}</td>
                    <td>{entry.user || "—"}</td>
                    <td>
                      <code>{entry.action}</code>
                    </td>
                    <td>
                      {entry.entity_type}
                      {entry.entity_id ? ` #${entry.entity_id}` : ""}
                    </td>
                    <td className="small">{describeDetails(entry.details)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}
        {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
      </div>
    </>
  );
}

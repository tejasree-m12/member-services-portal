import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { useApi } from "../api/useApi.js";
import { EmptyState, ErrorMessage, Loading, Pagination, StatusBadge } from "../components/ui.jsx";
import { formatDate, formatMoney, formatStatus } from "../utils/format.js";
import { useDebounce } from "../utils/useDebounce.js";

const STATUSES = ["submitted", "in_review", "approved", "denied", "paid"];

export default function ClaimsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const query = useDebounce(search);

  const { data, error, loading } = useApi(
    () => api.get("/claims", { q: query, status, page, per_page: 15 }),
    [query, status, page]
  );

  return (
    <>
      <div className="page-header">
        <h1>Claims</h1>
      </div>
      <p className="muted">To create a claim, open the member's page and choose “New claim”.</p>

      <div className="filters">
        <input
          type="search"
          placeholder="Search by claim number, member number or last name"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
          aria-label="Search claims"
        />
        <select
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setPage(1);
          }}
          aria-label="Status"
        >
          <option value="">All statuses</option>
          {STATUSES.map((value) => (
            <option key={value} value={value}>
              {formatStatus(value)}
            </option>
          ))}
        </select>
      </div>

      <ErrorMessage error={error} />
      <div className="card">
        {loading && !data ? (
          <Loading />
        ) : data && data.items.length === 0 ? (
          <EmptyState>No claims match these filters.</EmptyState>
        ) : (
          data && (
            <table>
              <thead>
                <tr>
                  <th>Claim</th>
                  <th>Member</th>
                  <th>Provider</th>
                  <th>Service date</th>
                  <th className="number">Billed</th>
                  <th className="number">Approved</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((claim) => (
                  <tr key={claim.id}>
                    <td>
                      <Link to={`/claims/${claim.id}`}>{claim.claim_number}</Link>
                    </td>
                    <td>
                      <Link to={`/members/${claim.member.id}`}>{claim.member.full_name}</Link>
                    </td>
                    <td>{claim.provider.name}</td>
                    <td>{formatDate(claim.service_date)}</td>
                    <td className="number">{formatMoney(claim.billed_amount)}</td>
                    <td className="number">{formatMoney(claim.approved_amount)}</td>
                    <td>
                      <StatusBadge status={claim.status} />
                    </td>
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

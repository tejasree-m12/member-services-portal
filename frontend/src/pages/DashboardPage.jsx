import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { useApi } from "../api/useApi.js";
import { EmptyState, ErrorMessage, Loading, StatusBadge } from "../components/ui.jsx";
import { formatDate, formatMoney, formatStatus } from "../utils/format.js";

const STATUS_ORDER = ["submitted", "in_review", "approved", "denied", "paid"];

function StatCard({ label, value, hint }) {
  return (
    <div className="card stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {hint && <div className="muted small">{hint}</div>}
    </div>
  );
}

// A horizontal bar chart drawn with plain CSS widths; no chart library needed.
function BarList({ rows }) {
  const max = Math.max(...rows.map((row) => row.count), 1);
  return (
    <div className="bar-list">
      {rows.map((row) => (
        <div className="bar-row" key={row.label}>
          <span className="bar-label">{row.label}</span>
          <span className="bar-track">
            <span className="bar-fill" style={{ width: `${(row.count / max) * 100}%` }} />
          </span>
          <span className="bar-count">{row.count}</span>
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const { data, error, loading } = useApi(() => api.get("/dashboard/summary"), []);

  if (loading) return <Loading />;
  if (error) return <ErrorMessage error={error} />;

  const { members, providers, claims, recent_claims: recentClaims } = data;

  return (
    <>
      <h1>Dashboard</h1>
      <div className="stat-grid">
        <StatCard label="Active members" value={members.active} hint={`${members.total} total`} />
        <StatCard label="Providers" value={providers.total} />
        <StatCard label="Claims awaiting action" value={claims.awaiting_action} hint={`${claims.total} claims in total`} />
        <StatCard
          label="Approval rate"
          value={claims.approval_rate === null ? "—" : `${claims.approval_rate}%`}
          hint="of decided claims"
        />
        <StatCard label="Total billed" value={formatMoney(claims.total_billed)} />
        <StatCard label="Total approved" value={formatMoney(claims.total_approved)} />
      </div>

      <div className="two-column">
        <section className="card">
          <h2>Claims by status</h2>
          <BarList
            rows={STATUS_ORDER.map((status) => ({
              label: formatStatus(status),
              count: claims.by_status[status].count,
            }))}
          />
        </section>
        <section className="card">
          <h2>Active members by plan</h2>
          {members.by_plan_type.length === 0 ? (
            <EmptyState>No active members yet.</EmptyState>
          ) : (
            <BarList rows={members.by_plan_type.map((row) => ({ label: row.plan_type, count: row.count }))} />
          )}
        </section>
      </div>

      <section className="card">
        <h2>Most recent claims</h2>
        {recentClaims.length === 0 ? (
          <EmptyState>No claims yet.</EmptyState>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Claim</th>
                <th>Member</th>
                <th>Service date</th>
                <th className="number">Billed</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {recentClaims.map((claim) => (
                <tr key={claim.id}>
                  <td>
                    <Link to={`/claims/${claim.id}`}>{claim.claim_number}</Link>
                  </td>
                  <td>{claim.member.full_name}</td>
                  <td>{formatDate(claim.service_date)}</td>
                  <td className="number">{formatMoney(claim.billed_amount)}</td>
                  <td>
                    <StatusBadge status={claim.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}

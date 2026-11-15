import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client.js";
import { useApi } from "../api/useApi.js";
import { ClaimForm, MemberForm } from "../components/forms.jsx";
import { EmptyState, ErrorMessage, Loading, Modal, Pagination, StatusBadge } from "../components/ui.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { formatDate, formatMoney } from "../utils/format.js";

export default function MemberDetailPage() {
  const { memberId } = useParams();
  const navigate = useNavigate();
  const { canEdit, isAdmin } = useAuth();
  const [dialog, setDialog] = useState(null); // "edit" | "claim" | "deactivate" | null
  const [claimsPage, setClaimsPage] = useState(1);
  const [actionError, setActionError] = useState(null);

  const member = useApi(() => api.get(`/members/${memberId}`), [memberId]);
  const claims = useApi(
    () => api.get(`/members/${memberId}/claims`, { page: claimsPage, per_page: 10 }),
    [memberId, claimsPage]
  );

  if (member.loading && !member.data) return <Loading />;
  if (member.error) return <ErrorMessage error={member.error} />;
  const data = member.data;

  async function deactivate() {
    setActionError(null);
    try {
      await api.delete(`/members/${data.id}`);
      setDialog(null);
      member.reload();
    } catch (err) {
      setActionError(err);
    }
  }

  return (
    <>
      <p>
        <Link to="/members">← All members</Link>
      </p>
      <div className="page-header">
        <h1>
          {data.full_name} <StatusBadge status={data.status} />
        </h1>
        <div className="button-row">
          {canEdit && (
            <button className="btn" onClick={() => setDialog("edit")}>
              Edit
            </button>
          )}
          {canEdit && data.status === "active" && (
            <button className="btn btn-primary" onClick={() => setDialog("claim")}>
              New claim
            </button>
          )}
          {isAdmin && data.status === "active" && (
            <button className="btn btn-danger" onClick={() => setDialog("deactivate")}>
              Deactivate
            </button>
          )}
        </div>
      </div>

      <section className="card">
        <dl className="details">
          <div><dt>Member number</dt><dd>{data.member_number}</dd></div>
          <div><dt>Date of birth</dt><dd>{formatDate(data.date_of_birth)}</dd></div>
          <div><dt>Plan type</dt><dd>{data.plan_type}</dd></div>
          <div><dt>Email</dt><dd>{data.email || "—"}</dd></div>
          <div><dt>Phone</dt><dd>{data.phone || "—"}</dd></div>
          <div><dt>Primary provider</dt><dd>{data.primary_provider ? data.primary_provider.name : "—"}</dd></div>
        </dl>
      </section>

      <section className="card">
        <h2>Claims</h2>
        <ErrorMessage error={claims.error} />
        {claims.loading && !claims.data ? (
          <Loading />
        ) : claims.data && claims.data.items.length === 0 ? (
          <EmptyState>This member has no claims.</EmptyState>
        ) : (
          claims.data && (
            <table>
              <thead>
                <tr>
                  <th>Claim</th>
                  <th>Provider</th>
                  <th>Service date</th>
                  <th className="number">Billed</th>
                  <th className="number">Approved</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {claims.data.items.map((claim) => (
                  <tr key={claim.id}>
                    <td>
                      <Link to={`/claims/${claim.id}`}>{claim.claim_number}</Link>
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
        {claims.data && (
          <Pagination
            page={claims.data.page}
            pages={claims.data.pages}
            total={claims.data.total}
            onChange={setClaimsPage}
          />
        )}
      </section>

      {dialog === "edit" && (
        <Modal title="Edit member" onClose={() => setDialog(null)}>
          <MemberForm
            member={data}
            onCancel={() => setDialog(null)}
            onSaved={() => {
              setDialog(null);
              member.reload();
            }}
          />
        </Modal>
      )}
      {dialog === "claim" && (
        <Modal title="New claim" onClose={() => setDialog(null)}>
          <ClaimForm member={data} onCancel={() => setDialog(null)} onSaved={(claim) => navigate(`/claims/${claim.id}`)} />
        </Modal>
      )}
      {dialog === "deactivate" && (
        <Modal title="Deactivate member" onClose={() => setDialog(null)}>
          <p>
            {data.full_name} will be marked inactive and no new claims can be created for them. Their record and
            existing claims are kept.
          </p>
          <ErrorMessage error={actionError} />
          <div className="form-actions">
            <button className="btn" onClick={() => setDialog(null)}>
              Cancel
            </button>
            <button className="btn btn-danger" onClick={deactivate}>
              Deactivate member
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}

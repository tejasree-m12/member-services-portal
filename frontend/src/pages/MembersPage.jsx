import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useApi } from "../api/useApi.js";
import { MemberForm, PLAN_TYPES } from "../components/forms.jsx";
import { EmptyState, ErrorMessage, Loading, Modal, Pagination, StatusBadge } from "../components/ui.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { formatDate } from "../utils/format.js";
import { useDebounce } from "../utils/useDebounce.js";

export default function MembersPage() {
  const { canEdit } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [planType, setPlanType] = useState("");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const query = useDebounce(search);

  const { data, error, loading } = useApi(
    () => api.get("/members", { q: query, status, plan_type: planType, page, per_page: 15 }),
    [query, status, planType, page]
  );

  // Changing a filter goes back to page 1; otherwise you could be left on a
  // page number that no longer exists.
  const changeFilter = (setter) => (event) => {
    setter(event.target.value);
    setPage(1);
  };

  return (
    <>
      <div className="page-header">
        <h1>Members</h1>
        {canEdit && (
          <button className="btn btn-primary" onClick={() => setCreating(true)}>
            New member
          </button>
        )}
      </div>

      <div className="filters">
        <input
          type="search"
          placeholder="Search by name or member number"
          value={search}
          onChange={changeFilter(setSearch)}
          aria-label="Search members"
        />
        <select value={status} onChange={changeFilter(setStatus)} aria-label="Status">
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
        <select value={planType} onChange={changeFilter(setPlanType)} aria-label="Plan type">
          <option value="">All plans</option>
          {PLAN_TYPES.map((plan) => (
            <option key={plan}>{plan}</option>
          ))}
        </select>
      </div>

      <ErrorMessage error={error} />
      <div className="card">
        {loading && !data ? (
          <Loading />
        ) : data && data.items.length === 0 ? (
          <EmptyState>No members match these filters.</EmptyState>
        ) : (
          data && (
            <table>
              <thead>
                <tr>
                  <th>Member #</th>
                  <th>Name</th>
                  <th>Date of birth</th>
                  <th>Plan</th>
                  <th>Primary provider</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((member) => (
                  <tr key={member.id}>
                    <td>
                      <Link to={`/members/${member.id}`}>{member.member_number}</Link>
                    </td>
                    <td>{member.full_name}</td>
                    <td>{formatDate(member.date_of_birth)}</td>
                    <td>{member.plan_type}</td>
                    <td>{member.primary_provider ? member.primary_provider.name : "—"}</td>
                    <td>
                      <StatusBadge status={member.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}
        {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
      </div>

      {creating && (
        <Modal title="New member" onClose={() => setCreating(false)}>
          <MemberForm onCancel={() => setCreating(false)} onSaved={(member) => navigate(`/members/${member.id}`)} />
        </Modal>
      )}
    </>
  );
}

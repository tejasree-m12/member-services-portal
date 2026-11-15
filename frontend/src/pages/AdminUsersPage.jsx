import { useState } from "react";
import { api } from "../api/client.js";
import { useApi } from "../api/useApi.js";
import { UserForm } from "../components/forms.jsx";
import { ErrorMessage, Loading, Modal, Pagination } from "../components/ui.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { formatDateTime } from "../utils/format.js";

export default function AdminUsersPage() {
  const { user: currentUser } = useAuth();
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const [actionError, setActionError] = useState(null);
  const { data, error, loading, reload } = useApi(() => api.get("/admin/users", { page, per_page: 15 }), [page]);

  async function update(user, changes) {
    setActionError(null);
    try {
      await api.patch(`/admin/users/${user.id}`, changes);
      reload();
    } catch (err) {
      setActionError(err);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Users</h1>
        <button className="btn btn-primary" onClick={() => setCreating(true)}>
          New user
        </button>
      </div>
      <ErrorMessage error={error || actionError} />
      <div className="card">
        {loading && !data ? (
          <Loading />
        ) : (
          data && (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.items.map((user) => {
                  const isSelf = user.id === currentUser.id;
                  return (
                    <tr key={user.id}>
                      <td>
                        {user.full_name} {isSelf && <span className="muted small">(you)</span>}
                      </td>
                      <td>{user.email}</td>
                      <td>
                        <select
                          value={user.role}
                          disabled={isSelf}
                          onChange={(event) => update(user, { role: event.target.value })}
                          aria-label={`Role for ${user.full_name}`}
                        >
                          <option value="admin">admin</option>
                          <option value="agent">agent</option>
                          <option value="viewer">viewer</option>
                        </select>
                      </td>
                      <td>
                        <span className={`badge ${user.is_active ? "badge-active" : "badge-inactive"}`}>
                          {user.is_active ? "Active" : "Deactivated"}
                        </span>
                      </td>
                      <td>{formatDateTime(user.created_at)}</td>
                      <td className="number">
                        {!isSelf && (
                          <button className="btn btn-small" onClick={() => update(user, { is_active: !user.is_active })}>
                            {user.is_active ? "Deactivate" : "Reactivate"}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )
        )}
        {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
      </div>

      {creating && (
        <Modal title="New user" onClose={() => setCreating(false)}>
          <UserForm
            onCancel={() => setCreating(false)}
            onSaved={() => {
              setCreating(false);
              reload();
            }}
          />
        </Modal>
      )}
    </>
  );
}

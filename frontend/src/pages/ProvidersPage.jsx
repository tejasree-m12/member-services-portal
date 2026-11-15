import { useState } from "react";
import { api } from "../api/client.js";
import { useApi } from "../api/useApi.js";
import { ProviderForm } from "../components/forms.jsx";
import { EmptyState, ErrorMessage, Loading, Modal, Pagination } from "../components/ui.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useDebounce } from "../utils/useDebounce.js";

export default function ProvidersPage() {
  const { isAdmin } = useAuth();
  const [search, setSearch] = useState("");
  const [accepting, setAccepting] = useState("");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const [actionError, setActionError] = useState(null);
  const query = useDebounce(search);

  const { data, error, loading, reload } = useApi(
    () => api.get("/providers", { q: query, accepting, page, per_page: 15 }),
    [query, accepting, page]
  );

  async function toggleAccepting(provider) {
    setActionError(null);
    try {
      await api.put(`/providers/${provider.id}`, { accepting_patients: !provider.accepting_patients });
      reload();
    } catch (err) {
      setActionError(err);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Providers</h1>
        {isAdmin && (
          <button className="btn btn-primary" onClick={() => setCreating(true)}>
            New provider
          </button>
        )}
      </div>

      <div className="filters">
        <input
          type="search"
          placeholder="Search by name, NPI or city"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
          aria-label="Search providers"
        />
        <select
          value={accepting}
          onChange={(event) => {
            setAccepting(event.target.value);
            setPage(1);
          }}
          aria-label="Accepting patients"
        >
          <option value="">All providers</option>
          <option value="true">Accepting new patients</option>
          <option value="false">Not accepting new patients</option>
        </select>
      </div>

      <ErrorMessage error={error || actionError} />
      <div className="card">
        {loading && !data ? (
          <Loading />
        ) : data && data.items.length === 0 ? (
          <EmptyState>No providers match these filters.</EmptyState>
        ) : (
          data && (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>NPI</th>
                  <th>Specialty</th>
                  <th>Location</th>
                  <th>Phone</th>
                  <th>New patients</th>
                  {isAdmin && <th />}
                </tr>
              </thead>
              <tbody>
                {data.items.map((provider) => (
                  <tr key={provider.id}>
                    <td>{provider.name}</td>
                    <td>{provider.npi}</td>
                    <td>{provider.specialty}</td>
                    <td>
                      {provider.city}, {provider.state}
                    </td>
                    <td>{provider.phone || "—"}</td>
                    <td>
                      <span className={`badge ${provider.accepting_patients ? "badge-active" : "badge-inactive"}`}>
                        {provider.accepting_patients ? "Accepting" : "Not accepting"}
                      </span>
                    </td>
                    {isAdmin && (
                      <td className="number">
                        <button className="btn btn-small" onClick={() => toggleAccepting(provider)}>
                          {provider.accepting_patients ? "Stop accepting" : "Start accepting"}
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}
        {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
      </div>

      {creating && (
        <Modal title="New provider" onClose={() => setCreating(false)}>
          <ProviderForm
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

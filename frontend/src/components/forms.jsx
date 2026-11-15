// Create/edit forms shown inside a Modal.
import { useState } from "react";
import { api } from "../api/client.js";
import { useApi } from "../api/useApi.js";
import { ErrorMessage, Field } from "./ui.jsx";

export const PLAN_TYPES = ["HMO", "PPO", "EPO", "Medicare Advantage"];

// Shared form behaviour: keep the values, submit them, and show either a
// general error or the per-field messages the API sends back with a 422.
function useForm(initialValues, submit, onSaved) {
  const [values, setValues] = useState(initialValues);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const bind = (name) => ({
    value: values[name] ?? "",
    onChange: (event) => setValues((current) => ({ ...current, [name]: event.target.value })),
  });

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      onSaved(await submit(values));
    } catch (err) {
      setError(err);
      setSaving(false);
    }
  }

  const fieldErrors = error?.details || {};
  // Show the banner only when there is no field-level message to show instead.
  const generalError = error && Object.keys(fieldErrors).length === 0 ? error : null;
  return { values, bind, handleSubmit, saving, fieldErrors, generalError };
}

function useProviderOptions() {
  const { data } = useApi(() => api.get("/providers", { per_page: 100 }), []);
  return data ? data.items : [];
}

function FormActions({ saving, onCancel, label = "Save" }) {
  return (
    <div className="form-actions">
      <button type="button" className="btn" onClick={onCancel}>
        Cancel
      </button>
      <button className="btn btn-primary" disabled={saving}>
        {saving ? "Saving…" : label}
      </button>
    </div>
  );
}

export function MemberForm({ member, onSaved, onCancel }) {
  const providers = useProviderOptions();
  const form = useForm(
    {
      first_name: member?.first_name || "",
      last_name: member?.last_name || "",
      date_of_birth: member?.date_of_birth || "",
      email: member?.email || "",
      phone: member?.phone || "",
      plan_type: member?.plan_type || "HMO",
      primary_provider_id: member?.primary_provider?.id || "",
    },
    (values) => {
      const body = {
        ...values,
        primary_provider_id: values.primary_provider_id ? Number(values.primary_provider_id) : null,
      };
      return member ? api.put(`/members/${member.id}`, body) : api.post("/members", body);
    },
    onSaved
  );
  const { bind, fieldErrors } = form;

  return (
    <form onSubmit={form.handleSubmit}>
      <ErrorMessage error={form.generalError} />
      <div className="form-grid">
        <Field label="First name" error={fieldErrors.first_name}>
          <input {...bind("first_name")} required maxLength={80} />
        </Field>
        <Field label="Last name" error={fieldErrors.last_name}>
          <input {...bind("last_name")} required maxLength={80} />
        </Field>
        <Field label="Date of birth" error={fieldErrors.date_of_birth}>
          <input type="date" {...bind("date_of_birth")} required />
        </Field>
        <Field label="Plan type" error={fieldErrors.plan_type}>
          <select {...bind("plan_type")}>
            {PLAN_TYPES.map((plan) => (
              <option key={plan}>{plan}</option>
            ))}
          </select>
        </Field>
        <Field label="Email (optional)" error={fieldErrors.email}>
          <input type="email" {...bind("email")} />
        </Field>
        <Field label="Phone (optional)" error={fieldErrors.phone}>
          <input {...bind("phone")} />
        </Field>
      </div>
      <Field label="Primary provider (optional)" error={fieldErrors.primary_provider_id}>
        <select {...bind("primary_provider_id")}>
          <option value="">None</option>
          {providers.map((provider) => (
            <option key={provider.id} value={provider.id}>
              {provider.name} — {provider.specialty}
            </option>
          ))}
        </select>
      </Field>
      <FormActions saving={form.saving} onCancel={onCancel} />
    </form>
  );
}

export function ClaimForm({ member, onSaved, onCancel }) {
  const providers = useProviderOptions();
  const form = useForm(
    {
      provider_id: member.primary_provider?.id || "",
      service_date: "",
      procedure_code: "",
      diagnosis_code: "",
      billed_amount: "",
    },
    (values) =>
      api.post("/claims", {
        ...values,
        member_id: member.id,
        provider_id: values.provider_id ? Number(values.provider_id) : null,
      }),
    onSaved
  );
  const { bind, fieldErrors } = form;

  return (
    <form onSubmit={form.handleSubmit}>
      <p className="muted">
        Member: {member.full_name} ({member.member_number})
      </p>
      <ErrorMessage error={form.generalError} />
      <Field label="Provider" error={fieldErrors.provider_id}>
        <select {...bind("provider_id")} required>
          <option value="">Select a provider</option>
          {providers.map((provider) => (
            <option key={provider.id} value={provider.id}>
              {provider.name} — {provider.specialty}
            </option>
          ))}
        </select>
      </Field>
      <div className="form-grid">
        <Field label="Service date" error={fieldErrors.service_date}>
          <input type="date" {...bind("service_date")} required />
        </Field>
        <Field label="Billed amount (USD)" error={fieldErrors.billed_amount}>
          <input inputMode="decimal" placeholder="150.00" {...bind("billed_amount")} required />
        </Field>
        <Field label="Procedure code (CPT/HCPCS)" error={fieldErrors.procedure_code}>
          <input placeholder="99213" {...bind("procedure_code")} required maxLength={5} />
        </Field>
        <Field label="Diagnosis code (ICD-10)" error={fieldErrors.diagnosis_code}>
          <input placeholder="E11.9" {...bind("diagnosis_code")} required maxLength={8} />
        </Field>
      </div>
      <FormActions saving={form.saving} onCancel={onCancel} label="Submit claim" />
    </form>
  );
}

export function ProviderForm({ onSaved, onCancel }) {
  const form = useForm(
    { npi: "", name: "", specialty: "", city: "", state: "", phone: "" },
    (values) => api.post("/providers", values),
    onSaved
  );
  const { bind, fieldErrors } = form;

  return (
    <form onSubmit={form.handleSubmit}>
      <ErrorMessage error={form.generalError} />
      <div className="form-grid">
        <Field label="NPI (10 digits)" error={fieldErrors.npi}>
          <input {...bind("npi")} required maxLength={10} />
        </Field>
        <Field label="Name" error={fieldErrors.name}>
          <input {...bind("name")} required maxLength={150} />
        </Field>
        <Field label="Specialty" error={fieldErrors.specialty}>
          <input {...bind("specialty")} required maxLength={100} />
        </Field>
        <Field label="Phone (optional)" error={fieldErrors.phone}>
          <input {...bind("phone")} />
        </Field>
        <Field label="City" error={fieldErrors.city}>
          <input {...bind("city")} required maxLength={100} />
        </Field>
        <Field label="State (2 letters)" error={fieldErrors.state}>
          <input {...bind("state")} required maxLength={2} />
        </Field>
      </div>
      <FormActions saving={form.saving} onCancel={onCancel} />
    </form>
  );
}

export function UserForm({ onSaved, onCancel }) {
  const form = useForm(
    { full_name: "", email: "", role: "agent", password: "" },
    (values) => api.post("/admin/users", values),
    onSaved
  );
  const { bind, fieldErrors } = form;

  return (
    <form onSubmit={form.handleSubmit}>
      <ErrorMessage error={form.generalError} />
      <Field label="Full name" error={fieldErrors.full_name}>
        <input {...bind("full_name")} required maxLength={120} />
      </Field>
      <Field label="Email" error={fieldErrors.email}>
        <input type="email" {...bind("email")} required />
      </Field>
      <div className="form-grid">
        <Field label="Role" error={fieldErrors.role}>
          <select {...bind("role")}>
            <option value="admin">admin</option>
            <option value="agent">agent</option>
            <option value="viewer">viewer</option>
          </select>
        </Field>
        <Field label="Temporary password (8+ characters)" error={fieldErrors.password}>
          <input type="password" {...bind("password")} required minLength={8} autoComplete="new-password" />
        </Field>
      </div>
      <FormActions saving={form.saving} onCancel={onCancel} label="Create user" />
    </form>
  );
}

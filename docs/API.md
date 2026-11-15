# API reference

Base URL: `/api/v1`. All request and response bodies are JSON unless stated.

## Conventions

**Authentication.** Call `POST /auth/login` to get an access token, then send it on every request:

```
Authorization: Bearer <access_token>
```

Tokens expire after 60 minutes (configurable with `JWT_ACCESS_TOKEN_MINUTES`).

**Roles.**

| Role | Can do |
|---|---|
| `viewer` | Read members, providers, claims and the dashboard |
| `agent` | Everything a viewer can, plus create/update members, create claims, review/approve/deny claims, upload documents |
| `admin` | Everything an agent can, plus manage providers and users, deactivate members, mark claims paid, read the audit log, export reports |

**Errors.** Every error has the same shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Some fields are invalid.",
    "details": { "date_of_birth": "Use the date format YYYY-MM-DD." }
  }
}
```

| Status | Meaning |
|---|---|
| 400 | Malformed request (body is not JSON, bad query parameter) |
| 401 | Missing, invalid or expired token; wrong email or password |
| 403 | Signed in, but the role is not allowed to do this |
| 404 | Record or route not found |
| 409 | Conflict with the current state (duplicate NPI, illegal claim status change) |
| 413 | Upload larger than 5 MB |
| 422 | Validation failed; `details` maps field names to messages |
| 500 | Unexpected server error (details are logged, not returned) |

**Pagination.** List endpoints accept `page` (default 1) and `per_page` (default 20, maximum 100) and return:

```json
{ "items": [], "page": 1, "per_page": 20, "total": 0, "pages": 0 }
```

**Data formats.** Dates are `YYYY-MM-DD`. Timestamps are UTC, e.g. `2026-01-15T14:05:09Z`. Money is a string with two decimals, e.g. `"150.00"`, so no precision is lost.

---

## Health

### `GET /health`
No authentication. Returns `200 {"status": "ok", "database": "ok"}`, or `503` if the database cannot be reached.

## Authentication

### `POST /auth/login`
```json
{ "email": "agent@example.com", "password": "Agent#12345" }
```
`200`:
```json
{
  "access_token": "eyJ...",
  "user": { "id": 2, "email": "agent@example.com", "full_name": "Jordan Agent", "role": "agent", "is_active": true, "created_at": "2026-01-10T09:00:00Z" }
}
```
`401 invalid_credentials` for a wrong email, wrong password or deactivated account (the message is the same in all three cases).

### `GET /auth/me`
Returns `{"user": {...}}` for the token's owner.

---

## Module 1: Member and provider directory

### `GET /members`
Roles: any. Query: `q` (matches first name, last name or member number), `status` (`active`/`inactive`), `plan_type`, `page`, `per_page`.

Member object:
```json
{
  "id": 1,
  "member_number": "MBR-10000",
  "first_name": "Maria",
  "last_name": "Lopez",
  "full_name": "Maria Lopez",
  "date_of_birth": "1984-03-12",
  "email": "maria.lopez0@example.com",
  "phone": "555-0200",
  "plan_type": "PPO",
  "status": "active",
  "primary_provider": { "id": 4, "name": "Dr. Wei Kim" },
  "created_at": "2026-01-10T09:00:00Z",
  "updated_at": "2026-01-10T09:00:00Z"
}
```

### `POST /members`
Roles: agent, admin. Returns `201` with the member.

| Field | Required | Rules |
|---|---|---|
| `first_name`, `last_name` | yes | up to 80 characters |
| `date_of_birth` | yes | `YYYY-MM-DD`, not in the future |
| `plan_type` | yes | `HMO`, `PPO`, `EPO` or `Medicare Advantage` |
| `email` | no | valid email |
| `phone` | no | 7 to 20 characters: digits, spaces, `+ - ( ) .` |
| `primary_provider_id` | no | id of an existing provider |
| `status` | no | `active` (default) or `inactive` |

### `GET /members/{id}`
Roles: any.

### `PUT /members/{id}`
Roles: agent, admin. Send only the fields to change; the rest are left as they are.

### `DELETE /members/{id}`
Roles: admin. Soft delete: sets `status` to `inactive` and returns the member. The row is kept.

### `GET /members/{id}/claims`
Roles: any. Paginated list of the member's claims, newest first.

### `GET /providers`
Roles: any. Query: `q` (name, NPI or city), `specialty`, `state`, `accepting` (`true`/`false`), `page`, `per_page`.

```json
{ "id": 4, "npi": "1234567893", "name": "Dr. Wei Kim", "specialty": "Cardiology", "city": "Chicago", "state": "IL", "phone": "555-0103", "accepting_patients": true }
```

### `POST /providers`
Roles: admin. Fields: `npi` (10 digits with a valid check digit; must be unique, otherwise `409`), `name`, `specialty`, `city`, `state` (2 letters), `phone` (optional), `accepting_patients` (optional, default `true`).

### `GET /providers/{id}`, `PUT /providers/{id}`
Read: any role. Update: admin; send only the fields to change.

---

## Module 2: Claims workflow

Status flow:

```
submitted -> in_review -> approved -> paid
                 |  ^
                 v  |   (appeal)
               denied
```

### `GET /claims`
Roles: any. Query: `q` (claim number, member number or member last name), `status`, `member_id`, `provider_id`, `page`, `per_page`. Newest first.

### `POST /claims`
Roles: agent, admin. Returns `201`. The new claim's status is `submitted`.

| Field | Rules |
|---|---|
| `member_id` | an existing, **active** member |
| `provider_id` | an existing provider |
| `service_date` | `YYYY-MM-DD`, not in the future |
| `procedure_code` | CPT (5 digits) or HCPCS (letter + 4 digits) |
| `diagnosis_code` | ICD-10 format, e.g. `E11.9` |
| `billed_amount` | greater than zero, at most two decimals |

### `GET /claims/{id}`
Roles: any. Returns the claim with its history, documents and the status changes the caller may make:

```json
{
  "id": 17,
  "claim_number": "CLM-100016",
  "member": { "id": 3, "member_number": "MBR-10002", "full_name": "Omar Patel" },
  "provider": { "id": 4, "name": "Dr. Wei Kim" },
  "service_date": "2026-01-15",
  "procedure_code": "99213",
  "diagnosis_code": "E11.9",
  "billed_amount": "150.00",
  "approved_amount": null,
  "status": "in_review",
  "denial_reason": null,
  "created_at": "2026-01-16T10:00:00Z",
  "updated_at": "2026-01-17T08:30:00Z",
  "history": [
    { "id": 30, "from_status": null, "to_status": "submitted", "note": "Claim created.", "changed_by": "Jordan Agent", "changed_at": "2026-01-16T10:00:00Z" },
    { "id": 31, "from_status": "submitted", "to_status": "in_review", "note": null, "changed_by": "Jordan Agent", "changed_at": "2026-01-17T08:30:00Z" }
  ],
  "documents": [],
  "allowed_transitions": ["approved", "denied"]
}
```

### `POST /claims/{id}/transition`
Roles: agent, admin (only admin may move a claim to `paid`).

```json
{ "to_status": "approved", "approved_amount": "135.00", "note": "Within plan limits." }
```

| `to_status` | Extra rules |
|---|---|
| `in_review` | from `submitted`, or from `denied` (appeal; clears the denial reason) |
| `approved` | `approved_amount` required, and not more than the billed amount |
| `denied` | `denial_reason` required |
| `paid` | admin only; from `approved` |

Errors: `409` if the move is not allowed from the current status, `403` if the role may not make it, `422` if a required value is missing or invalid.

### `POST /claims/{id}/documents`
Roles: agent, admin. `multipart/form-data` with one field named `file`. Allowed types: pdf, png, jpg, jpeg, txt. Maximum 5 MB. Returns `201`:

```json
{ "id": 5, "filename": "receipt.pdf", "content_type": "application/pdf", "size_bytes": 48211, "uploaded_by": "Jordan Agent", "uploaded_at": "2026-01-17T08:35:00Z" }
```

### `GET /claims/{id}/documents/{document_id}`
Roles: any. Returns the file as a download.

---

## Module 3: Admin tools and reporting

### `GET /dashboard/summary`
Roles: any.

```json
{
  "members": { "active": 36, "total": 40, "by_plan_type": [ { "plan_type": "PPO", "count": 11 } ] },
  "providers": { "total": 12 },
  "claims": {
    "total": 120,
    "by_status": { "submitted": { "count": 20, "billed_amount": "4523.00" }, "in_review": {}, "approved": {}, "denied": {}, "paid": {} },
    "total_billed": "26596.00",
    "total_approved": "13242.20",
    "approval_rate": 80.7,
    "awaiting_action": 37
  },
  "recent_claims": []
}
```

`approval_rate` is the percentage of decided claims (approved, paid or denied) that were approved or paid; `null` when nothing has been decided. `awaiting_action` counts `submitted` plus `in_review`.

### `GET /admin/users`
Roles: admin. Paginated.

### `POST /admin/users`
Roles: admin. Fields: `email`, `full_name`, `role` (`admin`/`agent`/`viewer`), `password` (8 to 128 characters). `409` if the email is taken.

### `PATCH /admin/users/{id}`
Roles: admin. Any of `full_name`, `role`, `is_active`, `password`. Role and active changes take effect on the user's next request. An admin cannot deactivate or demote their own account (`409`).

### `GET /admin/audit-logs`
Roles: admin. Query: `action`, `entity_type`, `user_id`, `page`, `per_page`. Newest first.

```json
{ "id": 88, "user": "Jordan Agent", "action": "claim.transition", "entity_type": "claim", "entity_id": 17, "details": { "from": "submitted", "to": "in_review" }, "created_at": "2026-01-17T08:30:00Z" }
```

Actions recorded: `login`, `member.create`, `member.update`, `member.deactivate`, `provider.create`, `provider.update`, `claim.create`, `claim.transition`, `claim.document_upload`, `user.create`, `user.update`, `report.claims_export`.

### `GET /admin/reports/claims.csv`
Roles: admin. Query: `status`, `date_from`, `date_to` (service date, inclusive). Returns a CSV file with the columns:

```
claim_number, member_number, member_name, provider_npi, provider_name, service_date,
procedure_code, diagnosis_code, billed_amount, approved_amount, status, denial_reason
```

---

## Try it with curl

```bash
TOKEN=$(curl -s -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"agent@example.com","password":"Agent#12345"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s "http://localhost:5000/api/v1/members?q=lopez" -H "Authorization: Bearer $TOKEN"
```

The same requests work in Postman: set the `Authorization` header to `Bearer <token>`.

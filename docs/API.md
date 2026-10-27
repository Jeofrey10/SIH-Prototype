# REST API Specification (API.md)

Base URL: `/api/v1`  
Authentication: HTTP Bearer JWT Header (`Authorization: Bearer <token>`)

---

## 1. Authentication (`/auth`)

| Method | Path | Required Role | Description |
|---|---|---|---|
| `POST` | `/auth/login` | Public | Authenticates official via email/username and password. Returns JWT token and user profile. Tracks failed attempts (lockout at 5 failures). |
| `GET` | `/auth/me` | Authenticated | Returns currently authenticated user details, permissions, and assigned bureau. |
| `POST` | `/auth/change-password` | Authenticated | Changes password for the currently authenticated user. |

---

## 2. Complaints Management (`/complaints`)

| Method | Path | Required Role | Description |
|---|---|---|---|
| `GET` | `/complaints` | Authenticated | Lists complaints with filters: `scope` (`bureau` vs `all`), `status`, `category`, `priority`, `bureau_code`, `is_overdue`, `search`, and pagination. |
| `POST` | `/complaints` | `RB_OFFICIAL`, `PGRC_OFFICIAL`, `SUPERVISOR`, `SYSTEM_ADMIN` | Registers a new complaint, initiates assignment, and triggers automated relation detection. |
| `GET` | `/complaints/{id}` | Authenticated | Retrieves detailed complaint record, allowed status transitions, case assignments, and relations. Redacts sensitive details if `SUMMARY` access. |
| `PATCH` | `/complaints/{id}` | Authenticated | Updates complaint details with optimistic locking check (`version`). |
| `POST` | `/complaints/{id}/status` | Authenticated | Transitions status with required reason and optional resolution summary. Enforces valid lifecycle state machine and optimistic lock. |
| `POST` | `/complaints/{id}/escalate` | Authenticated | Sets escalation flag and notifies Bureau Supervisor. |
| `POST` | `/complaints/{id}/notes` | Authenticated (Participating) | Appends an internal investigation case note. |
| `POST` | `/complaints/{id}/participants` | `SUPERVISOR`, `SYSTEM_ADMIN` | Adds a participating bureau with assignment rationale. |
| `POST` | `/complaints/{id}/transfer-primary` | `SUPERVISOR`, `SYSTEM_ADMIN` | Transfers primary handling bureau with justification. |

---

## 3. Duplicate & Related Grievances (`/relations`)

| Method | Path | Required Role | Description |
|---|---|---|---|
| `POST` | `/relations/related-preview` | Authenticated | Evaluates draft complaint against institution candidates in memory without database persistence (for live UI preview). |
| `GET` | `/relations/queue` | Authenticated | Retrieves relations review queue with status filter (`PENDING_REVIEW`, `CONFIRMED`, `DISMISSED`) and `min_score`. |
| `GET` | `/relations/complaint/{complaint_id}` | Authenticated | Retrieves all relations associated with a specific complaint. |
| `POST` | `/relations/{id}/confirm` | Authenticated | Confirms relation with classification (`DUPLICATE`, `RELATED_INCIDENT`, `FOLLOW_UP`) and optional auto-participation. |
| `POST` | `/relations/{id}/dismiss` | Authenticated | Dismisses flagged relation with mandatory explanation. |
| `POST` | `/relations/{id}/revert` | `SUPERVISOR`, `SYSTEM_ADMIN` | Reverts confirmed or dismissed decision back to `PENDING_REVIEW`. |

---

## 4. Institutions Directory (`/institutions`)

| Method | Path | Required Role | Description |
|---|---|---|---|
| `GET` | `/institutions` | Authenticated | Lists institutions with search by AICTE ID, Name, City, or State, plus complaint counts. |
| `GET` | `/institutions/{id}` | Authenticated | Retrieves institution details and summary metrics. |
| `GET` | `/institutions/{id}/coordination` | Authenticated | Multi-bureau coordination summary across active cases. |
| `GET` | `/institutions/{id}/timeline` | Authenticated | Chronological consolidated audit of grievances, updates, and resolutions across all bureaus. |

---

## 5. Analytics & Dashboard (`/analytics`)

| Method | Path | Required Role | Description |
|---|---|---|---|
| `GET` | `/analytics/summary` | Authenticated | Summary KPI numbers (active, overdue, pending reviews, multi-bureau cases, avg resolution days). |
| `GET` | `/analytics/status-distribution` | Authenticated | Live counts for all 7 lifecycle statuses (zero-filled). |
| `GET` | `/analytics/bureau-workload` | Authenticated | Active and overdue case counts grouped by bureau. |
| `GET` | `/analytics/aging-buckets` | Authenticated | Aging distribution (<7d, 7-14d, 15-30d, >30d) for open cases. |
| `GET` | `/analytics/trend` | Authenticated | 30-day daily intake vs resolution trend. |
| `GET` | `/analytics/top-institutions` | Authenticated | Institutions with highest volume of open complaints. |

---

## 6. Reports & Export (`/reports`)

| Method | Path | Required Role | Description |
|---|---|---|---|
| `GET` | `/reports/overdue` | Authenticated | Overdue SLA audit report preview (JSON). |
| `GET` | `/reports/overdue/csv` | Authenticated | Streams sanitized CSV file of overdue cases with formula injection protection. |
| `GET` | `/reports/complaints` | Authenticated | Grievance master report preview (JSON). |
| `GET` | `/reports/complaints/csv` | Authenticated | Streams sanitized CSV master grievance export. |

---

## 7. Notifications (`/notifications`)

| Method | Path | Required Role | Description |
|---|---|---|---|
| `GET` | `/notifications` | Authenticated | Lists user notifications with `is_read` filtering. |
| `PATCH` | `/notifications/{id}/read` | Authenticated | Marks a single notification as read. |
| `POST` | `/notifications/read-all` | Authenticated | Marks all unread notifications for current user as read. |

---

## 8. Administration (`/users`, `/audit`, `/system`)

| Method | Path | Required Role | Description |
|---|---|---|---|
| `GET` | `/users` | `SYSTEM_ADMIN` | Lists all official user accounts. |
| `POST` | `/users` | `SYSTEM_ADMIN` | Provisions a new official account. |
| `PATCH` | `/users/{id}/activate` | `SYSTEM_ADMIN` | Activates an official account. |
| `PATCH` | `/users/{id}/deactivate` | `SYSTEM_ADMIN` | Deactivates an official account (immediately revokes access). |
| `POST` | `/users/{id}/reset-password` | `SYSTEM_ADMIN` | Resets official user's password. |
| `GET` | `/audit` | `SYSTEM_ADMIN` | Lists immutable system audit logs with before/after state payloads. |
| `GET` | `/system/health` | Public | System health check (database ping, uptime, clock). |
| `POST` | `/system/jobs/overdue-scan`| `SUPERVISOR`, `SYSTEM_ADMIN` | Triggers immediate idempotent scan for SLA breaches. |

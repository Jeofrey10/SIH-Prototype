# Implementation Plan & Phase Tracking (IMPLEMENTATION_PLAN.md)

Tracking document for all phases specified in Section 21 and Section 19 of the master implementation prompt.

---

## Phase Checklist

- [x] **Phase 0: Workspace Inspection & Plan Initialization**
  - Inspected repository structure, recorded tool versions (Python 3.13.2, Node v22.14.0, npm 10.9.2).
  - Documented PostgreSQL availability constraints and decisions.

- [x] **Phase 1: Scaffolding & Configuration**
  - Backend configuration (`app/core/config.py`), security (`security.py`), error envelopes (`errors.py`), logging (`logging.py`), clocks (`clock.py`).
  - Frontend Vite + React 18 + TypeScript + Tailwind setup.
  - Environment templates (`.env.example`) and Docker Compose configuration.

- [x] **Phase 2: Database Schema & Migration**
  - SQLAlchemy 2.0 ORM models for Bureau, User, Institution, Complaint, CaseAssignment, StatusHistory, ComplaintNote, ComplaintRelation, Notification, AuditLog.
  - Alembic initial schema migration (`0001_initial_schema.py`).
  - Optimized composite indexes, unique constraints, and canonical ordering check constraints.

- [x] **Phase 3: Vertical Slice & Authentication**
  - Argon2id password hashing + JWT issue and verify.
  - Role-Based Access Control matrix (`app/core/permissions.py`) for `SYSTEM_ADMIN`, `SUPERVISOR`, `RB_OFFICIAL`, `PGRC_OFFICIAL`.
  - Auth routes (`/auth/login`, `/auth/me`, `/auth/change-password`) and user lockout tracking.

- [x] **Phase 4: Full Authorization & Access Level Redaction**
  - Redaction of complaints to `access_level="SUMMARY"` for non-participating bureau officials.
  - Strict enforcement of `allowed_actions` per lifecycle state and role.
  - `ACCESS_DENIED` auditing on 403 authorization failures.

- [x] **Phase 5: Complaint Features & Institution Management**
  - Full complaint registration, optimistic locking (`version`), notes, priority, SLA tracking.
  - Institution directory with active/overdue KPI aggregations, cross-bureau coordination summary, and unified chronological timeline.

- [x] **Phase 6: Multi-Bureau Case Coordination**
  - Case assignment tracking for primary and participating bureaus.
  - Jurisdictional transfers, supervisor participation assignment, and participant-scoped collaboration.

- [x] **Phase 7: Duplicate / Related Grievance Detection (Algorithm v1.0)**
  - Normalizer: tokenizer, suffix-stemmer, custom technical domain stopwords.
  - Scorer: Section 10 formula (Category Match, Sublinear TF-IDF Cosine Similarity, Domain Vocabulary Overlap, Incident Reference Identifier Floor, Incident Date Proximity Decay).
  - Review queue: `CONFIRM` (with auto-participation flag), `DISMISS`, and Supervisor `REVERT`.
  - Frontend live debounced related preview panel with `MatchExplanationCard`.

- [x] **Phase 8: Notifications & Overdue Scan Job**
  - In-process APScheduler background scanner.
  - Idempotent scan with dedupe keys (`OVERDUE:<complaint_id>:<date>`).
  - Notification management (read, mark all read, deep links).

- [x] **Phase 9: Analytics & Statutory CSV Reports**
  - Live analytics endpoints: summary KPIs, zero-filled status distribution across all 7 statuses, bureau workload, aging buckets, 30-day intake trend, top institutions.
  - CSV export with spreadsheet formula-injection guard (`'`, `+`, `-`, `=`, `@`).

- [x] **Phase 10: Deterministic Synthetic Dataset Generator**
  - Deterministic seed fixture (`random.seed(20260101)`).
  - Seed fixture includes `SYN-TN-0001` Meridian Institute of Technology and negative control pairs.
  - CLI command `python -m app.cli seed` and `seed --reset`.

- [x] **Phase 11: Complete Frontend Implementation**
  - TopBar with live unread notification polling and user designation.
  - Sidebar with dynamic pending relations queue counter.
  - Reusable DataTable with pagination, sorting, search, and loading/empty states.
  - Full pages: `LoginPage`, `DashboardPage`, `ComplaintsPage`, `ComplaintCreatePage`, `ComplaintDetailPage`, `RelationsQueuePage`, `InstitutionsPage`, `InstitutionDetailPage`, `NotificationsPage`, `ReportsPage`, `UsersAdminPage`, `AuditLogsAdminPage`, `ErrorPages`.
  - Embedded `"Prototype - synthetic data only"` banner.

- [x] **Phase 12: Testing & Verification**
  - Backend unit test suite: 12 passed in 0.55s.
  - Frontend Vitest suite: 3 test files, 10 tests passed in 1.52s.
  - TypeScript strict typecheck passed with 0 errors.
  - Linting passed with 0 errors.
  - Production build completed successfully in 4.42s.
  - Section 19 E2E scenario implemented with clear diagnostics.

- [x] **Phase 13: Documentation**
  - `docs/DECISIONS.md`
  - `docs/ARCHITECTURE.md`
  - `docs/API.md`
  - `docs/TROUBLESHOOTING.md`
  - `docs/VERIFICATION_REPORT.md`
  - `README.md`

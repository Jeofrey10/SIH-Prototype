# Architecture & Engineering Decisions (DECISIONS.md)

This document records the architectural, algorithmic, and engineering decisions made during the design and implementation of the **AICTE Integrated Institution Complaint Monitoring and Status Dashboard**.

---

## 1. Role-Based Access Control (RBAC) Architecture
- **Decision**: Implemented a fixed enum of four official roles: `SYSTEM_ADMIN`, `SUPERVISOR`, `RB_OFFICIAL`, and `PGRC_OFFICIAL`. No dynamic permissions tables are used.
- **Rationale**: Strict role clarity avoids complexity and security holes. Bureau officials (`RB_OFFICIAL`, `PGRC_OFFICIAL`) belong strictly to their bureau (`RB`, `PGRC`), while `SUPERVISOR` and `SYSTEM_ADMIN` have cross-bureau visibility.
- **Allowed Actions**: Computed dynamically per complaint by `app/core/permissions.py::compute_allowed_actions()` based on user role, participation status (PRIMARY vs PARTICIPATING vs NONE), and complaint lifecycle state.
- **Confidentiality / Redaction**: When an official accesses a case where their bureau is neither PRIMARY nor PARTICIPATING, the API returns `access_level="SUMMARY"` with complainant and internal note fields redacted.

---

## 2. Duplicate & Related Grievance Detection Algorithm v1.0
- **Decision**: Implemented as pure, deterministic mathematical functions in `app/services/relations/normalizer.py` and `app/services/relations/scorer.py`. No opaque AI/LLM models or external API calls are required.
- **Candidate Pool**: Restricted strictly to complaints for the *same* `institution_id` (candidate pool size is bounded per institution).
- **Canonical Ordering**: To prevent duplicate relations between pairs, canonical order `complaint_a_id < complaint_b_id` is enforced in the database table and query layer.
- **Scoring Components (Total 0–100)**:
  1. *Category Match* (0 or 15 pts)
  2. *Text Similarity* (Cosine on Sublinear TF with Suffix Stemming & Stopwords, up to 35 pts)
  3. *Shared Domain Terms* (Technical education domain vocabulary, up to 25 pts)
  4. *Incident Reference Exact Match* (Alphanumeric order/receipt identifiers, 40 pts floor)
  5. *Incident Date Proximity* (Decay over 30 days, up to 15 pts)
- **Review Workflow**: Relations with score ≥ 35 are flagged as `PENDING_REVIEW`. Officials review via the Relations Queue to `CONFIRM` or `DISMISS`. A `REVERT` action is reserved strictly for Supervisors. Never auto-merged.

---

## 3. Database Layer & PostgreSQL Compatibility
- **Decision**: Built on SQLAlchemy 2.0 with PostgreSQL 15+ dialect types (`UUID(as_uuid=True)`, `JSONB`, `ARRAY`). SQLite was intentionally excluded as required by the technical specification due to PostgreSQL array operators, JSON indexing, and strict concurrency controls.
- **Driver**: Migrated from `psycopg-binary==3.2.1` to `psycopg[binary]>=3.2.3` because the host Python version is 3.13.2, and prebuilt Windows wheels for Python 3.13 are available in psycopg 3.2.3+.
- **Database Availability Fallback**: When running in an environment without an active Docker daemon or PostgreSQL server, unit tests run in isolation with 100% pass rates, and integration tests gracefully skip with clear instructions for running Docker or installing local PostgreSQL.
- **Optimistic Locking**: Every `complaints` record includes an integer `version` field incremented on every modification to eliminate lost updates.

---

## 4. Frontend Technology Stack & User Experience
- **Framework**: React 18 with TypeScript in strict mode, bundled with Vite 5.
- **State Management & Caching**: TanStack Query v5 for server state caching, background polling (notifications polled every 30s, relation queue badges polled every 60s), and optimistic mutations.
- **Styling**: Tailwind CSS with custom Indian enterprise design tokens (`brand-900` deep navy, `surface` cards, accessible focus rings).
- **Banner**: Mandatory prototype disclosure banner `"Prototype - synthetic data only"` permanently embedded in the footer and top navigation.
- **Zero Decorative Controls**: Every interactive button, filter, and action corresponds to an active API endpoint or valid client-side state mutation.

---

## 5. Security & Audit Logging
- **Password Hashing**: Argon2id via `argon2-cffi`.
- **Authentication**: JWT access tokens signed with HMAC-SHA256 and configured with configurable expiration (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- **Audit Logs**: Immutable append-only log capturing `actor_id`, `action`, `entity_type`, `entity_id`, `before_data`, `after_data`, `ip_address`, and `occurred_at`. Access denials generate `ACCESS_DENIED` audit events.
- **CSV Formula Injection Defense**: All exported cells in CSV reports starting with `=`, `+`, `-`, or `@` are prefixed with a single quote (`'`) to neutralize spreadsheet command execution.

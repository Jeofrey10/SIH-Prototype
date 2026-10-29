# 🏛️ AICTE Integrated Institution Complaint Monitoring & Status Dashboard

## Complete Project Documentation

---

> **Smart India Hackathon (SIH) Prototype** — A centralized, real-time multi-bureau grievance monitoring, cross-bureau coordination, and intelligent duplicate detection platform for the **All India Council for Technical Education (AICTE)**.

---

## 📋 Table of Contents

1. [The Idea & Problem Statement](#1-the-idea--problem-statement)
2. [Core Functions & Features](#2-core-functions--features)
3. [Technology Stack](#3-technology-stack)
4. [System Architecture](#4-system-architecture)
5. [Innovation & USPs](#5-innovation--usps)
6. [Creative & Unique Implementations](#6-creative--unique-implementations)
7. [Database Design & Data Model](#7-database-design--data-model)
8. [Algorithm Deep-Dive: Duplicate Detection v1.0](#8-algorithm-deep-dive-duplicate-detection-v10)
9. [Security Architecture](#9-security-architecture)
10. [Frontend Design & UX](#10-frontend-design--ux)
11. [API Surface](#11-api-surface)
12. [Testing & Quality Assurance](#12-testing--quality-assurance)
13. [Deployment & DevOps](#13-deployment--devops)

---

## 1. The Idea & Problem Statement

### 🎯 The Problem

AICTE receives complaints about technical education institutions from students, faculty, and stakeholders. These complaints are handled by **multiple independent bureaus** — primarily the **Regulation Bureau (RB)** and the **Public Grievance Redressal Cell (PGRC)** — each operating in isolation.

This siloed approach creates critical operational failures:

| Pain Point | Impact |
|---|---|
| **No cross-bureau visibility** | The same institution's violations are investigated independently by RB and PGRC without mutual awareness |
| **Duplicate effort** | Two bureaus unknowingly investigate the same issue, wasting government resources |
| **Conflicting actions** | Bureaus may issue contradictory directives to the same institution |
| **Accountability gaps** | Cases fall into "limbo" — transferred but never accepted, or stalled with no recorded reason |
| **No delay transparency** | Overdue cases have no audit trail explaining *why* they are delayed |
| **Manual coordination** | Inter-bureau collaboration requires phone calls and emails with no structured tracking |

### 💡 The Solution

A **unified, real-time grievance command center** where:
- Every complaint is institution-centric, giving a 360° view of all active cases against an institution across all bureaus
- Potentially related or duplicate complaints are **automatically detected** using a deterministic, explainable algorithm — never auto-merged, always human-reviewed
- **Cross-bureau coordination** is formally tracked with handover contracts, acceptance/return workflows, and participation flags
- Every action is recorded in an **append-only, tamper-evident audit trail**
- Cases stalling in **bureaucratic limbo** are automatically surfaced with severity-coded flags
- SLA compliance is continuously monitored with overdue scanning and notification dispatch

---

## 2. Core Functions & Features

### 2.1 Multi-Bureau Grievance Management

- **Primary vs Participating Bureau Model**: Each complaint has one primary bureau (RB or PGRC) responsible for resolution, plus zero or more participating bureaus who collaborate
- **Cross-Bureau Jurisdictional Transfer**: Supervisor-initiated formal handover with structured context, key findings, and explicit accept/return workflow
- **Institution-Centric View**: Unified dashboard per institution showing all active cases, bureau coordination status, and a chronological cross-bureau timeline

### 2.2 Complaint Lifecycle (7 Stages)

```
SUBMITTED → UNDER_REVIEW → ASSIGNED → IN_INVESTIGATION → PENDING_INSTITUTION_ACTION → RESOLVED → CLOSED
                    ↑                                              ↓
                    └──────────── REOPENED (Disputed Resolution) ←──┘
```

- Strict state machine enforcement — invalid transitions are blocked
- Optimistic locking via `version` field to prevent lost updates in concurrent editing
- Supervisor-only closure authority (RESOLVED → CLOSED)

### 2.3 Duplicate & Related Grievance Detection (Algorithm v1.0)

- **Pure deterministic scoring** (0–100) with 5 weighted components
- **Live preview panel** — debounced real-time matching as officials type a new complaint
- **Explainable Match Cards** — point-by-point rule breakdown showing exactly why complaints were flagged
- **Human review pipeline**: `CONFIRM` → `DISMISS` → Supervisor `REVERT`
- **Issue Threads** — confirmed related complaints are automatically grouped into investigation threads with combined briefs

### 2.4 Handover Contract System

- **Initiate**: Supervisor creates handover with mandatory context summary (≥20 chars) and key findings
- **Accept**: Receiving bureau formally accepts; old bureau is retained as participant
- **Return**: Receiving bureau can return with mandatory explanation (≥10 chars)
- **IN_TRANSIT state**: Complaints show a distinct "in transit" status during handover
- Full notification dispatch to receiving bureau officials upon initiation

### 2.5 Waiting-On Ledger (Delay Accountability)

- Structured "waiting on" entries: `INSTITUTION_REPLY`, `BUREAU_OPINION`, `DOCUMENT_SUBMISSION`, `COMMITTEE_REVIEW`, `SUPERVISOR_APPROVAL`, `OTHER`
- Designated **chaser official** per waiting entry
- Auto-creation when status transitions to `PENDING_INFORMATION`
- Auto-resolution when complaint moves to `RESOLVED` or `CLOSED`
- Duration metrics computed in real-time

### 2.6 Limbo & Ping-Pong Detector

Automatic detection of silently stalled complaints with severity-coded flags:

| Flag Code | Rule | Severity |
|---|---|---|
| `UNACCEPTED_HANDOVER` | Transferred >24h ago, not yet accepted | WARNING / CRITICAL (>48h) |
| `NO_COMMITMENT` | Open case idle ≥7 days with no waiting entry | WARNING / CRITICAL (≥14d) |
| `PING_PONG` | ≥2 inter-bureau primary transfers | WARNING / CRITICAL (≥3) |
| `STATUS_FLIP_FLOP` | Status oscillates ≥2 reversals (A→B→A→B) | WARNING |
| `UNASSIGNED_CHASER` | Waiting entry open ≥3 days with no chaser | WARNING |

### 2.7 Deterministic Delay Explainer

Generates human-readable, context-aware status sentences — **no generative AI, no hallucinations**:
- Explicitly states "reason not recorded" when data is absent
- Covers all lifecycle stages: Closed, Resolved, In Transit, Waiting, Overdue, Stalled, On Track
- Tone-coded: `info`, `success`, `warning`, `danger`, `muted`

### 2.8 Real-Time Analytics Dashboard

- **Summary KPIs**: Active cases, overdue count, pending reviews, multi-bureau cases, average resolution days
- **Status Distribution**: Zero-filled bar chart across all 7 lifecycle stages
- **Bureau Workload**: Active and overdue counts per bureau
- **Aging Buckets**: <7d, 7-14d, 15-30d, >30d distribution for open cases
- **30-Day Intake Trend**: Daily intake vs. resolution line chart
- **Top Institutions**: Institutions with highest complaint volume

### 2.9 Statutory CSV Export

- Overdue SLA audit reports and master grievance reports
- **Formula-injection sanitized** — all cells starting with `=`, `+`, `-`, `@` are prefixed with `'` to prevent spreadsheet command execution

### 2.10 Strict Role-Based Access Control (RBAC)

| Role | Scope | Key Permissions |
|---|---|---|
| `SUPERVISOR` | Cross-bureau oversight | Full access, closure authority, transfers, reverts |
| `RB_OFFICIAL` | Regulation Bureau cases | Register, investigate, resolve within RB scope |
| `PGRC_OFFICIAL` | Grievance Cell cases | Register, investigate, resolve within PGRC scope |
| `SYSTEM_ADMIN` | System operations | User provisioning, audit logs, system jobs |

- **Dynamic `allowed_actions`** computed per complaint based on role + participation status + lifecycle state
- **Automatic redaction** to `access_level="SUMMARY"` when non-participating bureaus view a case
- **`PermissionGate` component** — React component wrapping children with role-based visibility checks

### 2.11 Append-Only Tamper-Evident Audit Trail

- Tracks: logins, registrations, status updates, relation decisions, handover events, access denials (`ACCESS_DENIED`)
- Captures `before_data` and `after_data` JSON snapshots, actor ID, IP address, and timestamp
- `ACCESS_DENIED` events are logged when 403 authorization failures occur

### 2.12 Notification System

- In-process APScheduler background scanner for overdue detection
- Idempotent scan with dedup keys (`OVERDUE:<complaint_id>:<date>`)
- Real-time unread count polling (30s interval) and badge updates
- Deep-linkable notifications pointing to relevant complaint/institution pages

---

## 3. Technology Stack

### Backend

| Component | Technology | Purpose |
|---|---|---|
| **Framework** | FastAPI ≥0.115 | High-performance async API server with auto-generated OpenAPI docs |
| **ORM** | SQLAlchemy 2.0 (Typed) | Modern declarative ORM with native type annotations |
| **Migrations** | Alembic ≥1.13 | Database schema version control and migrations |
| **Validation** | Pydantic v2 + pydantic-settings | Request/response validation with settings management |
| **Database Driver** | psycopg[binary] ≥3.2.3 | Native PostgreSQL async driver (Python 3.13 compatible) |
| **Password Hashing** | argon2-cffi ≥23.1 | Argon2id — memory-hard, GPU-resistant hashing |
| **Authentication** | PyJWT ≥2.9 | HMAC-SHA256 signed JWT access tokens |
| **Job Scheduling** | APScheduler ≥3.10 | In-process background job scheduling (overdue scans) |
| **Server** | Uvicorn[standard] ≥0.30 | ASGI server with hot reload |

### Frontend

| Component | Technology | Purpose |
|---|---|---|
| **Framework** | React 18 | Component-based UI with concurrent features |
| **Language** | TypeScript (strict mode) | End-to-end type safety |
| **Bundler** | Vite 5 | Near-instant HMR and optimized production builds |
| **Styling** | Tailwind CSS 3.4 | Utility-first CSS with custom Indian enterprise design tokens |
| **Routing** | React Router v6 | Client-side routing with RBAC-guarded routes |
| **Server State** | TanStack Query v5 | Caching, background polling, optimistic mutations |
| **Forms** | React Hook Form + Zod | Performant forms with schema validation |
| **Charts** | Recharts 2.13 | Composable data visualization |
| **Icons** | Lucide React | Consistent, accessible iconography |
| **Utilities** | clsx, tailwind-merge, date-fns | Conditional classes, date formatting |

### Database

| Component | Technology | Purpose |
|---|---|---|
| **RDBMS** | PostgreSQL 15+ | Production-grade relational database with JSONB, UUID, ARRAY support |
| **Containerization** | Docker Compose | One-command database setup (`docker compose up -d db`) |

### Testing

| Layer | Technology | Results |
|---|---|---|
| **Backend Unit** | pytest | 12 tests passed (0.55s) |
| **Frontend Component** | Vitest + React Testing Library + MSW | 10 tests passed (1.52s) |
| **Type Safety** | TypeScript strict mode | 0 errors |
| **Linting** | oxlint | 0 errors |
| **Production Build** | Vite build | Succeeded (4.42s) |

---

## 4. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CLIENT (Browser)                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌───────────┐ ┌──────────────┐  │
│  │ UI Components│ │ TanStack     │ │ Auth Ctx  │ │ React Router │  │
│  │ & AppShell   │ │ Query Cache  │ │ + JWT     │ │ v6 + Guards  │  │
│  └──────┬───────┘ └──────┬───────┘ └─────┬─────┘ └──────┬───────┘  │
│         └────────────────┴───────────────┴──────────────┘          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Bearer JWT (HTTPS)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              SERVER (FastAPI Modular Monolith)                       │
│  ┌────────────┐ ┌───────────────┐ ┌────────────────┐               │
│  │ API Routers│ │ Dependency    │ │ Domain Services│               │
│  │ /api/v1    │→│ Injection +   │→│ Layer          │               │
│  │            │ │ RBAC Guard    │ │                │               │
│  └────────────┘ └───────────────┘ └───────┬────────┘               │
│                                           │                         │
│  ┌────────────────────┐  ┌────────────────┴────────────────┐       │
│  │ APScheduler Jobs   │  │ Algorithm v1.0 Scorer+Normalizer│       │
│  │ (Overdue Scanner)  │  │ (Deterministic NLP)             │       │
│  └────────┬───────────┘  └─────────────────────────────────┘       │
└───────────┼─────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│              DATA & STORAGE (PostgreSQL 15+)                        │
│  ┌───────────────┐  ┌──────────────────┐  ┌───────────────────┐    │
│  │ PostgreSQL DB │  │ Append-Only      │  │ Immutability      │    │
│  │ (13 tables)   │  │ Audit Logs       │  │ Triggers          │    │
│  └───────────────┘  └──────────────────┘  └───────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Backend Modular Architecture

```
backend/app/
├── main.py                     # FastAPI app factory + middleware + startup hooks
├── cli.py                      # CLI commands (seed, seed --reset)
│
├── core/                       # Cross-cutting concerns
│   ├── config.py               # Pydantic settings (env-driven configuration)
│   ├── security.py             # JWT issue/verify + Argon2id hashing
│   ├── permissions.py          # RBAC matrix + allowed_actions computation
│   ├── errors.py               # Standardized error envelope factory
│   ├── logging.py              # Structured logging setup
│   └── clock.py                # Testable clock abstraction
│
├── models/                     # SQLAlchemy 2.0 ORM models
│   └── __init__.py             # Bureau, User, Institution, Complaint,
│                               # CaseAssignment, StatusHistory, ComplaintNote,
│                               # ComplaintRelation, Notification, AuditLog,
│                               # WaitingOnEntry, Handover, IssueThread
│
├── schemas/                    # Pydantic v2 request/response schemas
├── db/                         # Database session & engine management
├── seed/                       # Deterministic synthetic data generator
├── jobs/                       # APScheduler background jobs (overdue scan)
│
├── api/v1/routers/             # FastAPI route modules
│   ├── auth.py                 # /auth/* endpoints
│   ├── complaints.py           # /complaints/* endpoints
│   ├── relations.py            # /relations/* endpoints
│   ├── institutions.py         # /institutions/* endpoints
│   ├── analytics.py            # /analytics/* endpoints
│   ├── reports.py              # /reports/* endpoints
│   ├── notifications.py        # /notifications/* endpoints
│   ├── users.py                # /users/* admin endpoints
│   └── system.py               # /system/* health & jobs
│
└── services/                   # Domain services (business logic)
    ├── auth.py                 # Authentication & session management
    ├── complaints.py           # Complaint CRUD, status transitions, lifecycle
    ├── institutions.py         # Institution directory, coordination, timeline
    ├── analytics.py            # KPI computation, distributions, trends
    ├── reports.py              # CSV export with formula injection defense
    ├── notifications.py        # Notification dispatch & management
    ├── audit.py                # Immutable audit log writer
    ├── users.py                # User provisioning & management
    ├── handover.py             # ★ Inter-bureau handover contracts
    ├── waiting_on.py           # ★ Delay accountability ledger
    ├── delay_explainer.py      # ★ Deterministic status sentence generator
    ├── limbo_detector.py       # ★ Limbo & ping-pong detector
    ├── threads.py              # ★ Issue thread grouping for related cases
    └── relations/              # ★ Duplicate detection engine
        ├── normalizer.py       #   Unicode NFKC, tokenizer, suffix stemmer
        ├── scorer.py           #   5-component scoring formula
        └── service.py          #   Review queue management
```

### Frontend Architecture

```
frontend/src/
├── main.tsx                    # App entry point
├── App.tsx                     # Root component with providers
├── index.css                   # Global styles + Tailwind directives
├── App.css                     # App-level styles
│
├── api/                        # Typed API client layer
│   ├── index.ts                # Module-organized API functions
│   ├── client.ts               # HTTP client with JWT injection
│   └── types.ts                # TypeScript interfaces for API responses
│
├── auth/                       # Authentication & authorization
│   ├── AuthProvider.tsx        # React context for auth state
│   ├── useAuth.ts              # Custom hook for consuming auth context
│   └── PermissionGate.tsx      # Role-based visibility wrapper component
│
├── lib/                        # Shared utilities
├── routes/                     # React Router config + RBAC guards
│
├── components/                 # Reusable UI components
│   ├── AppShell.tsx            # Layout shell (TopBar + Sidebar + Content)
│   ├── Navigation.tsx          # Sidebar with dynamic badge counters
│   ├── DataTable.tsx           # Pagination, sorting, search, states
│   ├── KpiCard.tsx             # Analytics metric cards
│   ├── Badges.tsx              # Status, priority, role badges
│   ├── MatchExplanationCard.tsx# Algorithm score breakdown display
│   ├── ConfirmModal.tsx        # Reusable confirmation dialogs
│   └── EmptyState.tsx          # Empty data placeholder
│
└── pages/                      # 13 full page components
    ├── LoginPage.tsx           # Login with quick-fill role buttons
    ├── DashboardPage.tsx       # Analytics dashboard with charts
    ├── ComplaintsPage.tsx      # Complaint list with filters
    ├── ComplaintCreatePage.tsx # Registration with live relation preview
    ├── ComplaintDetailPage.tsx # Full detail with timeline & actions
    ├── RelationsQueuePage.tsx  # Relation review queue
    ├── InstitutionsPage.tsx    # Institution directory
    ├── InstitutionDetailPage.tsx# Institution coordination profile
    ├── NotificationsPage.tsx   # Notification center
    ├── ReportsPage.tsx         # CSV export center
    ├── UsersAdminPage.tsx      # User provisioning (Admin only)
    ├── AuditLogsAdminPage.tsx  # Audit trail explorer (Admin only)
    └── ErrorPages.tsx          # 404 / 403 error pages
```

---

## 5. Innovation & USPs

### 🧠 1. Deterministic Duplicate Detection Without AI/ML

Unlike traditional approaches that rely on opaque machine learning models or LLMs, our **Algorithm v1.0** is:
- **Fully deterministic** — same inputs always produce the same score
- **Explainable** — point-by-point breakdown card showing exactly *why* two complaints are flagged
- **Zero external dependencies** — no API calls, no model inference, no GPU required
- **Human-in-the-loop** — never auto-merges; officials review, confirm, or dismiss

### 🔄 2. Handover Contract System

A first-of-its-kind **formal inter-bureau transfer protocol**:
- Mandatory context briefing (≥20 characters of case summary)
- Explicit 3-state workflow: `PENDING → ACCEPTED / RETURNED`
- Old bureau automatically retained as participant (institutional memory preserved)
- Real-time notifications to receiving bureau officials
- Full audit trail with before/after state capture

### 📊 3. Waiting-On Ledger for Delay Accountability

Unlike traditional ticketing systems that only track status changes, this system introduces a **structured "waiting on" ledger**:
- Records *what* is being waited for, *from whom*, and *since when*
- Assigns a **designated chaser** responsible for follow-up
- Auto-syncs with lifecycle transitions (e.g., auto-creates entry on `PENDING_INFORMATION`)
- Computes real-time **duration metrics** for accountability dashboards

### 🕳️ 4. Limbo & Ping-Pong Detector

**Proactive stall detection** that government systems typically lack:
- Detects handovers languishing unaccepted for >24/48 hours
- Flags cases with no recorded commitment for 7+ days
- Identifies "ping-pong" cases bouncing between bureaus (unclear jurisdiction)
- Detects status oscillation patterns (A→B→A→B flip-flopping)
- Surfaces unassigned chasers on active waiting entries

### 📝 5. Deterministic Delay Explainer (No Hallucinations)

Unlike AI-generated explanations that may fabricate reasons:
- Generates human-readable status sentences based purely on database facts
- **Explicitly states "reason not recorded"** when no data supports an explanation
- Tone-coded for at-a-glance severity assessment
- Covers all lifecycle stages including handover transit

### 🧵 6. Issue Threads

When related complaints are confirmed, they're automatically woven into **Issue Threads**:
- Combined investigative briefs auto-generated from shared keywords and domain terms
- Graph-style view: member complaints as nodes, confirmed relations as edges
- Thread-level overview across institutions and bureaus

### 🔒 7. Confidentiality-Aware Redaction

Dynamic access-level computation ensures:
- Bureau officials only see full details of cases their bureau participates in
- Non-participating bureau views are automatically redacted to `SUMMARY` level
- `ACCESS_DENIED` audit events captured when unauthorized access is attempted

---

## 6. Creative & Unique Implementations

### 🎨 Custom NLP Pipeline (No Dependencies)

The text normalization pipeline is entirely handcrafted:

1. **Unicode NFKC Normalization** — handles accented characters, full-width forms
2. **Custom Suffix Stemmer** — handles `ies→y`, `sses→ss`, `ing`, `ment`, `ly`, `ed`, `es`, `s` with minimum length guards
3. **Domain-Aware Stopwords** — generic stopwords + education-specific terms (`institute`, `college`, `university`, `complaint`, `student`)
4. **Technical Education Domain Vocabulary** — 34 curated terms: `fee`, `refund`, `hostel`, `ragging`, `capitation`, `affiliation`, `accreditation`, etc.
5. **Sublinear TF-IDF** — `1 + ln(tf)` weighting to dampen high-frequency term dominance

### 🏗️ Composite Scoring Formula

```
Total Score = Category Match (25 pts)
            + Text Similarity (40 pts)     ← 0.5 × Jaccard + 0.5 × Cosine(sublinear TF)
            + Domain Terms (15 pts)        ← 15 × min(1, shared_count / 3)
            + Incident Reference (10 pts)  ← Exact alphanumeric match (floor 40)
            + Date Proximity (10 pts)      ← Decay: ≤7d→10, ≤30d→6, ≤90d→3, >90d→0
```

### 🔐 CSV Formula Injection Defense

All exported CSV cells starting with `=`, `+`, `-`, or `@` are prefixed with a single quote (`'`) — a creative defense against spreadsheet command injection attacks when reports are opened in Excel or Google Sheets.

### ⚡ Debounced Live Relation Preview

While officials type a new complaint, the system runs the scoring algorithm against all existing complaints for the same institution **in real-time** with debounced API calls, showing match candidates before the complaint is even submitted.

### 🔄 Optimistic Locking

Every complaint carries a `version` integer. On any update, the client must send the current version; the server increments it atomically. If versions don't match, a `409 Conflict` is returned — preventing lost updates in multi-user environments.

### 📌 Canonical Ordering for Relations

To prevent `(A, B)` and `(B, A)` from creating duplicate relation records, a canonical ordering constraint ensures `complaint_a_id < complaint_b_id` is always enforced at the database level.

### 🛡️ PermissionGate Component

A lightweight React component that wraps UI elements with role-based visibility checks:

```tsx
<PermissionGate allowedRoles={["SUPERVISOR", "SYSTEM_ADMIN"]}>
  <AdminPanel />
</PermissionGate>
```

- Renders `children` only if the authenticated user's role is in `allowedRoles`
- Optionally renders a `fallback` component for unauthorized users
- Uses the `useAuth()` hook for zero-config integration with the auth context

### 🕐 Idempotent Overdue Scanning

The APScheduler background job uses dedup keys (`OVERDUE:<complaint_id>:<date>`) to ensure the same overdue notification is never dispatched twice per day — even if the job runs multiple times.

---

## 7. Database Design & Data Model

### Entity-Relationship Overview

```
BUREAUS ──┐                                    ┌── STATUS_HISTORY
           ├──→ USERS ──→ COMPLAINTS ←── INSTITUTIONS
           │         │          │
           │         │          ├──→ CASE_ASSIGNMENTS
           │         │          ├──→ COMPLAINT_NOTES
           │         │          ├──→ COMPLAINT_RELATIONS ──→ ISSUE_THREADS
           │         │          ├──→ NOTIFICATIONS
           │         │          ├──→ WAITING_ON_ENTRIES
           │         │          └──→ HANDOVERS
           │         │
           │         └──→ AUDIT_LOGS
           │
           └──→ CASE_ASSIGNMENTS
```

### Key Tables (13 Total)

| Table | Purpose | Key Fields |
|---|---|---|
| `bureaus` | RB, PGRC, HQ organizational units | `code` (UK), `name`, `is_active` |
| `users` | AICTE officials | `email` (UK), `role`, `bureau_id` (FK), `is_active` |
| `institutions` | AICTE-approved colleges/universities | `aicte_id` (UK), `name`, `state`, `city`, `category` |
| `complaints` | Core grievance records | `reference_number` (UK), `status`, `priority`, `category`, `version`, `handover_status` |
| `case_assignments` | Bureau↔Complaint delegation | `role_in_case` (PRIMARY/PARTICIPATING), `is_active` |
| `status_history` | Lifecycle audit trail | `from_status`, `to_status`, `reason`, `changed_at` |
| `complaint_notes` | Investigation case notes | `content`, `note_type`, `author_id` |
| `complaint_relations` | Scored pairwise matches | `score`, `confidence`, `status`, `explanation` (JSONB), `thread_id` |
| `issue_threads` | Grouped related complaints | `title`, `brief`, `status` |
| `waiting_on_entries` | Delay accountability ledger | `waiting_on_type`, `waiting_on_party`, `chaser_user_id`, `is_resolved` |
| `handovers` | Inter-bureau transfer contracts | `from_bureau_id`, `to_bureau_id`, `status`, `context_summary` |
| `notifications` | User notification inbox | `type`, `title`, `message`, `is_read`, `deep_link` |
| `audit_logs` | Immutable system audit | `action`, `entity_type`, `before_data` (JSONB), `after_data` (JSONB) |

### PostgreSQL-Specific Features Used

- **UUID primary keys** (`UUID(as_uuid=True)`) for all entities
- **JSONB columns** for audit log snapshots and algorithm explanation payloads
- **Composite indexes** for query optimization
- **Check constraints** for canonical ordering of relations
- **Unique constraints** for reference numbers and dedup keys

---

## 8. Algorithm Deep-Dive: Duplicate Detection v1.0

### Pipeline Flow

```
New Complaint Submitted / Preview Request
        │
        ▼
Retrieve Historical Candidates (same institution_id only)
        │
        ▼
Text Preprocessing & Normalization
  ├── Unicode NFKC → lowercase
  ├── Remove non-alphanumeric → tokenize
  ├── Drop tokens < 3 chars, pure numbers, stopwords
  ├── Suffix stemming
  └── Build: token_list, token_set, token_counter
        │
        ├── Component 1: Category Match (25 pts)
        ├── Component 2: Text Similarity (40 pts)
        │     └── 0.5 × Jaccard + 0.5 × Cosine(sublinear TF)
        ├── Component 3: Domain Terms (15 pts)
        │     └── 15 × min(1, |shared_domain_terms| / 3)
        ├── Component 4: Incident Reference (10 pts)
        │     └── Floor at 40 if match found
        └── Component 5: Date Proximity (10 pts)
              └── ≤7d→10, ≤30d→6, ≤90d→3, >90d→0
        │
        ▼
Sum & Clamp [0, 100]
        │
        ▼
Score ≥ 40 AND (category_match OR text≥12 OR ref_match)?
  ├── No  → Discard
  └── Yes → Generate Explanation Payload
              │
              ▼
        Persist as PENDING_REVIEW in Relations Queue
              │
              ▼
        Dispatch RELATED_SUGGESTED Notifications
```

### Suggestion Rules

A relation is **suggested** when:
1. `score ≥ 40`, **AND**
2. At least one of: category match, text similarity ≥12 points, or incident reference match

An incident reference exact match **always** yields a suggestion with score floored to 40.

### Confidence Levels

| Score Range | Confidence |
|---|---|
| ≥ 60 | **HIGH** |
| 40–59 | **MEDIUM** |

---

## 9. Security Architecture

| Layer | Mechanism | Details |
|---|---|---|
| **Password Hashing** | Argon2id (argon2-cffi) | Memory-hard, GPU-resistant, winner of the Password Hashing Competition |
| **Authentication** | JWT (HMAC-SHA256) | Configurable expiration via `ACCESS_TOKEN_EXPIRE_MINUTES` |
| **Authorization** | Centralized RBAC Matrix | 4 fixed roles, dynamically computed `allowed_actions` per complaint |
| **Confidentiality** | Access-Level Redaction | FULL vs SUMMARY based on bureau participation |
| **Audit** | Append-Only Logs | Before/after JSONB snapshots, actor tracking, IP logging |
| **Access Denial Logging** | `ACCESS_DENIED` Events | Every 403 generates an immutable audit record |
| **Account Lockout** | Failed Login Tracking | Lockout threshold at 5 consecutive failures |
| **CSV Export Safety** | Formula Injection Guard | `=`, `+`, `-`, `@` prefixed with `'` in all exported cells |
| **Concurrency** | Optimistic Locking | `version` field prevents lost updates |

---

## 10. Frontend Design & UX

### Design System

- **Custom Indian Enterprise Design Tokens**: `brand-900` deep navy, card surfaces, accessible focus rings
- **Tailwind CSS** with custom configuration extending color palette, typography, and spacing
- **Responsive layout** with AppShell (TopBar + Collapsible Sidebar + Content Area)

### Interactive Features

- **Quick-Fill Login Buttons**: Pre-fill credentials for all 4 roles during demo/evaluation
- **Live Unread Notification Polling**: TopBar badge updates every 30 seconds
- **Dynamic Sidebar Badge Counters**: Pending relations queue count polled every 60 seconds
- **Debounced Relation Preview**: Real-time match suggestions in complaint creation form
- **DataTable Component**: Reusable table with pagination, column sorting, search, loading/empty states
- **Confirmation Modals**: For all destructive or irreversible actions
- **PermissionGate**: Declarative role-based rendering for UI elements

### Mandatory Prototype Disclosures

- `"Prototype - synthetic data only"` banner permanently embedded in:
  - Top navigation bar
  - Footer area
  - Login page

---

## 11. API Surface

### Endpoint Groups (8 Modules, 30+ Endpoints)

| Module | Endpoints | Description |
|---|---|---|
| `/auth` | 3 | Login, session info, password change |
| `/complaints` | 9 | Full CRUD, status transitions, notes, escalation, transfers |
| `/relations` | 6 | Preview, queue, confirm, dismiss, revert |
| `/institutions` | 4 | Directory, detail, coordination, timeline |
| `/analytics` | 6 | Summary KPIs, distributions, trends, top institutions |
| `/reports` | 4 | JSON preview + CSV export (overdue & master) |
| `/notifications` | 3 | List, mark read, mark all read |
| `/admin` | 7 | Users CRUD, audit logs, system health, overdue scan trigger |

### API Design Principles

- **RESTful** resource-oriented URLs
- **JSON envelope** error responses with structured error codes
- **Bearer JWT** authentication on all authenticated endpoints
- **Pagination** via `page` and `page_size` query parameters
- **Filtering** via query parameters (status, category, bureau_code, etc.)
- **Optimistic locking** via `version` field on mutation requests

---

## 12. Testing & Quality Assurance

### Backend Testing

| Suite | Count | Time | Coverage |
|---|---|---|---|
| Unit Tests (pytest) | 12 passed | 0.55s | Core services, algorithm, permissions |
| E2E Scenario (Section 19) | Integrated | Requires PostgreSQL | Full acceptance scenario |

### Frontend Testing

| Suite | Count | Time | Coverage |
|---|---|---|---|
| Vitest Component Tests | 10 passed | 1.52s | Badges, DataTable, MatchExplanationCard |
| TypeScript Strict Typecheck | — | — | 0 errors |
| oxlint Linting | — | — | 0 errors |
| Production Build | — | 4.42s | Build succeeded |

### Test Infrastructure

- **MSW (Mock Service Worker)** for API mocking in frontend component tests
- **React Testing Library** for user-centric component testing
- **Deterministic seed fixture** (`random.seed(20260101)`) for reproducible test data

---

## 13. Deployment & DevOps

### Local Development

```powershell
# Database
docker compose up -d db

# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
python -m app.cli seed
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### Docker Compose Services

```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: aicte
      POSTGRES_PASSWORD: aicte_dev_pw
      POSTGRES_DB: aicte_dashboard
    ports:
      - "5432:5432"
```

### Environment Configuration

- `.env.example` template with all configurable parameters
- Database URL, JWT secret, token expiration, debug flags
- Separate test database configuration

### Demo Credentials

| Role | Email | Password |
|---|---|---|
| **Supervisor** | `supervisor@aicte.gov.in` | `Supervisor@123` |
| **RB Official** | `rb.official@aicte.gov.in` | `Official@123` |
| **PGRC Official** | `pgrc.official@aicte.gov.in` | `Official@123` |
| **System Admin** | `admin@aicte.gov.in` | `Admin@123` |

---

> **Built for Smart India Hackathon** — Designed to demonstrate how technology can transform government grievance redressal from siloed, opaque processes into a transparent, accountable, and intelligent system.

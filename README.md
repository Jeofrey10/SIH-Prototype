# AICTE Integrated Institution Complaint Monitoring and Status Dashboard

[![Backend Tests](https://img.shields.io/badge/backend%20tests-12%20passed-brightgreen)](#)
[![Frontend Tests](https://img.shields.io/badge/frontend%20tests-10%20passed-brightgreen)](#)
[![TypeScript](https://img.shields.io/badge/TypeScript-strict-blue)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-teal)](#)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue)](#)

A centralized, real-time multi-bureau grievance monitoring, cross-bureau coordination, and duplicate detection platform for the All India Council for Technical Education (AICTE).

> **Prototype Notice**: All data displayed in this application is strictly synthetic and generated deterministically for demonstration and evaluation purposes. A visible banner `"Prototype - synthetic data only"` is permanently embedded in the application.

---

## 🌟 Key Features

1. **Multi-Bureau Grievance Management**:
   - Primary vs Participating bureau case delegation between Regulation Bureau (`RB`), Grievance Redressal Cell (`PGRC`), and Headquarters (`HQ`).
   - Cross-bureau jurisdictional transfer and collaboration tracking.
2. **Duplicate & Related Grievance Detection (Algorithm v1.0)**:
   - Pure, deterministic scoring function (0–100) combining category match, sublinear TF-IDF cosine similarity, suffix-stemming, domain vocabulary, and incident reference extraction.
   - Explainable breakdown card with point-by-point rule assessment.
   - Human review pipeline: `CONFIRM` (with auto-participation flag), `DISMISS`, and Supervisor `REVERT`.
   - Debounced live candidate preview panel in complaint registration form.
3. **Strict Role-Based Access Control (RBAC)**:
   - 4 official roles: `SYSTEM_ADMIN`, `SUPERVISOR`, `RB_OFFICIAL`, `PGRC_OFFICIAL`.
   - Dynamically computed `allowed_actions` per complaint.
   - Automatic redaction to `access_level="SUMMARY"` when non-participating bureaus view a case.
4. **Append-Only Tamper-Evident Audit Trail**:
   - Complete tracking of logins, registrations, status updates, relation decisions, and access denials (`ACCESS_DENIED`).
5. **Real-Time Analytics & Statutory CSV Export**:
   - Zero-filled status distribution across all 7 lifecycle stages.
   - Workload by bureau, aging buckets (<7d to >30d), and 30-day intake trend.
   - Formula-injection-sanitized CSV export.

---

## 🚀 Quickstart Guide

### Prerequisites
- **Python**: 3.11+ (Tested on Python 3.13.2)
- **Node.js**: 18+ (Tested on Node.js v22.14.0, npm 10.9.2)
- **Database**: PostgreSQL 15+ (via Docker or local service)

---

### Step 1: Database Setup

#### Option A: Using Docker Compose (Recommended)
```powershell
docker compose up -d db
```

#### Option B: Local PostgreSQL (Fallback without Docker)
If Docker is unavailable, install PostgreSQL locally and initialize the database:
```sql
CREATE USER aicte WITH PASSWORD 'aicte_dev_pw';
CREATE DATABASE aicte_dashboard OWNER aicte;
CREATE DATABASE aicte_dashboard_test OWNER aicte;
GRANT ALL PRIVILEGES ON DATABASE aicte_dashboard TO aicte;
GRANT ALL PRIVILEGES ON DATABASE aicte_dashboard_test TO aicte;
```

---

### Step 2: Backend Setup & Seed

```powershell
cd backend

# 1. Create and activate virtual environment (optional)
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 3. Apply database migrations
alembic upgrade head

# 4. Populate deterministic synthetic dataset
python -m app.cli seed

# 5. Start the backend API server
uvicorn app.main:app --reload --port 8000
```

The API will be live at `http://localhost:8000/api/v1` with documentation at `http://localhost:8000/docs`.

---

### Step 3: Frontend Setup & Dev Server

```powershell
cd frontend

# 1. Install dependencies
npm install

# 2. Start Vite development server
npm run dev
```

Open your browser at `http://localhost:5173`.

---

## 👥 Demo Quick-Fill Credentials

For rapid evaluation, the login page features quick-fill buttons for all 4 roles:

| Role | Email | Password | Scope & Permissions |
|---|---|---|---|
| **Supervisor** | `supervisor@aicte.gov.in` | `Supervisor@123` | Full cross-bureau oversight, closure, transfers, revert |
| **RB Official** | `rb.official@aicte.gov.in` | `Official@123` | Regulation Bureau case worker |
| **PGRC Official**| `pgrc.official@aicte.gov.in`| `Official@123` | Grievance Redressal Cell case worker |
| **System Admin** | `admin@aicte.gov.in` | `Admin@123` | User provisioning, audit trail explorer, system ops |

---

## 🧪 Running Automated Tests

### Backend Unit Tests
```powershell
cd backend
python -m pytest tests/unit/
```
*Current Result: 12 passed in 0.55s.*

### Backend Acceptance Scenario (Section 19)
```powershell
cd backend
python -m pytest tests/
```
*Requires active PostgreSQL on port 5432.*

### Frontend Tests, Typecheck & Linting
```powershell
cd frontend

# Run Vitest component tests
npm run test

# Typecheck TypeScript (strict mode)
npm run typecheck

# Lint with oxlint
npm run lint

# Production build
npm run build
```
*Current Result: 10 tests passed in 1.52s, 0 lint errors, build succeeded in 4.42s.*

---

## 📚 Project Documentation

- [docs/DECISIONS.md](file:///c:/project%20files/SIH%20Prototype/docs/DECISIONS.md) - Architecture and engineering decisions
- [docs/ARCHITECTURE.md](file:///c:/project%20files/SIH%20Prototype/docs/ARCHITECTURE.md) - System diagrams, ER model, state machine, and algorithm pipeline
- [docs/API.md](file:///c:/project%20files/SIH%20Prototype/docs/API.md) - REST API specification
- [docs/TROUBLESHOOTING.md](file:///c:/project%20files/SIH%20Prototype/docs/TROUBLESHOOTING.md) - Solutions for port conflicts, Docker, and connection errors
- [docs/VERIFICATION_REPORT.md](file:///c:/project%20files/SIH%20Prototype/docs/VERIFICATION_REPORT.md) - Verified test and build outputs

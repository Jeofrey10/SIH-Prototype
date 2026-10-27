# System Architecture & Design (ARCHITECTURE.md)

This document provides architectural diagrams, domain models, lifecycle states, and algorithmic workflows for the **AICTE Integrated Institution Complaint Monitoring and Status Dashboard**.

---

## 1. High-Level System Architecture

```mermaid
graph TD
    subgraph Client ["Frontend (React 18 + TypeScript + Vite)"]
        UI[UI Components & AppShell]
        ReactQuery[TanStack Query Caching & Polling]
        AuthCtx[Auth Context & Token Storage]
        Router[React Router v6 & RBAC Guards]
    end

    subgraph Server ["Backend (FastAPI Modular Monolith)"]
        API[FastAPI Routers /api/v1]
        Deps[Dependency Injection & RBAC Guard]
        Services[Domain Services Layer]
        Algorithm[Algorithm v1.0 Scorer & Normalizer]
        Jobs[APScheduler In-Process Background Jobs]
    end

    subgraph Data ["Data & Storage Layer (PostgreSQL 15+)"]
        PG[(PostgreSQL Database)]
        Audit[(Append-Only Audit Logs)]
        Triggers[Immutability Triggers]
    end

    UI --> Router
    Router --> ReactQuery
    ReactQuery --> AuthCtx
    AuthCtx -->|Bearer JWT| API

    API --> Deps
    Deps --> Services
    Services --> Algorithm
    Services --> PG
    Services --> Audit
    Jobs --> Services
    PG --- Triggers
```

---

## 2. Entity-Relationship (ER) Data Model

```mermaid
erDiagram
    BUREAUS ||--o{ USERS : "employs"
    BUREAUS ||--o{ CASE_ASSIGNMENTS : "assigned_to"
    USERS ||--o{ COMPLAINTS : "creates"
    USERS ||--o{ COMPLAINT_NOTES : "writes"
    USERS ||--o{ AUDIT_LOGS : "acts"
    INSTITUTIONS ||--o{ COMPLAINTS : "receives"
    COMPLAINTS ||--o{ CASE_ASSIGNMENTS : "delegated"
    COMPLAINTS ||--o{ STATUS_HISTORY : "tracks"
    COMPLAINTS ||--o{ COMPLAINT_NOTES : "contains"
    COMPLAINTS ||--o{ NOTIFICATIONS : "triggers"
    COMPLAINTS ||--o{ COMPLAINT_RELATIONS : "complaint_a"
    COMPLAINTS ||--o{ COMPLAINT_RELATIONS : "complaint_b"

    BUREAUS {
        uuid id PK
        string code UK
        string name
        boolean is_active
    }

    INSTITUTIONS {
        uuid id PK
        string aicte_id UK
        string name
        string state
        string city
        string category
    }

    COMPLAINTS {
        uuid id PK
        string complaint_number UK
        uuid institution_id FK
        string status
        string priority
        string category
        string title
        text description
        date incident_date
        date target_resolution_date
        integer version
        boolean is_escalated
        boolean is_overdue
    }

    CASE_ASSIGNMENTS {
        uuid id PK
        uuid complaint_id FK
        string bureau_code FK
        uuid assigned_official_id FK
        string role_in_case
        string reason
    }

    COMPLAINT_RELATIONS {
        uuid id PK
        uuid complaint_a_id FK
        uuid complaint_b_id FK
        integer score
        string status
        string relation_type
        jsonb explanation
        uuid reviewed_by_id FK
        timestamp reviewed_at
    }

    AUDIT_LOGS {
        uuid id PK
        uuid actor_id FK
        string action
        string entity_type
        string entity_id
        jsonb before_data
        jsonb after_data
        string ip_address
        timestamp occurred_at
    }
```

---

## 3. Complaint Lifecycle State Transitions

```mermaid
stateDiagram-v2
    [*] --> SUBMITTED: Registration
    SUBMITTED --> UNDER_REVIEW: Review (Bureau Official / Supervisor)
    UNDER_REVIEW --> ASSIGNED: Assign Case Worker
    ASSIGNED --> IN_INVESTIGATION: Commence Investigation
    IN_INVESTIGATION --> PENDING_INSTITUTION_ACTION: Request Compliance / Evidence
    PENDING_INSTITUTION_ACTION --> IN_INVESTIGATION: Response Received
    IN_INVESTIGATION --> RESOLVED: Investigation Complete & Redressed
    RESOLVED --> CLOSED: Formal Closure (Supervisor Only)
    RESOLVED --> UNDER_REVIEW: Reopened (Disputed Resolution)
    CLOSED --> [*]
```

---

## 4. Cross-Bureau Coordination Workflow

```mermaid
sequenceDiagram
    autonumber
    actor RB as Bureau RB Official
    actor PGRC as Bureau PGRC Official
    actor Sup as AICTE Supervisor
    participant Backend as FastAPI Backend
    participant Alg as Algorithm v1.0
    participant DB as PostgreSQL DB

    RB->>Backend: Register Complaint (a) for Institution X
    Backend->>DB: Persist Complaint (a) with Primary Bureau = RB
    PGRC->>Backend: Register Complaint (b) for Institution X
    Backend->>Alg: Run Scorer on Complaint (b) vs Institution X Candidates
    Alg-->>Backend: Match Flagged (Score: 78 ≥ 35)
    Backend->>DB: Persist Relation (a, b) as PENDING_REVIEW
    Backend->>PGRC: Notify PGRC Official & RB Official of Suggested Relation

    PGRC->>Backend: Review Relation -> Confirm as RELATED_INCIDENT (auto_participate=True)
    Backend->>DB: Update Relation to CONFIRMED
    Backend->>DB: Add PGRC as Participating Bureau to Complaint (a)
    Backend->>DB: Add RB as Participating Bureau to Complaint (b)
    Backend->>DB: Write Audit Trail (RELATION_CONFIRMED, PARTICIPANT_ADDED)

    Note over RB,PGRC: Both Bureaus now have Full Visibility and Collaboration Access
    Sup->>Backend: View Institution X Coordination Dashboard
    Backend-->>Sup: Returns Unified Multi-Bureau Coordination Profile & Chronological Timeline
```

---

## 5. Duplicate Detection Algorithm v1.0 Pipeline

```mermaid
flowchart TD
    A[New Complaint Submitted / Preview Request] --> B[Retrieve Institution Historical Candidates]
    B --> C{Any Candidates for Institution?}
    C -- No --> D[Return 0 Relations]
    C -- Yes --> E[Text Preprocessing & Normalization]

    E --> F1[1. Category Match: 15 pts]
    E --> F2[2. Cosine Similarity on Sublinear TF: Up to 35 pts]
    E --> F3[3. Domain Keyword Overlap: Up to 25 pts]
    E --> F4[4. Incident Reference Extraction: Floor 40 pts]
    E --> F5[5. Incident Date Proximity Decay: Up to 15 pts]

    F1 & F2 & F3 & F4 & F5 --> G[Sum Components & Clamp 0-100]
    G --> H{Score ≥ 35?}
    H -- No --> I[Discard / Ignore]
    H -- Yes --> J[Generate Explanation Payload & Rule Points Breakdown]
    J --> K[Persist in PENDING_REVIEW Relations Queue]
    K --> L[Dispatch RELATED_SUGGESTED Notifications to Bureau Officials]
```

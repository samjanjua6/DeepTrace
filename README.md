# DeepTrace — Technical Documentation & Developer Guide

> **Explainable AI Document Forensics & Tampering Detection Platform**  
> Compliant with State Bank of Pakistan (SBP) Frameworks, Electronic Transactions Ordinance (ETO 2002), PECA 2016, and NIST SP 800-86.

---

## 📖 Table of Contents
1. [Executive Summary & System Architecture](#1-executive-summary--system-architecture)
2. [Database Layer (PostgreSQL 16 + Prisma ORM)](#2-database-layer-postgresql-16--prisma-orm)
3. [Modular Feature-First Application Structure](#3-modular-feature-first-application-structure)
4. [Security Audit & Vulnerability Remediation](#4-security-audit--vulnerability-remediation)
5. [Runtime Bug Fixes & Compatibility Solutions](#5-runtime-bug-fixes--compatibility-solutions)
6. [Developer Quickstart & Testing Guide](#6-developer-quickstart--testing-guide)
7. [Testing in Swagger UI](#7-testing-in-swagger-ui)

---

## 1. Executive Summary & System Architecture

DeepTrace is built to detect tampered, forged, and synthetic financial PDFs (bank statements, salary slips, utility bills, and tax certificates) for the Pakistani and global banking ecosystems.

The platform employs a **Tri-Pillar Architecture**:
1. **Deterministic Verification**: 100% rule-based checks (Lakh/Crore balance reconciliations, PK-IBAN MOD-97 check digits, FBR tax ratios, PDF incremental save history).
2. **Computer Vision Forensics**: Error Level Analysis (ELA at $Q=95$), copy-move forgery detection, font baseline displacement analysis, and glyph anomaly bounding boxes.
3. **Multi-Agent AI Swarm**: LangGraph-coordinated specialized LLM agents (Structural, Visual, Semantic PK, and Lead Investigator) operating under a **strict Zero-Hallucination Policy** bound to verified evidence manifests.

---

## 2. Database Layer (PostgreSQL 16 + Prisma ORM)

The database schema is defined in `prisma/schema.prisma` and enhanced with PostgreSQL-native extensions in `app/db/migrations/001_extensions.sql`.

### 2.1 Domain Overview (28 Models / 24 Core Tables)

| Domain | Tables | Purpose |
|---|---|---|
| **1. Identity & Multi-Tenancy** | `organizations`, `users`, `api_keys`, `user_sessions` | Tenancy boundaries, RBAC roles (`OWNER`, `ADMIN`, `ANALYST`, `VIEWER`, `API_SERVICE`), session management, and hashed API keys. |
| **2. Investigation Core** | `investigations`, `documents`, `document_metadata`, `document_pages` | Forensic cases (`DT-PK-YYYY-NNNNNN`), SHA-256 custody-locked files, deep PDF object trees, and per-page OCR text. |
| **3. Forensic Pipeline** | `pipeline_runs`, `pipeline_stages` | Tracks execution of the 8-stage pipeline, stage durations, inputs/outputs, and failure stacks. |
| **4. Evidence & Findings** | `evidence_items`, `bounding_boxes`, `evidence_artifacts` | Anomaly records, pixel/point overlay coordinates for UI highlighting, and visual proof files (ELA heatmaps, diffs). |
| **5. Risk Assessment** | `risk_assessments`, `risk_signals` | Bayesian evidence-fused risk scores (0–100), calibrated risk tiers (`LOW` to `CRITICAL`), and analyst overrides. |
| **6. Multi-Agent AI** | `agent_sessions`, `agent_messages` | LLM swarm turn history, tool invocations, token/cost metrics, and Langfuse trace observability. |
| **7. Audit & Compliance** | `audit_logs`, `custody_events`, `investigation_notes`, `tags`, `investigation_tags`, `webhook_endpoints`, `webhook_deliveries` | SBP-mandated append-only audit trail, ETO 2002 custody events, and HMAC-signed webhook event deliveries. |

### 2.2 Advanced Database Safeguards

* **PostgreSQL Extensions Installed**:
  * `pgcrypto`: Cryptographic hashing and UUID generation.
  * `pg_trgm`: Trigram indexing for fuzzy search on OCR text and file names.
  * `btree_gin`: GIN index acceleration for JSONB metadata lookups.
  * `unaccent`: Accent-insensitive text search.
* **Row-Level Security (RLS)**:
  * 19 PostgreSQL RLS policies enforce `organizationId` boundaries directly inside the database engine.
  * Every tenant query is scoped using session context: `SELECT set_config('app.current_org_id', '<org_id>', true)`.
* **Database-Level Immutability**:
  * Tables `audit_logs` and `custody_events` have PostgreSQL triggers (`trg_audit_logs_immutable`, `trg_custody_events_immutable`) that reject any `UPDATE` or `DELETE` with a `restrict_violation` exception.
* **Sequence-Based Case Numbers**:
  * Implemented `generate_case_number()` SQL function backed by `investigation_case_seq` producing readable case identifiers: `DT-PK-2026-000001`.
* **Hot-Path Partial Indexes**:
  * `idx_investigations_active`: Indexes only non-archived, non-closed cases.
  * `idx_api_keys_active`: Indexes only active API keys (`isActive = TRUE`).
  * `idx_evidence_critical_high`: Filters hot-path queries for high-severity findings.

---

## 3. Modular Feature-First Application Structure

The application is structured by **business feature (domain)** rather than technical layers. Every domain feature lives in `app/features/<feature>/` and is self-contained.

```
d:\zylo\DeepTrace\
├── docker-compose.yml              # Local PostgreSQL 16 + Redis 7 dev stack
├── .env.example                    # Configuration template
├── .env                            # Active environment configuration
├── prisma/
│   └── schema.prisma               # Prisma schema definition
│
├── app/
│   ├── main.py                     # FastAPI app factory, lifespan, router mounting
│   ├── config.py                   # Type-safe pydantic-settings configuration
│   ├── dependencies.py             # Global dependency injection (SettingsDep, DbDep)
│   ├── exceptions.py               # Global exception handlers (validation, DB, HTTP)
│   │
│   ├── db/                         # Database connection & migrations
│   │   ├── client.py               # Async Prisma client singleton & RLS context manager
│   │   ├── enums.py                # Python enum mirrors with domain logic
│   │   └── migrations/
│   │       └── 001_extensions.sql  # Database extensions, RLS, triggers, check constraints
│   │
│   ├── core/                       # Shared cross-cutting infrastructure (NO business logic)
│   │   ├── security.py             # Bcrypt hashing, JWT tokens, API key SHA-256 hashing
│   │   ├── storage.py              # S3/MinIO abstraction with presigned URLs
│   │   ├── cache.py                # Async Redis wrapper (get, set, delete)
│   │   ├── celery_app.py           # Celery application & queue routing
│   │   ├── pagination.py           # Standard pagination helpers (Page, Limit, Total)
│   │   └── case_number.py          # Case number sequence caller
│   │
│   └── features/                   # Self-contained feature modules
│       ├── auth/                   # Login, logout, /me, JWT issuance, session management
│       ├── organizations/          # Org settings, usage quotas, tier information
│       ├── api_keys/               # M2M key generation (shown once, stored as hash)
│       ├── investigations/         # Case CRUD, status state-machine, analyst assignment
│       ├── documents/              # File upload, SHA-256 custody locking, page rendering
│       ├── pipeline/               # 8-stage pipeline orchestration
│       │   └── tasks/              # 8 dedicated Celery tasks (custody, pdf, font, cv, ocr, math, fusion, report)
│       ├── evidence/               # Discovered findings manifest, bounding boxes, proof
│       ├── risk/                   # Bayesian fusion engine, risk score (0-100), analyst override
│       ├── agents/                 # Multi-agent swarm & interactive Q&A assistant
│       │   └── swarm/              # Base agent + 4 LangGraph forensic agents
│       ├── reports/                # Court-admissible PDF dossier generation
│       └── webhooks/               # Outbound event dispatch, HMAC-SHA256 signing, retry task
│
├── scripts/
│   └── seed_dev.py                 # Development database seeder
└── tests/
    ├── conftest.py                 # Async test client fixtures
    └── test_db_connection.py       # End-to-end database validation suite
```

### Feature Module Contract
Each module adheres to a standard separation of concerns:
* `router.py`: Handles HTTP routing, path parameters, request/response validation. Zero business logic.
* `service.py`: Contains all business logic, database queries, and third-party integrations.
* `schemas.py`: Pydantic v2 schemas with `AliasChoices` for seamless camelCase (Prisma) to snake_case (API) serialization.
* `dependencies.py`: Feature-scoped FastAPI `Depends()` factories.

---

## 4. Security Audit & Vulnerability Remediation

During development, a security audit was performed against the database and application integration. All 5 identified vulnerabilities were systematically remediated:

### 1. Multi-Tenant RLS Bypass via Superuser Connection (CRITICAL)
* **Problem**: The app originally connected using the `postgres` superuser. In PostgreSQL, superusers possess `rolbypassrls = true`, causing PostgreSQL to completely ignore all Row-Level Security policies. Any organization could query another organization's records.
* **Fix**:
  1. Created a dedicated least-privilege non-superuser role `deeptrace_app` with `NOSUPERUSER NOBYPASSRLS`.
  2. Granted only table-level DML (`SELECT, INSERT, UPDATE, DELETE`) and sequence usage on `deeptrace_db`.
  3. Updated `DATABASE_URL` in `.env` to connect via `deeptrace_app`.
  4. Verified with an empirical test: Cross-tenant access is blocked by the PostgreSQL engine (`PostgresError: new row violates row-level security policy`).

### 2. SQL Injection in `app/db/client.py:set_org_context()` (HIGH)
* **Problem**: Session tenant variable was set via string interpolation (`f"SET LOCAL app.current_org_id = '{org_id}'"`), allowing SQL injection.
* **Fix**: Added strict regex validation (`^[a-zA-Z0-9_\-]+$`) and switched to parameterized PostgreSQL configuration execution:
  ```python
  await tx.execute_raw("SELECT set_config('app.current_org_id', $1, true);", org_id)
  ```

### 3. Weak Superuser Password (`12345`) (HIGH)
* **Problem**: The default administrative `postgres` user was configured with the dictionary password `12345`.
* **Fix**: Rotated the `postgres` password to a 32-character high-entropy secret (`KanY*J5BTfYFJ4wtk&wkpdJqzx*SpGkE`). Verified that `12345` is rejected.

### 4. Missing Connection & DDL Audit Logging (COMPLIANCE)
* **Problem**: `log_connections`, `log_disconnections`, and `log_statement` were disabled, non-compliant with SBP BPRD and PECA 2016 audit requirements.
* **Fix**: Applied settings in PostgreSQL:
  ```sql
  ALTER SYSTEM SET log_connections = 'on';
  ALTER SYSTEM SET log_disconnections = 'on';
  ALTER SYSTEM SET log_statement = 'ddl';
  ALTER SYSTEM SET log_min_duration_statement = '1000';
  ```

### 5. Network Interface Exposure (MEDIUM)
* **Problem**: PostgreSQL was set to `listen_addresses = '*'`.
* **Fix**: Set `ALTER SYSTEM SET listen_addresses = 'localhost';` to bind database traffic strictly to the internal loopback interface.

---

## 5. Runtime Bug Fixes & Compatibility Solutions

1. **Passlib / Bcrypt 5.0 Incompatibility**:
   * *Issue*: `passlib 1.7.4` crashes when used with `bcrypt 4.1+` due to an obsolete `__about__.__version__` check.
   * *Solution*: Switched `app/core/security.py` to use the `bcrypt` library directly (`bcrypt.hashpw` and `bcrypt.checkpw`) with automatic 72-byte truncation.
2. **CORS_ORIGINS Parsing in Pydantic-Settings**:
   * *Issue*: Pydantic-settings tried to parse comma-separated environment strings as JSON, failing during startup.
   * *Solution*: Added an `@field_validator(mode="after")` to `app/config.py` allowing both comma-separated strings and native lists.
3. **Prisma Python CamelCase Model Mapping**:
   * *Issue*: Prisma Client Python exposes model properties in camelCase (`user.passwordHash`, `user.organizationId`). Calling snake_case attributes caused runtime `AttributeError` on endpoints.
   * *Solution*: Updated all auth and investigation services to use camelCase model attributes and configured Pydantic schemas with `AliasChoices` for clean API outputs.
4. **Starlette Deprecation Warning & Error Handling**:
   * *Issue*: `HTTP_422_UNPROCESSABLE_ENTITY` triggered a deprecation warning in Starlette, and generic `Exception` handler swallowed `HTTPException`.
   * *Solution*: Updated `app/exceptions.py` to use `HTTP_422_UNPROCESSABLE_CONTENT` and added an explicit `HTTPException` handler.
5. **Updated-At Trigger on Tables without `updatedAt`**:
   * *Issue*: Database trigger `set_updated_at()` attempted to set `NEW."updatedAt"` on `api_keys`, which has no `updatedAt` column.
   * *Solution*: Removed `api_keys` from the trigger array in `001_extensions.sql`.

---

## 6. Developer Quickstart & Testing Guide

### Prerequisites
* Python 3.12+
* PostgreSQL 14+ running on port `5433` (configured via `.env`)

### Installation & Local Setup

1. **Configure Environment**:
   Verify `.env` has the correct settings:
   ```ini
   POSTGRES_USER=deeptrace_app
   POSTGRES_PASSWORD=LUlD3iS7THGyXHXOOUhmUw6fsNUiXjKY
   POSTGRES_DB=deeptrace_db
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5433

   DATABASE_URL="postgresql://deeptrace_app:LUlD3iS7THGyXHXOOUhmUw6fsNUiXjKY@localhost:5433/deeptrace_db?schema=public"
   ```

2. **Generate Prisma Client**:
   ```bash
   prisma generate --schema prisma/schema.prisma
   ```

3. **Seed Development Data**:
   Creates demo organization, admin, analyst, and a sample investigation:
   ```bash
   python scripts/seed_dev.py
   ```

4. **Run the Database Test Suite**:
   Verifies RLS, sequence generation, and immutability triggers:
   ```bash
   python tests/test_db_connection.py
   ```

---

## 7. Testing in Swagger UI

### Step 1: Start the Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

### Step 2: Open Interactive Documentation
Navigate to: **[http://localhost:8000/docs](http://localhost:8000/docs)**

### Step 3: Test Execution Workflow
1. **Authenticate (`POST /api/v1/auth/login`)**:
   * Body:
     ```json
     {
       "email": "analyst@meezan.pk",
       "password": "Analyst@12345"
     }
     ```
   * Execute and copy the `access_token` from the response.
2. **Authorize Swagger UI**:
   * Click the **Authorize 🔓** button at the top right of the Swagger UI page.
   * Paste the token into the **Value** input field and click **Authorize**.
3. **Verify Identity (`GET /api/v1/auth/me`)**:
   * Click **Try it out** ➔ **Execute**. Returns your user profile and organization ID.
4. **View Organization Details (`GET /api/v1/org`)**:
   * Click **Execute**. Returns the tenant profile (`Meezan Bank Ltd`).
5. **View Quota Usage (`GET /api/v1/org/usage`)**:
   * Click **Execute**. Returns document quota limits and remaining usage.
6. **List Investigations (`GET /api/v1/investigations`)**:
   * Click **Execute**. Returns cases belonging strictly to your organization.
7. **Create a Case (`POST /api/v1/investigations`)**:
   * Body:
     ```json
     {
       "title": "Habib Bank Tampered Salary Slip Audit",
       "description": "Cross-verification of monthly salary against FBR tax challans.",
       "priority": 2,
       "client_reference": "REF-HBL-2026-09"
     }
     ```
   * Execute. Returns `201 Created` with sequence-generated case number `DT-PK-2026-00000X`.
8. **Manage API Keys (`POST /api/v1/api-keys`, `GET /api/v1/api-keys`, `DELETE /api/v1/api-keys/{id}`)**:
   * Create, view, and revoke machine-to-machine tokens.

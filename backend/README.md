# Converge AI — Backend Foundation (Phase 1, WS-2 & WS-3)

This directory contains the production-conscious FastAPI backend and PostgreSQL migration foundation for **Converge AI — Conference Agent Network**.

---

## 1. Prerequisites

- Python 3.12+ (tested on Python 3.12.3 in Ubuntu 24.04 / WSL 2)
- `python3-venv` package installed
- PostgreSQL 16+ (tested on PostgreSQL 16.15 / 17.11 client)

---

## 2. Local Database Provisioning (Two-Role Model - GAP-02)

Before running migrations or the application with database connectivity, execute the administrative provisioning script as a PostgreSQL superuser:

```bash
# Execute provisioning script to create roles and databases:
# - converge_ai_owner: Migration/DDL role
# - converge_ai_app: Runtime application role (DML only: SELECT, INSERT, UPDATE, DELETE)
# - converge_ai_db: Main application database
# - converge_ai_test: Isolated test database
sudo -u postgres psql -f backend/scripts/provision_db.sql
```

---

## 3. Local Environment Setup

From the repository root (`/home/sanjana/converge-ai`):

### 3.1 Activate Dedicated Virtual Environment
```bash
source backend/.venv/bin/activate
```

### 3.2 Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 3.3 Configure Environment Variables
Copy `.env.example` to `.env` and configure:
```env
# Application Settings
ENVIRONMENT=development
PORT=8030
API_V1_PREFIX=/converge-api/v1

# Runtime Database URL (converge_ai_app)
DATABASE_URL=postgresql+asyncpg://converge_ai_app:local_app_secret@127.0.0.1:5432/converge_ai_db

# Migration Database URL (converge_ai_owner)
MIGRATION_DATABASE_URL=postgresql+psycopg2://converge_ai_owner:local_owner_secret@127.0.0.1:5432/converge_ai_db

# Isolated Test Database URL
TEST_DATABASE_URL=postgresql+asyncpg://converge_ai_app:local_app_secret@127.0.0.1:5432/converge_ai_test
```

---

## 4. Running Migrations

Run schema migrations as the `converge_ai_owner` role:

```bash
cd backend
source .venv/bin/activate

# Upgrade to latest migration (establishes core, agenda, a2a, matching schemas)
alembic upgrade head

# Downgrade (safe teardown with RESTRICT)
alembic downgrade -1
```

---

## 5. Running the Application

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8030 --reload
```

### Verify Endpoints
- **Process Liveness:** `curl -fsS http://127.0.0.1:8030/converge-api/v1/health`
- **Database Readiness:** `curl -fsS http://127.0.0.1:8030/converge-api/v1/health/ready`
- **Application Version:** `curl -fsS http://127.0.0.1:8030/converge-api/v1/version`
- **OpenAPI Documentation:** `http://127.0.0.1:8030/converge-api/v1/docs`

---

## 6. Running Automated Tests

```bash
cd backend
source .venv/bin/activate
pytest
```
*Executes all 25 unit, contract, database lifecycle, and Alembic migration tests.*

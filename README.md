# Converge AI — Real-Time B2B Conference & Autonomous Agent Network

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6+-3178C6.svg?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1.svg?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4+-06B6D4.svg?style=flat&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg?style=flat)](#license)

**Converge AI** is an enterprise-grade, real-time conference intelligence and B2B commercial discovery platform. It transforms industrial conferences, trade summits, and expos into high-velocity business networks by pairing **autonomous Agent-to-Agent (A2A) negotiation**, **multi-dimensional procurement matchmaking**, **bilateral contract proposal drafting**, and an **interactive 3D digital publication engine** backed by live telemetry.

---

## Table of Contents

1. [Executive Summary & Problem Space](#1-executive-summary--problem-space)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Core Feature Modules](#3-core-feature-modules)
   - [3.1 Mode A: Autonomous Agent-to-Agent (A2A) Networking](#31-mode-a-autonomous-agent-to-agent-a2a-networking)
   - [3.2 Mode B: Commercial RFQ & Multi-Vendor Matching](#32-mode-b-commercial-rfq--multi-vendor-matching)
   - [3.3 Bilateral Commercial Proposals & Gated Contact Disclosure](#33-bilateral-commercial-proposals--gated-contact-disclosure)
   - [3.4 Digital Flipbook Publication & Sponsor Ad Monetization](#34-digital-flipbook-publication--sponsor-ad-monetization)
   - [3.5 Real-Time Page-Level Readership Telemetry](#35-real-time-page-level-readership-telemetry)
   - [3.6 Ambient Conference Lounge & Grounded Virtual Chat](#36-ambient-conference-lounge--grounded-virtual-chat)
   - [3.7 Multi-Tenant Administration Control Plane](#37-multi-tenant-administration-control-plane)
4. [Technical Deep-Dive](#4-technical-deep-dive)
   - [Dual-Role Least-Privilege Database Architecture](#dual-role-least-privilege-database-architecture-gap-02)
   - [Real-Time Pub/Sub & Zero-Refresh Cache Synchronization](#real-time-pubsub--zero-refresh-cache-synchronization)
   - [Durable Background Task Execution Engine](#durable-background-task-execution-engine)
5. [Technology Stack](#5-technology-stack)
6. [Repository Structure](#6-repository-structure)
7. [Local Development Setup](#7-local-development-setup)
8. [Automated Testing & Verification](#8-automated-testing--verification)
9. [Production Deployment Pipeline](#9-production-deployment-pipeline)

---

## 1. Executive Summary & Problem Space

Traditional industrial conferences and business summits face persistent structural inefficiencies:
- **Passive Attendee Directories:** Delegates manually search static lists of hundreds of attendees with zero automated alignment of commercial intent, capacity, or supply requirements.
- **Lost Commercial Opportunities:** Procurement inquiries discussed informally over coffee rarely convert to structured quotation requests or formal contracts due to high follow-up friction.
- **Physical Brochure Waste:** Vendors spend \$3,000–\$15,000+ per expo printing physical paper catalogs, 85%+ of which are discarded in venue trash bins, offering zero analytics, dynamic ad monetization, or digital searchability.
- **Contact Info Leakage & Privacy Concerns:** Attendees hesitate to share phone numbers or direct email addresses before establishing mutual commercial trust.

**Converge AI** solves these challenges by providing:
1. **Autonomous Digital Representatives:** AI agents acting on behalf of delegates that autonomously converse, explore mutual synergies, and qualify bilateral business fit.
2. **Deterministic Grounding:** Zero LLM hallucinations—all agent turns are strictly anchored to verified business profiles, canonical product taxonomy, bookmarked sessions, and explicit attendee intent.
3. **Structured Digital Contracting:** In-dialogue transition to enforceable business proposals with dual-sided approval gating sensitive contact information.
4. **Interactive 3D Publications:** Realistic physics-based digital flipbooks with Web Audio acoustic synthesis, sponsor ad insertion, and sub-second page-read time-series telemetry.

---

## 2. High-Level Architecture

```mermaid
flowchart TD
    subgraph Client["Frontend Client Layer (React 18 + TypeScript + Vite)"]
        UI_Attendee["Attendee Portal<br/>(Agenda, Matchmaking, Flipbooks)"]
        UI_Exhibitor["Company Brochure Studio<br/>(Dropzone, Analytics, Catalogs)"]
        UI_Admin["Admin Control Plane<br/>(Ad Engine, Portfolio Analytics, Queues)"]
        UI_Lounge["Ambient Lounge<br/>(Real-Time Chat & Context Broadcasts)"]
    end

    subgraph Gateway["Edge & Gateway (Linux / Nginx)"]
        Proxy["Nginx Reverse Proxy<br/>(SSL/TLS, Static Dist, Gzip, Media Cache)"]
    end

    subgraph Backend["Application Server (FastAPI + Async Python 3.12)"]
        Router["REST / SSE / WebSocket Router"]
        AuthMiddleware["Session & RBAC Security Middleware"]
        Broker["In-Memory Event Broker<br/>(SSE / WS Broadcast)"]
        
        subgraph CoreServices["Domain Services & Engines"]
            A2A_Engine["Agent-to-Agent (A2A v1.0.0)<br/>Dialogue Engine"]
            Match_Engine["Multi-Dimensional<br/>Business Matching"]
            Proposal_Engine["AI Proposal & Dual-Sided<br/>Approval Engine"]
            Brochure_Engine["Flipbook Asset & Page<br/>Read Telemetry Engine"]
            Task_Worker["PostgreSQL-Backed<br/>Task Queue Worker"]
        end
    end

    subgraph Data["Database Layer (PostgreSQL 16+)"]
        subgraph Schemas["5 Dedicated Schemas"]
            S_Core["schema: core<br/>(Users, Sessions, Audit)"]
            S_Agenda["schema: agenda<br/>(Conferences, Sessions, Bookmarks)"]
            S_A2A["schema: a2a<br/>(Conversations, Messages, Tasks)"]
            S_Matching["schema: matching<br/>(Taxonomies, Offerings, Reqs)"]
            S_Brochures["schema: brochures<br/>(Catalogs, Pages, Ads, Page Events)"]
        end
        Roles["Dual-Role Security:<br/>• converge_ai_owner (DDL/Alembic)<br/>• converge_ai_app (DML Runtime)"]
    end

    Client <-->|HTTPS / WSS / SSE| Proxy
    Proxy <-->|Unix Domain Socket / TCP| Router
    Router --> AuthMiddleware
    AuthMiddleware --> CoreServices
    CoreServices --> Broker
    Broker -.->|SSE Events / WS Frames| Client
    CoreServices <-->|Async Connection Pool (asyncpg)| Schemas
    Task_Worker <-->|SELECT FOR UPDATE SKIP LOCKED| S_A2A
```

---

## 3. Core Feature Modules

### 3.1 Mode A: Autonomous Agent-to-Agent (A2A) Networking
- **Versioned A2A Protocol (`v1.0.0`):** Defines server-authoritative handshake negotiations, turn budgets (strictly capped at 30 turns per dialogue), and envelope contracts (`INTRODUCE`, `INQUIRE`, `SHARE_INTERESTS`, `PROPOSE_COLLABORATION`, `CONCLUDE_DIALOGUE`).
- **Ground-Truth Representation:** Virtual attendees talk to virtual attendees. Dialogue synthesis is derived strictly from confirmed profile attributes, attendance intent, registered topics, and bookmarked sessions—eliminating unrecorded claims or hallucinated whereabouts.
- **Human Handover:** Live notification triggers when an agent turn uncovers high mutual synergy, allowing delegates to take over the conversation in real time.

### 3.2 Mode B: Commercial RFQ & Multi-Vendor Matching
- **Procurement Query Parser:** Extracts target commodities, technical specifications (e.g., LC3 calcined clay cement, green steel grades), delivery cities/ports, quantity metrics, and lead time constraints.
- **Unit Normalization Engine:** Automatic unit conversions (`MT`, `Tons`, `kg`, `sq.ft.`) with strict dimension compatibility checks.
- **Multi-Factor Scoring Matrix:** Evaluates vendor candidates against product relevance ($\ge 60\%$ eligibility threshold), production capacity, geographical coverage, and verified industrial certifications.
- **Off-Platform Quoting via Email:** Matched vendors can inspect incoming customer asks and dispatch branded, formal commercial quotations directly to the buyer's inbox via transactional SMTP.

### 3.3 Bilateral Commercial Proposals & Gated Contact Disclosure
- **Dynamic Commercial Roles:** Configurable buyer, seller, distributor, and strategic partner contract frameworks.
- **Context-Synthesized Drafts:** Automatically pre-fills proposal scope, deliverables, and payment milestones directly from conversation dialogue turns.
- **Immutable Revision Ledger:** Full history tracking ($V_1, V_2, \dots, V_k$) with interactive visual diff sliders.
- **Cryptographic & Database Contact Disclosure Gating:** Contact coordinates (`email`, `phone_number`, direct location) are strictly masked at the database level and unlocked only when both parties commit mutual approval to the exact same revision.

### 3.4 Digital Flipbook Publication & Sponsor Ad Monetization
- **Self-Serve Exhibitor Studio (`/company/brochure`):** Drag-and-drop page upload, automated thumbnail and aspect-ratio normalization via Pillow, reordering, deletion, and instant publication toggling.
- **Interactive 3D Sensory Flipbook Viewer:**
  - Real-time page-turn simulation via `page-flip` (StPageFlip) with realistic corner curling.
  - Spectrograph-matched procedural sound synthesis via the browser's native **Web Audio API** (`PAPER_RUSTLE`, `REALISTIC_BOOK_FLIP`, `BOOK_SNAP`, `GLOSSY_MAGAZINE`).
  - Viewport-adaptive rendering: 2-page spread on desktop, single-page touch gestures on mobile.
  - High-resolution pan, double-click zoom, and one-click print stylesheet.
- **Dynamic Ad Injection Engine:**
  - **Pre-Roll Inside Front Cover (`PRE_ROLL`):** Full-spread sponsor display before page 1.
  - **Top Leaderboard Banner (`BANNER_TOP`):** Persistent banner positioned directly above the reading canvas.
  - **Targeting Matrix:** Admin control to map campaigns conference-wide or to target specific exhibitor catalogs.

### 3.5 Real-Time Page-Level Readership Telemetry
- **Granular Event Stream:** Logs distinct `OPEN` events and individual `PAGE_READ` events for every page turned (capturing both single-page mobile turns and double-page desktop spreads).
- **Time-Series Aggregation:** Chronological activity bucketing supporting `Last 24 Hours` (hourly), `Last 7 Days` (daily), `Last 30 Days`, and `All Time`.
- **Zero-Refresh Synchronization:** Real-time SSE push (`brochure:viewed`, `brochure:page_read`) coupled with TanStack Query invalidation updates dashboard counts automatically without user refresh.
- **Per-Page Funnel Analysis:** Identifies top-performing pages, percentage engagement share, unique reader session counts, and drop-off points.

### 3.6 Ambient Conference Lounge & Grounded Virtual Chat
- **Interval Broadcast Lounge:** Central conference community chat maintaining active delegate presence.
- **Temporal & Environmental Grounding:** Automated system prompts integrating live schedule changes, local weather forecasts, and venue traffic updates.

### 3.7 Multi-Tenant Administration Control Plane
- **Master Monetization & Ad Engine:** Real-time monitoring of impressions, click-through rates (CTR), active campaigns, and sponsor targeting.
- **Review Queues:** Administrative oversight for submitted conferences, organizer verification credentials, and formal proposals.

---

## 4. Technical Deep-Dive

### Dual-Role Least-Privilege Database Architecture (GAP-02)

To protect against SQL injection and privilege escalation, the PostgreSQL database operates under two distinct role boundaries:

1. **`converge_ai_owner` (DDL & Schema Migration Role):**
   - Possesses ownership of all 5 database schemas (`core`, `agenda`, `a2a`, `matching`, `brochures`).
   - Exclusively utilized by **Alembic** during automated deployment migrations.
   - Disallowed from general application request servicing.
2. **`converge_ai_app` (DML Application Runtime Role):**
   - Strictly restricted to `SELECT`, `INSERT`, `UPDATE`, `DELETE` operations on application tables.
   - Explicitly denied `CREATE`, `DROP`, `ALTER`, or schema manipulation privileges. Verified by automated security test suites (`test_runtime_role_cannot_perform_ddl`).

### Real-Time Pub/Sub & Zero-Refresh Cache Synchronization

```
┌─────────────────────────────────┐
│   FastAPI Backend Event Broker  │
│      (app/core/events.py)       │
└──────────────┬──────────────────┘
               │  Publish Event: 'brochure:page_read'
               ▼
┌─────────────────────────────────┐
│ Server-Sent Events (SSE) Stream │
│     GET /events/stream          │
└──────────────┬──────────────────┘
               │  JSON Payload Frame
               ▼
┌─────────────────────────────────┐
│ Client: RealtimeSyncProvider    │
│  (RealtimeSyncContext.tsx)      │
└──────────────┬──────────────────┘
               │  queryClient.invalidateQueries(...)
               ▼
┌────────────────────────────────────────────────────────┐
│ TanStack React Query Cache Invalidation                │
│ • ['admin', 'brochure-analytics']                     │
│ • ['my-brochure', 'analytics']                        │
│ • ['my-brochure']                                     │
└────────────────────────────────────────────────────────┘
```

The system employs an in-memory asynchronous event broker (`RealtimeEventBroker`) managing active `asyncio.Queue` channels for web clients. Whenever significant domain actions occur (e.g. conference approvals, proposal updates, brochure page turns), the backend publishes named events to SSE queues. The React client invalidates the exact TanStack Query keys, achieving immediate, zero-refresh UI updates.

### Durable Background Task Execution Engine

Background tasks (e.g. AI agent dialogue progression, thumbnail generation, email dispatch) are executed via a robust PostgreSQL-backed queue:
- **Concurrency Control:** Claims pending tasks using `SELECT ... FOR UPDATE SKIP LOCKED` across concurrent workers.
- **Lease Expiration & Worker Recovery:** Tasks carry time-bound leases; stalled or failed workers are automatically detected and reclaimed.
- **Idempotency:** Unique task fingerprinting prevents redundant agent execution.

---

## 5. Technology Stack

| Layer | Technologies & Libraries | Key Responsibilities |
| :--- | :--- | :--- |
| **Frontend Framework** | React 18, TypeScript 5.6, Vite 5 | SPA interface, reactive state management, strict type safety |
| **State & Cache** | TanStack React Query v5 | Server state caching, optimistic updates, real-time invalidation |
| **Styling & UI** | Tailwind CSS 3.4 | Responsive layouts (mobile 360px+ to desktop 1440px+), custom theme |
| **Sensory & Physics** | `page-flip` (StPageFlip), Web Audio API | 3D paper-curling physics, procedural acoustic turn audio |
| **Backend Framework** | Python 3.12, FastAPI 0.115, Pydantic v2 | High-throughput asynchronous REST API, OpenAPI auto-documentation |
| **Database & ORM** | PostgreSQL 16+, SQLAlchemy 2.0 (Async), asyncpg | Relational persistence, connection pooling, 5-schema architecture |
| **Database Migrations**| Alembic 1.13, psycopg2 | Version-controlled DDL migrations under `converge_ai_owner` role |
| **Real-Time Streaming**| Server-Sent Events (SSE), WebSockets | Asynchronous pub/sub event broadcasting, live lounge chat |
| **Image Processing** | Pillow (PIL) | High-res brochure page resizing, aspect calculation, WebP thumbnails |
| **Testing Frameworks** | Pytest, AnyIO, Vitest, React Testing Library | 200+ unit, integration, security, and UI regression tests |
| **Infrastructure** | Linux (Ubuntu 24.04), Nginx, systemd, Rsync | Reverse proxy, process supervision, hardened zero-downtime deployment |

---

## 6. Repository Structure

```
converge-ai/
├── backend/
│   ├── alembic/                      # Database migration scripts
│   │   └── versions/                 # Additive versioned migrations (001 -> 030)
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/               # API endpoints (admin, brochures, a2a, matching, etc.)
│   │   ├── core/                     # Config, security, session handling, event broker
│   │   ├── db/
│   │   │   └── models/               # SQLAlchemy ORM models across 5 schemas
│   │   ├── lib/                      # Helper libraries (unit conversion, taxonomy)
│   │   ├── schemas/                  # Pydantic v2 request/response contracts
│   │   ├── services/                 # Domain business logic & AI orchestration engines
│   │   └── main.py                   # FastAPI application factory & lifespan handler
│   ├── scripts/                      # Database provisioning & utility scripts
│   └── tests/                        # Pytest suite (API contracts, A2A, migrations, security)
├── frontend/
│   ├── src/
│   │   ├── components/               # Modular UI components (brochures, proposals, chat)
│   │   ├── lib/                      # API clients, Web Audio acoustic synthesis, SSE sync
│   │   ├── routes/                   # Route views (Admin, Company Studio, Viewer, Lounge)
│   │   └── types/                    # TypeScript domain interfaces matching Pydantic schemas
│   ├── tests/                        # Vitest + React Testing Library test suites
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── deploy_prod.sh                    # Automated production release & migration pipeline
└── README.md                         # Project documentation
```

---

## 7. Local Development Setup

### Prerequisites
- **Python:** `3.12.3+` with `python3-venv`
- **Node.js:** `20.x+` with `npm`
- **PostgreSQL:** `16+` active on `127.0.0.1:5432`

### 1. Database Provisioning
Run the database initialization script as a PostgreSQL superuser to establish the dual-role architecture:

```bash
sudo -u postgres psql -f backend/scripts/provision_db.sql
```

### 2. Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start API development server
uvicorn app.main:app --host 127.0.0.1 --port 8030 --reload
```
The backend API is accessible at `http://127.0.0.1:8030` with interactive Swagger docs at `/converge-api/v1/docs`.

### 3. Frontend Setup
```bash
cd frontend
npm install

# Start Vite development server
npm run dev
```
The frontend is accessible at `http://localhost:5173`.

---

## 8. Automated Testing & Verification

The platform maintains high test coverage across both backend and frontend layers.

### Run Backend Tests (Pytest)
```bash
cd backend
source .venv/bin/activate

# Execute all backend tests
pytest -q

# Test migration integrity (downgrade & re-upgrade verification)
pytest tests/test_migrations.py -q
```

### Run Frontend Tests (Vitest & Typecheck)
```bash
cd frontend

# Verify TypeScript compilation
npm run type-check

# Execute Vitest test suite
npm test
```

---

## 9. Production Deployment Pipeline

Deployments are executed via the hardened zero-downtime release pipeline (`deploy_prod.sh`):

```bash
./deploy_prod.sh
```

### Automated Pipeline Stages:
1. **Frontend Compilation:** Executes `npm run build` (`tsc --noEmit && vite build`) to generate minified, hash-versioned assets in `dist/`.
2. **Backend Synchronization:** Transmits updated application code and migration files to the production host via `rsync` over SSH.
3. **Frontend Distribution:** Synchronizes `dist/` directly to the Nginx serving root with atomic directory replacement.
4. **Remote Migration & Service Cycle:**
   - Applies pending Alembic migrations under `converge_ai_owner`.
   - Restarts the `converge-ai.service` systemd unit.
   - Validates Nginx configuration (`nginx -t`) and executes graceful reload.
5. **Health Verification:** Executes an automated cURL check against `/converge-api/v1/health/ready` to verify system readiness.

---

## License

Proprietary enterprise software developed for the **Converge AI Conference & Industrial Agent Network**. All rights reserved.

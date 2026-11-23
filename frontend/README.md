# Converge AI — Frontend Foundation (Phase 1, WS-4)

This directory contains the React 18, Vite, TypeScript, and Tailwind CSS frontend application for **Converge AI — Conference Agent Network**.

---

## 1. Prerequisites

- Node.js v18.19+ (tested on Node v18.19.1 in Ubuntu 24.04 / WSL 2)
- npm 9.2+

---

## 2. Setup & Installation

From the repository root (`/home/sanjana/converge-ai/`):

```bash
cd frontend
npm install
```

---

## 3. Development Server

Start the local Vite development server:

```bash
npm run dev
```

- Accessible locally at: `http://localhost:3000/converge/`
- Local proxy: Requests to `/converge-api/*` are proxied to the backend at `http://127.0.0.1:8030`.

---

## 4. Production Build & Static Assets

Compile the TypeScript application and generate the production distribution:

```bash
npm run build
```

- Target output: `frontend/dist/`
- Base URL prefix: `/converge/`
- Assets emitted: `frontend/dist/assets/`

---

## 5. Verification Commands

```bash
# TypeScript type checking
npm run type-check

# Component and unit tests
npm test
```

---

## 6. Architecture & Design System

- **Visual Direction:** Warm Editorial Aesthetic (Alabaster `#FAF7F2`, deep charcoal `#1C1917`, brass `#B47834`, terracotta `#C25438`, sage `#3E634F`).
- **Iconography Standard:** Native Emojis used exclusively and selectively (☕, 💬, 🤝, 📅, ⭐, 🔒, ✅, ❌, ⏳, 🤖). Zero external icon font/SVG libraries.
- **Data Integrity Policy:** Zero simulated participants, fake agenda sessions, or hardcoded match scores. The UI displays truthful live telemetry from `/converge-api/v1/health`, `/health/ready`, and `/version`.

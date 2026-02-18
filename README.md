# Application Vault

A local-first, archive-oriented job application management system. Capture job postings, store submitted documents as immutable copies, track your application timeline, and generate calendar reminders — all stored privately on your own machine.

## Features

- **Job capture** — save job postings as text snapshots via one-click browser extension or URL paste
- **Document vault** — store immutable copies of every CV and cover letter you submit, versioned per application
- **Application timeline** — full event ledger (Saved → Shortlisted → Submitted → Interview → Offer / Rejected)
- **Calendar integration** — generate `.ics` deadline reminders compatible with Google Calendar, Outlook, and Apple Calendar
- **Full-text search** — search across all captured job descriptions and metadata
- **Backup and restore** — export your entire vault as a zip; restore from any backup
- **Vault lock** — passphrase-protected vault with auto-lock timeout
- **Analytics** — response rates, stage durations, ghost rate tracking
- **Offline-first** — no account, no cloud required; all data stays on your machine

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, aiosqlite, Argon2 |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Zustand |
| Browser Extension | Manifest V3 (Chrome/Firefox) |
| Storage | SQLite + local filesystem |

## Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- pip

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd applications-vault
```

### 2. Install backend dependencies

```bash
make install
```

This installs the FastAPI backend and all Python dependencies into a virtual environment under `backend/.venv`.

### 3. Install frontend dependencies

```bash
make install-frontend
```

## Running in Development

The backend and frontend run as separate processes. Open two terminals:

**Terminal 1 — Backend (API server)**
```bash
make dev-backend
```
The API will be available at `http://127.0.0.1:8000`.
Interactive API docs: `http://127.0.0.1:8000/docs`

**Terminal 2 — Frontend (UI)**
```bash
make dev-frontend
```
The UI will be available at `http://localhost:5173`.

## Browser Extension

The extension lets you capture job postings with one click from any web page.

**Load in Chrome / Edge:**
1. Go to `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** and select the `extension/` folder

**Load in Firefox:**
1. Go to `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on**
3. Select `applications-vault/extension/dist/firefox.json`

> The extension requires the backend to be running at `http://127.0.0.1:8000`.

## Configuration

All settings use the `VAULT_` environment variable prefix. Defaults are sensible for local use.

| Variable | Default | Description |
|----------|---------|-------------|
| `VAULT_VAULT_PATH` | `~/ApplicationVault` | Where vault data is stored |
| `VAULT_AUTO_LOCK_SECONDS` | `900` | Idle timeout before vault locks (seconds) |
| `VAULT_MAX_UPLOAD_BYTES` | `10485760` | Max document upload size (10 MiB) |
| `VAULT_PORT` | `8000` | Backend port |

Example — custom vault location:
```bash
VAULT_VAULT_PATH=/data/my-vault make dev-backend
```

## Vault Storage Layout

All data is stored in a single portable directory:

```
~/ApplicationVault/
├── db.sqlite          # all metadata, events, tags
└── jobs/
    └── <job-id>/
        ├── captures/  # text and HTML snapshots of job postings
        └── documents/ # immutable copies of submitted CVs and cover letters
```

The vault directory is self-contained and can be copied or backed up directly.

## Running Tests

```bash
make test
```

## Building for Production

```bash
make build
```

Outputs a production-ready frontend bundle to `frontend/dist/`.

## First Launch

On first use:
1. Start the backend and open the UI at `http://localhost:5173`
2. Create a passphrase to lock your vault
3. (Recommended) Save the generated recovery key in a safe place
4. Start capturing jobs

> **Important:** If you lose your passphrase and recovery key, the vault cannot be recovered. This is by design — your data is private.

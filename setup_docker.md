# 🐳 Docker Setup Guide

This document explains how to run the project using **Docker** and **Makefile**.

---

## 📦 Prerequisites

* [Docker](https://www.docker.com/) installed and running
* [Make](https://www.gnu.org/software/make/)

  * macOS: `xcode-select --install`
  * Ubuntu/WSL: `sudo apt install make`

---

## ⚙️ Environment Setup

Create a `.env` files

```env
# backend/.env.docker
# backend/.env

PORT=

POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
POSTGRES_HOST=
POSTGRES_PORT=

DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DB_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}?schema=public"

ACCESS_TOKEN_SECRET=
ACCESS_TOKEN_EXPIRE=
REFRESH_TOKEN_SECRET=
REFRESH_TOKEN_EXPIRE=
```

```env
# frontend/.env.local

VITE_APPWRITE_URL="https://cloud.appwrite.io/v1"
VITE_APPWRITE_PROJECT_ID=
VITE_APPWRITE_DATABASE_ID=
VITE_APPWRITE_STORAGE_ID=
VITE_APPWRITE_USER_COLLECTION_ID=
VITE_APPWRITE_POST_COLLECTION_ID=
VITE_APPWRITE_SAVES_COLLECTION_ID=
```

```env
# /.env

POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
POSTGRES_PORT=
DB_HOST=

DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DB_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}?schema=public"

```
> ⚠️ Do not commit `.env` to Git. Make sure it's listed in `.gitignore`.

---

## 🚀 First-Time Setup

Run the following command:

```bash
make first-run
```

This will:

* Build and start all services in the background
* Create and apply the initial Prisma migration (`--name init`)
* Start the backend server

You can access:

* Frontend: [http://localhost:5173](http://localhost:5173)
* Backend: [http://localhost:5000](http://localhost:5000)

---

## 🏃 Normal Workflow

After the first run, use:

```bash
make run
```

This will:

* Start containers (if not already running)
* Apply any new Prisma migrations
* Start the backend server

---

## 🔧 Useful Commands

| Command              | Description                                        |
| -------------------- | -------------------------------------------------- |
| `make up`            | Start all containers in the background             |
| `make stop`          | Stop containers without removing data              |
| `make reset`         | Stop and remove containers + volumes (clean slate) |
| `make logs`          | View logs from all services (live)                 |
| `make logs-backend`  | View backend logs only                             |
| `make logs-frontend` | View frontend logs only                            |
| `make logs-db`       | View database logs only                            |
| `make studio`        | Open Prisma Studio GUI                             |
| `make status`        | Check Prisma migration status                      |
| `make seed`          | Run seed script (if defined)                       |

---

## 📁 File Structure (Docker-Related)

```
.
├── backend/             # Contains .env and backend code
├── frontend/            # Vite frontend
├── docker-compose.yml   # Orchestration for backend, frontend, and db
├── Makefile             # Dev automation commands
└── README-docker.md     # ← This file
```

---

## ✅ Notes

* Containers are detached by default (run in background)
* Use `make logs` to view what's happening inside services
* You can run `make reset` anytime to wipe the system and start fresh

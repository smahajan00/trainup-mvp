# TrainUp

## Project Title

TrainUp — AI-Powered Multi-Sport Coaching and Performance Analysis

## Description

TrainUp is a monorepo foundation for an AI-powered coaching platform spanning multiple sports. This setup focuses on production-ready scaffolding only: a Next.js frontend, a FastAPI backend, PostgreSQL via Docker, shared environment configuration, and clean project structure for future feature development.

## Tech Stack

- Next.js with TypeScript, App Router, Tailwind CSS, ESLint, Prettier, shadcn/ui baseline, Framer Motion, and Recharts
- FastAPI with SQLAlchemy, Alembic, Pydantic, JWT/auth-ready dependencies, and pytest
- PostgreSQL 16
- Docker and Docker Compose

## Project Structure

```text
trainup-mvp/
├── backend/
├── docs/
├── frontend/
├── infra/
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

## Setup Instructions

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker Desktop or Docker Engine with Compose

### Environment

1. Review the root [.env.example](/Users/subratamahajan/trainup-mvp/.env.example).
2. The backend includes a local [.env](/Users/subratamahajan/trainup-mvp/backend/.env) file for container-based development.
3. When running the backend directly on your host instead of Docker, override `DATABASE_URL` to use `localhost` instead of `db`.

## How to Run

### Docker

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Health check: `http://localhost:8000/api/health`
- PostgreSQL: `localhost:5432`

### Local Development

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://trainup_user:trainup_password@localhost:5432/trainup_db
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Database only:

```bash
docker compose up db -d
```

## Ports Used

- `3000`: Next.js frontend
- `8000`: FastAPI backend
- `5432`: PostgreSQL

## Future Phases Note

This repository intentionally excludes business logic, AI workflows, authentication flows, sport-specific modeling, and analytics features. Future phases can now build on a clean baseline with isolated frontend, backend, and infrastructure layers.


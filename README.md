# TrainUp

## Project Title

TrainUp — AI-Powered Multi-Sport Coaching and Performance Analysis

## Description

TrainUp is a monorepo for an AI-powered coaching platform spanning multiple sports. The current implementation includes video upload processing, MediaPipe pose extraction, deterministic drill evaluation, deterministic coaching feedback, and optional grounded LLM feedback enhancement.

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
- Python 3.12 for the backend runtime
- Docker Desktop or Docker Engine with Compose

### Environment

1. Review the root [.env.example](/Users/subratamahajan/trainup-mvp/.env.example).
2. The backend includes a local [.env](/Users/subratamahajan/trainup-mvp/backend/.env) file for container-based development.
3. When running the backend directly on your host instead of Docker, override `DATABASE_URL` to use `localhost` instead of `db`.

### Optional LLM Feedback Enhancement

Deterministic feedback is always available. LLM enhancement is optional and is
disabled by default. If LLM enhancement is disabled, no API key is configured,
the provider times out, or the response is malformed, the backend returns the
deterministic Phase 3A feedback and marks the LLM result with
`fallback_used=true`.

Configure LLM behavior through environment variables:

```bash
LLM_ENABLE_ENHANCEMENT=false
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=
LLM_BASE_URL=
LLM_TIMEOUT_SECONDS=10
LLM_MAX_TOKENS=500
LLM_TEMPERATURE=0.2
```

The current client uses an OpenAI-compatible chat-completions endpoint. To use
another compatible provider or local model server, set `LLM_PROVIDER`,
`LLM_MODEL`, `LLM_API_KEY`, and optionally `LLM_BASE_URL` without changing the
feedback business logic.

### Optional Fuzzy Interpretation

The Phase 4A fuzzy layer is additive. It reads stored deterministic
`evaluation_result` artifacts, assigns linguistic labels such as `IDEAL`,
`SLIGHTLY_OFF`, `MODERATELY_OFF`, and `STRONGLY_OFF`, and persists a
`fuzzy_interpretation_result` artifact. Deterministic severity and ranking remain
authoritative.

```bash
FUZZY_INTERPRETATION_ENABLED=true
```

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
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://trainup_user:trainup_password@localhost:5432/trainup_db
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The Phase 1 MediaPipe perception pipeline is validated against Python 3.12 and
`mediapipe==0.10.14`; keep the backend `.venv` on Python 3.12 before running
pose extraction tests or local uploads.

Database only:

```bash
docker compose up db -d
```

## Ports Used

- `3000`: Next.js frontend
- `8000`: FastAPI backend
- `5432`: PostgreSQL

## Implemented Coaching Flow

The implemented backend flow is:

```text
upload → capture validation → pose extraction → pose_sequence artifact
→ deterministic evaluation → evaluation_result artifact + metric rows
→ optional fuzzy interpretation → fuzzy_interpretation_result artifact
→ deterministic feedback → feedback_result artifact + feedback rows
→ optional LLM enhancement → llm_feedback_result artifact
```

Reevaluating a session clears downstream feedback artifacts and feedback rows so
deterministic and LLM feedback always correspond to the latest evaluation.

# TrainUp — AI-Assisted Multi-Sport Coaching and Performance Analysis

TrainUp is a bachelor project MVP for pose-based multi-sport coaching and performance analysis. The system combines uploaded or live movement capture, MediaPipe pose extraction, deterministic biomechanical evaluation, advanced reasoning layers, optional Gemini-assisted coaching wording refinement, Kokoro text-to-speech feedback, and range-based progress analytics.

The project is designed around an academically defensible boundary: deterministic evaluation and deterministic feedback remain the source of truth. The language model is used only to improve the wording, prioritization, and clarity of coaching feedback from compact supplied summaries. Kokoro TTS only reads the final coaching text. TrainUp does not perform medical diagnosis, does not use voice cloning, and does not require user voice uploads.

## Key Features

- Authentication, athlete profile setup, and skill-level-aware sessions
- Multi-sport catalog with drill preview pages and bundled drill demo videos
- Upload video and live camera session flows
- MediaPipe pose extraction and real pose overlay for uploaded and live movement
- Optimized pose extraction with frame downsampling, inference resizing, and pose cache reuse
- Drill-specific deterministic evaluation for six supported drills
- Deterministic coaching feedback and improvement plans
- Fuzzy interpretation and interval type-2 fuzzy uncertainty interpretation
- Pedagogical reasoning for skill-level-appropriate coaching tone and intensity
- Ontology reasoning for movement concepts and body-region explanations
- Choquet aggregation for linked issue reasoning
- Temporal modeling for movement timing patterns
- Gemini-assisted coaching wording refinement with deterministic fallback
- Kokoro-82M click-to-play voice coaching using the `am_michael` voice
- Weekly, monthly, and all-time progress analytics

Supported sports and drills:

- Gym: Bodyweight Squat, Dumbbell Shoulder Press
- Basketball: Set Shot Form, Defensive Stance
- Football: Instep Pass, Basic Shooting Form

## Academic Overview

TrainUp evaluates sport and exercise movements from pose landmarks rather than from raw video semantics. Uploaded or live sessions produce a `pose_sequence`, which is analyzed by deterministic drill evaluators. The deterministic layer computes movement quality, issues, severity, scores, and base feedback. Advanced reasoning layers then provide interpretation context, such as uncertainty, pedagogical style, linked issues, and movement timing.

Gemini is optional and bounded. It receives compact deterministic and advanced-reasoning summaries, not raw video, full pose sequences, or raw landmark streams. Its role is wording refinement only. If Gemini is unavailable, the system continues with deterministic coaching feedback. Kokoro TTS then speaks the visible final coaching text only after the user clicks Listen.

## Analysis Pipeline

```text
User profile
-> Sport/drill selection
-> Upload or live capture
-> pose_sequence
-> deterministic evaluation
-> fuzzy interpretation
-> IT2 fuzzy interpretation
-> deterministic feedback
-> pedagogical decision
-> ontology reasoning
-> Choquet aggregation
-> temporal modeling
-> optional Gemini coaching refinement
-> Kokoro TTS voice guidance
-> weekly/monthly/all-time progress analytics
```

## System Boundaries

- Deterministic evaluation remains the authoritative source of scores and issues.
- Gemini only refines visible coaching language from supplied summaries.
- Gemini does not receive raw video, full pose sequences, or raw pose landmark data.
- Kokoro TTS only reads the final coaching text.
- TTS is click-to-play only and does not autoplay.
- No voice cloning or user voice upload is used.
- Sample test data may be used during local development to verify dashboard and analytics behavior.
- TrainUp is a coaching aid, not a medical diagnosis system.

## Tech Stack

Frontend:

- Next.js App Router
- TypeScript
- Tailwind CSS
- Framer Motion
- Recharts
- MediaPipe Tasks Vision assets for browser-side live overlay

Backend:

- FastAPI
- PostgreSQL
- SQLAlchemy and Alembic
- MediaPipe
- OpenCV
- Gemini API via a compact HTTP client
- Kokoro-82M TTS
- Docker and Docker Compose

## Repository Structure

```text
trainup-mvp/
|-- backend/
|   |-- app/
|   |   |-- api/routes/          # FastAPI route modules
|   |   |-- core/                # config, database, dependencies, security
|   |   |-- engines/             # perception, cognition, fuzzy, ontology, aggregation, temporal engines
|   |   |-- models/              # SQLAlchemy models
|   |   |-- repositories/        # database access layer
|   |   |-- schemas/             # Pydantic API and artifact schemas
|   |   |-- seed/                # sports, drills, and metric definitions
|   |   |-- services/            # session, feedback, LLM, TTS, progress, and reasoning services
|   |   `-- utils/
|   |-- alembic/                 # migrations
|   |-- scripts/                 # utility scripts and smoke checks
|   `-- tests/
|-- frontend/
|   |-- app/                     # Next.js routes
|   |-- components/ui/           # shared UI primitives
|   |-- features/                # domain feature modules
|   |-- hooks/
|   |-- lib/
|   |-- public/
|   |   |-- mediapipe/           # browser pose model and wasm assets
|   |   `-- videos/drills/       # tracked drill demo videos
|   |-- services/                # frontend API clients
|   `-- types/                   # shared TypeScript response types
|-- docs/
|-- infra/
|-- docker-compose.yml
|-- .env.example
`-- README.md
```

Route clarification:

- `/dashboard` = Home
- `/progress` = Performance Dashboard
- `/sessions/new` = compatibility fallback for the older setup flow

Normal training flow starts from Drill Preview and routes directly into Upload or Live pages with setup controls embedded in the session page.

## Docker Quickstart

Create `backend/.env` from `.env.example`, then set a real `SECRET_KEY` and optionally `GEMINI_API_KEY`.

```bash
docker compose up --build -d
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Backend health: `http://localhost:8000/api/health`
- PostgreSQL: `localhost:5432`

## Local Development

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

Database only:

```bash
docker compose up db -d
```

Use Python 3.12 for backend development.

## Environment Variables

Start from `.env.example`. Do not commit real `.env` files.

Core variables:

```text
DATABASE_URL=postgresql://trainup_user:trainup_password@db:5432/trainup_db
SECRET_KEY=change_this
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

Gemini refinement:

```text
LLM_ENABLE_ENHANCEMENT=true
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_gemini_api_key_here
LLM_TIMEOUT_SECONDS=20
LLM_MAX_TOKENS=220
```

Kokoro TTS:

```text
TTS_ENABLED=true
TTS_MODEL=hexgrad/Kokoro-82M
TTS_VOICE=am_michael
TTS_WARMUP_ON_STARTUP=true
TTS_SEGMENT_PAUSE_MS=400
```

Pose processing:

```text
POSE_TARGET_FPS=12
POSE_MAX_WIDTH=720
POSE_CACHE_ENABLED=true
```

## Testing

Backend:

```bash
cd backend
source .venv/bin/activate
pytest tests
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run lint
```

Docker and health:

```bash
docker compose config
docker compose up -d --build backend frontend
curl http://localhost:8000/api/health
```

## Development Notes

- The Performance Dashboard supports Weekly, Monthly, and All Time analytics.
- Recent session lists are intentionally limited visually, while range totals use aggregate counts.
- If Gemini is unavailable, TrainUp uses deterministic coaching feedback without failing the analysis.
- Kokoro TTS is generated only after the user clicks Listen and cached for repeated playback.
- Sample test data may be used during local development to verify dashboard and analytics behavior.

## Git and Asset Hygiene

- `.env` files are ignored and must not be committed.
- Local model files and generated media/cache files are ignored.
- `backend/models/.gitkeep` is tracked so the model folder exists when needed.
- Drill demo videos under `frontend/public/videos/drills/*.mp4` are intentionally tracked.
- MediaPipe browser assets under `frontend/public/mediapipe` are intentionally tracked.

## Responsible AI and Ethics

TrainUp prioritizes explainability by keeping deterministic evaluation and deterministic coaching as the source of truth. LLM refinement is bounded to language improvements and cannot create new scoring outcomes. The system does not provide medical diagnosis, does not clone voices, and does not require user voice uploads. Privacy-sensitive data should be handled carefully in deployment, and user-facing claims should remain aligned with validated system capability.

## Future Work

- Expand the drill catalog and add more sports.
- Conduct real-user evaluation with athletes and coaches.
- Validate biomechanical scoring thresholds against expert annotation.
- Improve mobile capture and device-specific calibration.
- Add a coach dashboard for group progress review.
- Strengthen longitudinal analytics with larger datasets.

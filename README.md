# TrainUp

TrainUp - AI-Powered Multi-Sport Coaching and Performance Analysis.

TrainUp is an AI-assisted multi-sport coaching and performance analysis platform. It combines uploaded or live movement capture, MediaPipe pose extraction, deterministic drill evaluation, advanced reasoning artifacts, local LLM wording refinement, Kokoro voice playback, and progress analytics.

Deterministic evaluation and deterministic coaching remain the source of truth. The local LLM only refines coaching wording from supplied artifacts, and Kokoro TTS only speaks the final coaching text. TrainUp does not use voice cloning or require user voice uploads.

Repository description suggestion:

```text
AI-powered multi-sport coaching and performance analysis system using pose estimation, deterministic reasoning, advanced cognitive layers, local LLM refinement, and Kokoro TTS.
```

## Product Overview

TrainUp helps an athlete:

1. Create a profile.
2. Choose a sport and drill.
3. Review a reference demo.
4. Upload a clip or start a live camera session.
5. Extract pose data.
6. Run the analysis pipeline.
7. Read and optionally listen to coaching feedback.
8. Track progress on the performance dashboard.

Supported demo sports and drills:

- Gym: Bodyweight Squat, Dumbbell Shoulder Press
- Basketball: Set Shot Form, Defensive Stance
- Football: Instep Pass, Basic Shooting Form

## Current Implemented Features

- Multi-sport drill catalog
- Upload session flow
- Live camera session flow
- MediaPipe pose extraction
- Real pose overlay for uploaded video and live camera preview
- Optimized pose extraction with frame downsampling, inference resizing, and pose cache reuse
- Deterministic drill evaluation
- Deterministic coaching feedback
- Fuzzy interpretation
- IT2 fuzzy uncertainty interpretation
- Pedagogical decision layer
- Ontology reasoning
- Choquet aggregation
- Temporal modeling
- Local Qwen2.5 GGUF coaching refinement through llama.cpp
- Kokoro-82M TTS voice coaching with the `am_michael` voice
- Click-to-play cached coaching audio
- Progress dashboard and training analytics
- Synthetic demo athlete seed data

## Architecture Overview

```text
trainup-mvp/
|-- backend/              # FastAPI, SQLAlchemy, analysis services, AI/TTS services
|-- frontend/             # Next.js App Router, Tailwind UI, session and dashboard flows
|-- docs/                 # Project documentation placeholders
|-- infra/                # Infrastructure documentation placeholders
|-- docker-compose.yml    # Frontend, backend, PostgreSQL
|-- .env.example          # Root environment template
`-- README.md
```

Backend highlights:

- FastAPI application under `backend/app`
- SQLAlchemy models and repositories
- MediaPipe pose extraction through the perception interface
- Deterministic evaluation and feedback services
- Advanced reasoning services: fuzzy, IT2 fuzzy, pedagogy, ontology, Choquet, temporal
- Local Qwen GGUF refinement through llama.cpp
- Kokoro TTS for click-to-play coaching audio

Frontend highlights:

- Next.js App Router under `frontend/app`
- Feature modules under `frontend/features`
- API clients under `frontend/services`
- Shared TypeScript contracts under `frontend/types`
- Public MediaPipe assets under `frontend/public/mediapipe`
- Drill demo videos under `frontend/public/videos/drills`

## Route Clarification

Some route names are preserved for compatibility:

- `/dashboard` = Home
- `/progress` = Performance Dashboard
- `/sessions/new` = compatibility fallback for the older setup flow

Normal training flow now starts from Drill Preview and goes directly to Upload or Live session pages with setup controls embedded there.

## Full User Flow

```text
Landing page
-> Sign up or log in
-> Create or update profile
-> Home (/dashboard)
-> Sports catalog
-> Drill list
-> Drill Preview
-> Upload Video or Live Camera
-> Session setup strip
-> Capture/upload
-> Pose extraction
-> Analysis pipeline
-> Coaching feedback and optional voice playback
-> Performance Dashboard (/progress)
```

Existing sessions can still be reopened from Home, Results, or the Performance Dashboard.

## Demo Flow

For a supervisor demo:

1. Start Docker services.
2. Seed the synthetic demo athlete.
3. Log in with demo credentials.
4. Open Home, Sports, Drill Preview, Upload, Results, and Performance Dashboard.
5. Use one of the bundled drill demo videos or upload a clean movement clip.
6. Run analysis and optionally play coaching feedback through Kokoro TTS.

Demo credentials:

```text
email: demo.athlete@trainup.local
password: DemoPass123!
```

The seeded athlete history is synthetic demo data only. It is not validation data, real athlete data, or user-study data.

## Docker Quickstart

```bash
docker compose up --build -d
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Health check: `http://localhost:8000/api/health`
- PostgreSQL: `localhost:5432`

Seed demo data after the backend is running:

```bash
docker compose exec backend python scripts/seed_demo_athlete.py
```

The backend Dockerfile installs CPU-only PyTorch wheels to avoid NVIDIA CUDA packages and keep Docker/macOS demo builds smaller.

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

Use Python 3.12 for backend development. MediaPipe pose extraction is validated against the backend dependency set in `backend/requirements.txt`.

## Environment Variables

Start from `.env.example`. Docker Compose reads `backend/.env` for backend container configuration and passes `NEXT_PUBLIC_API_URL` to the frontend.

Important groups:

- Database and auth: `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- Frontend API: `NEXT_PUBLIC_API_URL`
- CORS: `BACKEND_CORS_ORIGINS`
- Pose processing: `POSE_TARGET_FPS`, `POSE_MAX_WIDTH`, `POSE_CACHE_ENABLED`
- LLM: `LLM_ENABLE_ENHANCEMENT`, `LLM_PROVIDER`, `LLM_MODEL_PATH`, `LLM_MODEL_REPO_ID`, `LLM_MODEL_FILENAME`
- TTS: `TTS_ENABLED`, `TTS_MODEL`, `TTS_VOICE`, `TTS_SEGMENT_PAUSE_MS`

## Analysis Pipeline Order

The current end-to-end coaching pipeline is:

```text
Upload/Live capture
-> pose_sequence
-> deterministic evaluation
-> fuzzy interpretation
-> IT2 fuzzy interpretation
-> deterministic feedback
-> pedagogical decision
-> ontology reasoning
-> Choquet aggregation
-> temporal modeling
-> Qwen2.5 local coaching refinement
-> Kokoro TTS voice guidance
-> dashboard/progress analytics
```

Required stages:

- Evaluation
- Deterministic feedback

Optional enrichment stages:

- Fuzzy interpretation
- IT2 fuzzy interpretation
- Pedagogy
- Ontology reasoning
- Choquet aggregation
- Temporal modeling
- Local LLM feedback refinement

Required failures block analysis completion. Optional failures are surfaced as warnings and should not hide deterministic feedback.

Important boundaries:

- Deterministic logic remains the source of truth.
- The LLM may refine wording, prioritization, tone, and explanation clarity only.
- The LLM must not invent movement issues, override scores, or replace deterministic evaluation.
- TTS must not create coaching logic; it only speaks final coaching text.
- Demo dashboard data is synthetic and should not be presented as validation or user-study data.

## Pose Extraction and Overlay

Upload flow:

- Uploaded video is stored for the session.
- Frames are sampled according to `POSE_TARGET_FPS`.
- Inference frames are resized up to `POSE_MAX_WIDTH` without changing the stored video.
- Pose landmarks are saved as a `pose_sequence` session artifact.
- The upload preview uses the stored `pose_sequence` to draw the movement overlay during playback.

Live flow:

- Camera preview runs in the browser.
- Browser-side MediaPipe assets are loaded from `frontend/public/mediapipe`.
- The live overlay draws detected landmarks in real time without sending frames to the backend just for preview.

Pose cache:

- Upload pose extraction can reuse a session-local cached pose artifact when the uploaded file hash and processing settings match.
- Changed files or changed processing settings force pose recomputation and clear stale downstream analysis artifacts.

## Qwen GGUF Local LLM Setup

TrainUp uses local llama.cpp refinement when enabled. This is the current primary LLM setup. The GGUF model file is not committed to Git.

Default model configuration:

```text
repo: bartowski/Qwen2.5-7B-Instruct-GGUF
file: Qwen2.5-7B-Instruct-Q4_K_M.gguf
path: backend/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf
```

The model must be available locally under `backend/models/` for local refinement. The service is configured for the repo and filename above and can reuse the local model file once present. `backend/models/*.gguf` is ignored by Git, while `backend/models/.gitkeep` remains trackable so the directory exists in the repository.

Useful variables:

```bash
LLM_ENABLE_ENHANCEMENT=false
LLM_PROVIDER=llama_cpp
LLM_MODEL=Qwen2.5-7B-Instruct-Q4_K_M.gguf
LLM_MODEL_PATH=models/Qwen2.5-7B-Instruct-Q4_K_M.gguf
LLM_MODEL_REPO_ID=bartowski/Qwen2.5-7B-Instruct-GGUF
LLM_MODEL_FILENAME=Qwen2.5-7B-Instruct-Q4_K_M.gguf
LLM_WARMUP_ON_STARTUP=false
```

The LLM may refine coaching wording, prioritization, and clarity. It must not invent issues, override scores, or replace deterministic evaluation.

Optional legacy/external provider support may still be configured through OpenAI-compatible fields such as `LLM_API_KEY` and `LLM_BASE_URL`, but the documented default is local llama.cpp with Qwen2.5 GGUF.

## Kokoro TTS Setup

TrainUp uses Kokoro-82M only for click-to-play coaching feedback audio.

Default configuration:

```bash
TTS_ENABLED=true
TTS_MODEL=hexgrad/Kokoro-82M
TTS_VOICE=am_michael
TTS_WARMUP_ON_STARTUP=false
TTS_SEGMENT_PAUSE_MS=400
```

Audio responses are cached by session, text hash, model, voice, and pause settings where applicable. TTS must not autoplay; the user starts playback by clicking Listen.

TTS speaks only the short coaching script:

1. Main coaching cue
2. What to fix
3. Next session cue

TTS is non-blocking. If model loading or synthesis fails, visible text feedback remains available.

## Demo Seed Script

```bash
docker compose exec backend python scripts/seed_demo_athlete.py
```

The script safely resets and recreates only `demo.athlete@trainup.local`. It creates synthetic sessions, summaries, progress records, metric results, feedback, and analysis artifacts for dashboard demonstrations.

## Test Commands

Frontend:

```bash
cd frontend
npm run typecheck
npm run lint
```

Backend:

```bash
cd backend
source .venv/bin/activate
pytest
```

Run focused backend tests when changing a narrow area, for example:

```bash
pytest tests/test_feedback_tts.py
pytest tests/test_phase3b_llm_feedback.py
pytest tests/test_upload_pose_cache.py
```

## Git, Model, and Media Hygiene

Do not commit:

- `.env` files
- Python virtual environments
- `node_modules`
- `.next`
- generated caches
- GGUF/bin/safetensors model files
- generated audio/cache files

Intentional tracked media:

- `frontend/public/videos/drills/*.mp4`
- `backend/tests/assets/squat1.mov`

The Qwen GGUF belongs in `backend/models/` locally and should stay ignored.

## Troubleshooting

Backend health:

```bash
curl -s http://127.0.0.1:8000/api/health
```

Frontend cannot reach backend:

- Check `NEXT_PUBLIC_API_URL`.
- Check backend CORS origins.
- Confirm backend is running on port `8000`.

Pose overlay missing:

- Confirm `frontend/public/mediapipe` assets are present.
- Check browser network requests for MediaPipe task and wasm files.
- Confirm the session has a valid `pose_sequence` artifact for upload overlay.

Local LLM slow first use:

- Confirm the GGUF file exists under `backend/models`.
- Enable `LLM_WARMUP_ON_STARTUP=true` only when demo startup time is acceptable.

TTS slow first use:

- Kokoro downloads/loads on first use.
- Enable `TTS_WARMUP_ON_STARTUP=true` for demos if startup latency is acceptable.

Docker rebuild downloads large packages:

- Backend Docker installs CPU-only PyTorch wheels.
- Avoid adding CUDA or NVIDIA-specific dependencies.

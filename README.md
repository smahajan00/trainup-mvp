# TrainUp: AI-Powered Multi-Sport Coaching and Performance Analysis

TrainUp is a bachelor project MVP for AI-powered multi-sport coaching and performance analysis. The system combines uploaded-video movement capture, browser-side live pose preview, MediaPipe pose estimation, deterministic drill-specific movement evaluation, rep-cycle segmentation where applicable, set-level aggregation, coaching feedback generation, optional Gemini-assisted wording refinement, Kokoro text-to-speech feedback, and range-based progress analytics.

The project is designed around an academically defensible boundary: deterministic evaluation and deterministic feedback remain the source of truth. Gemini is used only to improve the wording, readability, and clarity of coaching feedback from compact supplied summaries. It does not decide scores, severity levels, priorities, or detected movement issues. Kokoro TTS only reads the final coaching text. TrainUp does not perform medical diagnosis, does not use voice cloning, and does not require user voice uploads.

## Key Features

- User registration, login, authentication, and protected routes
- Athlete profile setup with sport preference and skill-level context
- Multi-sport catalogue with sport and drill selection
- Drill preview pages with setup guidance, focus points, and preparation instructions
- Upload-video analysis flow for saved performance evaluation
- Browser-side live camera preview for camera angle, framing, and readiness checking
- MediaPipe and OpenCV-based pose extraction from uploaded videos
- Pose overlay display for uploaded-video movement review
- Video upload validation for supported file types and file size limits
- Drill-specific deterministic movement evaluation
- Severity-based movement issue classification
- Multi-joint movement checks within selected drill contexts
- Temporal movement assessment where applicable
- Rep-cycle segmentation and set-level aggregation where applicable
- Deterministic coaching feedback and improvement suggestions
- Optional Gemini wording refinement with deterministic fallback
- Kokoro TTS click-to-play voice coaching
- Weekly, monthly, and all-time progress analytics
- Progress dashboard with session history, trends, key weakness, and drill breakdown
- Validation and error handling for invalid login, invalid upload, missing data, and failed analysis states

## Supported Sports and Drills

The current MVP supports selected representative sports and drills for academic demonstration.

- Gym: Squat, Shoulder Press
- Basketball: Basketball Set Shot, Defensive Stance
- Football: Instep Pass, Basic Shooting Form

The drill catalogue is intentionally limited in the current version. Future versions can expand the catalogue with more sports, drills, reference rules, validation examples, and coaching templates.

## Training Flows

TrainUp separates camera readiness from saved performance analysis.

### Live Camera Preview

The live camera feature provides browser-side pose preview and setup support. It helps users check camera angle, framing, full-body visibility, lighting, and general recording readiness before capturing a training video.

In the current MVP, the live camera feature does not generate saved backend performance results and does not persist a backend `pose_sequence`.

### Upload Video Analysis

The upload-video flow is the main saved analysis workflow. A recorded training video is uploaded to the backend, processed into a pose sequence, evaluated by the deterministic movement pipeline, and used to generate saved results, coaching feedback, optional Gemini-refined wording, TTS playback, and progress records.

For complete analysis and saved progress tracking, use:

```text
Drill Preview -> Upload Video -> Analyze Performance -> Results -> Progress Dashboard
```

## Academic Overview

TrainUp evaluates sport and exercise movements from pose landmarks extracted from uploaded videos. The backend processes uploaded media using OpenCV and MediaPipe, creates structured pose-related data, and passes this data to deterministic drill-specific evaluators.

The deterministic evaluation layer computes movement quality, detected issues, severity levels, scores, and base feedback. Where applicable, the evaluator uses rep-cycle segmentation and set-level aggregation to produce one session-level coaching outcome from a recorded drill set.

Gemini is optional and bounded. It receives compact deterministic summaries rather than raw video, full pose sequences, or raw landmark streams. Its role is wording refinement only. If Gemini is unavailable, the system continues using deterministic coaching feedback.

Kokoro TTS converts the visible final coaching text into audio after the user clicks the listen control. TTS does not autoplay and does not use voice cloning.

TrainUp is an academic prototype and training-support system. It is not a medical diagnosis tool, injury assessment system, rehabilitation platform, or professional sports certification system.

## Analysis Pipeline

```text
User profile
-> Sport/drill selection
-> Drill preview
-> Uploaded video
-> Video validation
-> MediaPipe/OpenCV pose extraction
-> pose_sequence
-> Pose overlay
-> Deterministic drill-specific evaluation
-> Rep-cycle segmentation where applicable
-> Set-level aggregation where applicable
-> Severity-based classification
-> Multi-joint movement checks
-> Deterministic feedback generation
-> Optional Gemini wording refinement
-> Kokoro TTS click-to-play voice guidance
-> Session summary and progress persistence
-> Weekly/monthly/all-time progress analytics
```

## System Boundaries

- Deterministic evaluation remains the authoritative source of scores and detected issues.
- Gemini does not decide scores, severity levels, priorities, or movement faults.
- Gemini only refines wording, readability, and coaching tone from supplied summaries.
- Gemini does not receive raw video, full pose sequences, or raw landmark streams.
- Kokoro TTS only reads the final visible coaching text.
- TTS is click-to-play only and does not autoplay.
- No voice cloning or user voice upload is used.
- Coaching feedback is educational training support only.
- TrainUp is not clinically or professionally validated.
- TrainUp does not provide medical diagnosis, injury assessment, rehabilitation advice, or professional sports certification.
- Evaluation thresholds are heuristic prototype thresholds and require future validation using expert-labelled videos.
- 2D pose estimation cannot reliably measure true 3D movement, force, pressure, external load, ball contact, or camera-calibrated depth.
- Results depend on pose-tracking quality, lighting, camera angle, framing, and clear full-body visibility.
- Live camera is a browser-side preview and setup check in the current MVP.
- Saved backend analysis and progress persistence currently use uploaded videos.
- Raw video is handled temporarily during processing and is not retained by default.
- Sample test data may be used during local development to verify dashboard and analytics behaviour.

## Tech Stack

### Frontend

- Next.js App Router
- React
- TypeScript
- Tailwind CSS
- Framer Motion
- Recharts
- MediaPipe Tasks Vision assets for browser-side live overlay

### Backend

- FastAPI
- Uvicorn
- PostgreSQL
- SQLAlchemy
- Alembic
- MediaPipe
- OpenCV
- Gemini API through a bounded HTTP client
- Kokoro TTS
- Docker and Docker Compose

### Development and Version Control

- VS Code
- Git
- GitHub

## Repository Structure

```text
trainup-mvp/
|-- backend/
|   |-- app/
|   |   |-- api/routes/          # FastAPI route modules
|   |   |-- core/                # config, database, dependencies, security
|   |   |-- engines/             # perception, cognition, evaluation, timing, and support logic
|   |   |-- models/              # SQLAlchemy models
|   |   |-- repositories/        # database access layer
|   |   |-- schemas/             # Pydantic API and artifact schemas
|   |   |-- seed/                # sports, drills, and metric definitions
|   |   |-- services/            # session, feedback, LLM, TTS, progress, and analysis services
|   |   `-- utils/
|   |-- alembic/                 # database migrations
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
|   |   `-- videos/drills/       # drill demo videos
|   |-- services/                # frontend API clients
|   `-- types/                   # shared TypeScript response types
|-- docs/
|-- infra/
|-- docker-compose.yml
|-- .env.example
`-- README.md
```

## Main Routes

```text
/                         Landing page
/signup                   Registration page
/login                    Login page
/profile                  Profile setup page
/dashboard                Home page
/sports                   Sport selection page
/sports/[sportId]/drills  Drill selection page
/drills/[drillId]         Drill preview page
/progress                 Progress analytics dashboard
```

Route clarification:

- `/dashboard` is the authenticated home page.
- `/progress` is the performance analytics dashboard.
- Upload-video analysis is the main saved analysis path.
- Live camera is used for preview, framing, and capture-readiness support.

## Docker Quickstart

Create `backend/.env` from `.env.example`, then set a real `SECRET_KEY` and optionally set `GEMINI_API_KEY`.

```bash
docker compose up --build -d
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Backend health check: `http://localhost:8000/api/health`
- PostgreSQL: `localhost:5432`

## Local Development

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://trainup_user:trainup_password@localhost:5432/trainup_db
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Only

```bash
docker compose up db -d
```

Use Python 3.12 for backend development.

## Environment Variables

Start from `.env.example`. Do not commit real `.env` files.

### Core Variables

```text
DATABASE_URL=postgresql://trainup_user:trainup_password@db:5432/trainup_db
SECRET_KEY=change_this
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### Gemini Wording Refinement

```text
LLM_ENABLE_ENHANCEMENT=true
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_gemini_api_key_here
LLM_TIMEOUT_SECONDS=20
LLM_MAX_TOKENS=220
```

### Kokoro TTS

```text
TTS_ENABLED=true
TTS_MODEL=hexgrad/Kokoro-82M
TTS_VOICE=am_michael
TTS_WARMUP_ON_STARTUP=true
TTS_SEGMENT_PAUSE_MS=400
```

### Pose Processing

```text
POSE_TARGET_FPS=20
POSE_MAX_WIDTH=720
POSE_CACHE_ENABLED=true
```

## Testing

### Backend Tests

```bash
cd backend
source .venv/bin/activate
pytest tests
```

### Frontend Checks

```bash
cd frontend
npm run typecheck
npm run lint
```

### Docker and Health Checks

```bash
docker compose config
docker compose up -d --build backend frontend
curl http://localhost:8000/api/health
```

## Recommended Demo Flow

For final demonstration, use the uploaded-video workflow because it is the complete saved analysis path.

1. Open the landing page.
2. Register or log in.
3. Complete the profile setup.
4. Open the dashboard.
5. Select a sport.
6. Select a drill.
7. Review the drill preview and setup guidance.
8. Upload a valid training video.
9. Confirm pose overlay output.
10. Run analysis.
11. Review performance overview and coaching feedback.
12. Play Kokoro TTS audio.
13. Open the progress dashboard.
14. Review trends, session history, and drill breakdown.

Use the live camera page only to show preview and capture-readiness support.

## Development Notes

- The progress dashboard supports weekly, monthly, and all-time analytics.
- Persisted backend analysis currently runs through uploaded videos.
- The live page is a browser-side pose preview, setup check, and readiness scaffold.
- The live page can help users adjust framing before recording a video for upload.
- If Gemini is unavailable, TrainUp uses deterministic coaching feedback without failing the analysis.
- Kokoro TTS is generated only after the user clicks the listen control.
- TTS output may be cached for repeated playback.
- Sample test data may be used during local development to verify dashboard and analytics behaviour.
- Longer videos may require more processing time because the backend extracts frames, runs pose estimation, creates pose sequences, and evaluates movement.

## Git and Asset Hygiene

- `.env` files are ignored and must not be committed.
- API keys, secret keys, passwords, and database credentials must not be committed.
- Local model files and generated media/cache files should be ignored unless intentionally required.
- Drill demo videos under `frontend/public/videos/drills/*.mp4` may be intentionally tracked if they are part of the demo.
- MediaPipe browser assets under `frontend/public/mediapipe` may be intentionally tracked if required for live preview.
- Keep `.env.example` updated so the project can be reproduced without exposing private credentials.

## Responsible AI and Ethics

TrainUp prioritises explainability by keeping deterministic evaluation and deterministic coaching feedback as the source of truth. Gemini refinement is bounded to language improvement and cannot create new scores, movement faults, severity levels, diagnoses, or unsupported body-mechanics claims.

The system does not provide medical diagnosis, does not assess injuries, does not replace professional coaching, does not clone voices, and does not require user voice uploads. User-facing claims should remain aligned with validated system capability.

Privacy-sensitive data should be handled carefully in any deployment. Uploaded videos are processed temporarily for pose extraction and are not retained by default. A production version should include explicit consent, retention settings, deletion workflows, data export, access monitoring, and clear privacy notices.

## Known Limitations

- Pose accuracy depends on lighting, camera angle, framing, occlusion, and full-body visibility.
- 2D pose estimation cannot fully measure depth, physical force, pressure, load, ball contact, or true 3D movement.
- The current drill catalogue is limited to selected representative drills.
- Movement thresholds are heuristic prototype thresholds and require expert-labelled validation.
- Live camera support is currently preview and capture guidance, not saved backend analysis.
- Kokoro TTS may take time to load depending on runtime resources.
- Local Docker deployment is suitable for academic demonstration but not equivalent to production deployment.
- Production deployment would require stronger privacy, monitoring, scaling, backup, and security controls.

## Future Work

- Expand the drill catalogue and add more sports.
- Add automatic video quality checking before analysis.
- Conduct real-user evaluation with athletes, students, and coaches.
- Validate movement thresholds against expert-labelled videos.
- Improve mobile capture and device-specific calibration.
- Implement persisted live `pose_sequence` capture before offering saved backend analysis from live sessions.
- Add a coach or admin dashboard for group progress review.
- Improve progress analytics with goals, comparisons, and personalised training plans.
- Strengthen privacy controls, including consent, retention, deletion, and data export.
- Explore cloud deployment with secure hosting, monitoring, and database backup.
- Add more automated frontend and backend tests.

## Academic Disclaimer

TrainUp is an academic MVP developed for bachelor project demonstration. It provides educational coaching support only. It should not be used for medical diagnosis, injury assessment, rehabilitation decisions, professional sports certification, or high-stakes coaching decisions.

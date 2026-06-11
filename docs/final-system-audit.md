# TrainUp Final System Audit

Date: 2026-05-23

## Executive Summary

TrainUp is suitable for an upload-first academic MVP demonstration when presented as a pose-based coaching prototype with deterministic scoring as the source of truth. The strongest validated flow is:

Profile setup -> sport and drill selection -> drill preview -> uploaded-video session -> MediaPipe pose extraction -> uploaded pose overlay -> deterministic evaluation -> advanced reasoning context -> deterministic/Gemini-refined coaching -> click-to-play Kokoro TTS -> progress analytics.

The system should not be presented as a clinically validated biomechanics engine, medical assessment tool, or production privacy architecture. It uses 2D pose landmarks, heuristic drill-specific thresholds, deterministic feedback, optional Gemini wording refinement from compact summaries, and optional Kokoro audio delivery of the visible coaching text.

No high-risk architectural changes were made during this audit. Low-risk fixes were limited to misleading labels, stale placeholder documentation, and visible debug/demo wording.

## Validation Results

Commands run:

- `git status --short`: worktree contains pre-existing modified files plus this final audit document.
- `npm run typecheck` from `frontend`: passed.
- `npm run lint` from `frontend`: passed with no ESLint warnings or errors.
- `backend/.venv/bin/python -m pytest backend/tests`: initial sandboxed run could not connect to local Postgres; rerun with local DB access passed with 232 passed, 3 skipped, and 298 warnings.
- `docker compose config`: valid.
- `docker compose config --quiet`: passed.
- `docker compose ps`: frontend, backend, and Postgres containers were running; Postgres reported healthy.
- `curl -s http://127.0.0.1:8000/api/health`: returned `{"status":"ok"}`.

Additional validation notes:

- The full Compose render included values from the local ignored `backend/.env`. Git tracking was checked separately; `.env`, `backend/.env`, and `frontend/.env.local` are ignored and not tracked.
- A destructive or data-mutating live Docker upload/analyze/TTS smoke test was not run because it would require known seeded credentials and sample media. The backend suite covers upload persistence, analysis artifacts, progress aggregation, LLM fallback behavior, and TTS segment/caching logic.

## User Flow Assessment

Audited routes and flows:

- `/`: landing/application entry.
- `/signup` and `/login`: authentication.
- `/profile`: athlete profile and preferred sport setup.
- `/dashboard`: home/dashboard summary.
- `/sports` and `/sports/[sportId]/drills`: sport and drill selection.
- `/drills/[drillId]`: drill preview, reference demo, camera guidance, and session launch.
- `/sessions/new`: compatibility/new-session fallback.
- `/sessions/[sessionId]/upload`: persisted backend analysis path.
- `/sessions/[sessionId]/live`: browser-side live pose preview and readiness scaffold.
- `/progress`: weekly, monthly, and all-time progress analytics.

Assessment:

- Navigation is coherent for the upload-first demo path.
- Upload sessions expose appropriate loading, warning, error, and post-analysis states.
- Results scroll to the results panel after analysis completes or fails.
- Start New Session returns to the drill flow without deleting history.
- Live camera capture now avoids promising backend analysis unless a persisted `pose_sequence` exists.
- Mobile/local-network behavior is supported by dynamic API origin resolution when no explicit API URL override is configured, but was not device-lab validated during this audit.

## Layer-By-Layer Audit

### Perception Layer

Strengths:

- MediaPipe pose extraction is isolated in the backend perception service for uploaded media.
- Uploaded sessions persist normalized landmarks, timestamps, validity flags, preprocessing metadata, pose-cache metadata, and capture validation results.
- `POSE_TARGET_FPS=20`, `POSE_MAX_WIDTH=720`, and pose-cache behavior are implemented through configuration.
- Uploaded-video overlay uses timestamp-based pose lookup, interpolation, and tolerance logic instead of frame-index assumptions.
- Live preview uses browser-side MediaPipe Tasks Vision and does not send raw camera frames to Gemini.
- Low-visibility and missing-landmark conditions are surfaced through warnings and metric computability checks.

Risks:

- 2D pose cannot reliably infer pressure, load, true 3D rotation, ball contact, equipment contact, or calibrated joint depth.
- Overlay quality depends on encoding, lighting, full-body framing, camera angle, and landmark visibility.
- Live capture currently does not persist a backend `pose_sequence`; therefore full deterministic backend analysis is not available from the live path in this MVP.
- `POSE_TARGET_FPS=20` improves temporal density but increases extraction cost, making cache reuse important for repeated demos.
- Camera-angle limitations are documented but still rely on users following capture guidance.

### Cognition Layer

Strengths:

- Deterministic evaluation remains the authoritative scoring layer.
- Drill-specific metrics cover Bodyweight Squat, Dumbbell Shoulder Press, Set Shot Form, Defensive Stance, Instep Pass, and Basic Shooting Form.
- `squat_depth` is present as an explicit Bodyweight Squat metric.
- Multi-rep/set evaluation supports rep-cycle segmentation, single-cycle fallback, per-rep evaluation, and set-level aggregation.
- Defensive Stance supports small-motion athletic clips while rejecting fully static clips.
- Fuzzy, IT2 fuzzy, pedagogical, ontology, Choquet, and temporal layers add interpretation context without replacing deterministic scores.
- Reanalysis cleanup removes stale downstream artifacts and progress history before regeneration.

Risks:

- Thresholds are heuristic prototype thresholds, not externally validated sport-science cutoffs.
- Some sport concepts are proxies because ball/equipment contact is not directly observed.
- Segmentation may fall back or fail under unusual pacing, occlusion, camera shake, or limited motion.
- Diagnostic `NOT_COMPUTABLE` metrics can influence severity while being skipped from primary coaching feedback; this should be explained as a data-quality signal, not as a movement fault by itself.
- Legacy cognition scaffold files and old Gemini JSON parsing helpers remain for regression history and tests; they should not be described as the active runtime path.

### Action Layer

Strengths:

- Deterministic feedback is grounded in deterministic evaluation issues.
- The results UI presents one Primary Performance Focus and collapses secondary observations.
- Coaching wording uses professional labels and avoids casual or diagnostic language.
- TTS reads concise final coaching segments and is user-triggered.
- Gemini receives compact deterministic and advanced-reasoning summaries only, and deterministic feedback remains available if Gemini is unavailable.
- Kokoro TTS is cached by session/text/model/voice/pause configuration; TTS failure does not block analysis results.

Risks:

- Gemini availability depends on external API configuration and network availability.
- Kokoro first-use latency can be noticeable if the model has not warmed up.
- Secondary observations are intentionally compact, so users needing detail should review metric and advanced-analysis panels.

## Frontend UX Audit

Strengths:

- Dashboard and Progress pages distinguish recent sessions from weekly, monthly, and all-time aggregate counts.
- Drill cards are compact and scannable with stable actions.
- Drill previews include reference demos and setup guidance.
- Upload results, coaching feedback, and performance overview are organized for a single-session demo.
- The live camera page now clearly presents preview/readiness behavior rather than complete backend analysis.
- Placeholder module README files were replaced with project-specific descriptions.

Remaining UX risks:

- Browser camera permission, fullscreen behavior, and MediaPipe Tasks Vision support vary by device.
- Mobile responsiveness is reasonable from code/layout inspection but was not exhaustively tested across devices.
- Live preview should be introduced verbally as a scaffold, not the primary analysis path.

## Backend, API, And Data Audit

Strengths:

- API routes are domain-grouped and protected by current-user dependencies.
- Session ownership filtering is applied through session service/repository access.
- Upload processing persists artifacts and clears stale downstream outputs when reprocessing.
- Progress records are produced after completed deterministic evaluation/feedback, not after upload alone.
- Progress APIs support weekly, monthly, and all-time ranges.
- Health endpoint is available and returned healthy from the running Docker backend.
- Docker Compose configuration is syntactically valid.

Risks:

- `backend/scripts/seed_demo_athlete.py` contains synthetic local demo data generation and should not be presented as validation evidence.
- Local ignored environment files can contain real API keys and appear in full `docker compose config` output; do not paste full rendered configs into public reports.
- Docker CORS is permissive for demo convenience and should be tightened before production.
- Production retention, export, deletion, and audit-log workflows are not implemented.

## Documentation Readiness

Strengths:

- README states deterministic evaluation/feedback as the source of truth.
- README describes Gemini as optional wording refinement and Kokoro as audio delivery only.
- README and `docs/evaluation-audit.md` clarify that persisted backend analysis is upload-based, while live capture is browser preview/readiness scaffolding.
- `docs/evaluation-audit.md` documents metrics, thresholds, set aggregation, validation coverage, and limitations.
- This final audit document records validation outcomes and remaining limitations.

Remaining documentation risks:

- Final report language must not imply clinical validation, injury diagnosis, production privacy compliance, or complete live backend analysis.
- Synthetic/demo seed data must not be cited as empirical validation.
- Any demo instructions should identify upload-video analysis as the reliable primary path.

## Security, Privacy, And Ethics Audit

Verified boundaries:

- `.env`, `backend/.env`, and `frontend/.env.local` are ignored by Git and were not tracked.
- Git currently tracks `.env.example` and `docker-compose.yml`, not local secret files.
- Gemini receives compact summaries, not raw video, full pose sequences, or raw landmark streams.
- Kokoro TTS does not require user voice upload and does not perform voice cloning.
- README states non-medical and responsible-AI boundaries.
- Uploaded raw video bytes are discarded after pose extraction completes.

Risks:

- Any real API key present in a local ignored environment file should still be treated as sensitive and rotated if it was ever shared outside the local machine.
- The application is an MVP and lacks production-grade privacy controls, retention controls, consent workflows, and data export/deletion flows.

## Bugs And Issues Found

Low-risk issues fixed:

- Live camera copy incorrectly implied Analyze Performance became available after stopping capture; it now directs users to upload video for persisted backend analysis.
- Live camera capture status used stale "rep" wording; it now uses "set" wording.
- The pose overlay component defaulted visible debug markers/logging on; debug overlay is now opt-in through the prop.
- Placeholder module README files were replaced with project-specific documentation.

Issues flagged but not fixed because they are architectural or higher risk:

- Persisted backend analysis for live camera sessions is not implemented.
- Thresholds and scoring philosophy are heuristic and were not tuned during this audit.
- Legacy cognition scaffold files and old Gemini JSON parsing helpers remain because tests and history still reference them.
- Production CORS, privacy controls, and data lifecycle controls need future work.

## Demo Readiness Verdict

Demo-ready with these boundaries:

- Use upload-video analysis as the primary demo flow.
- Present live camera as browser-side pose preview/readiness scaffolding only.
- Present deterministic scoring as interpretable prototype logic, not validated biomechanics.
- Present Gemini as optional wording refinement and Kokoro as optional click-to-play audio.

The demo is not ready to be presented as:

- Clinically validated movement analysis.
- Medical diagnosis or injury-risk assessment.
- Production deployment with complete privacy controls.
- Complete live camera backend analysis.

## Documentation Readiness Verdict

Documentation is ready for an academic MVP submission if the final report preserves the current boundaries:

- Deterministic evaluation and deterministic coaching are the source of truth.
- Advanced reasoning layers provide interpretation context.
- Gemini does not create scores or new facts.
- Kokoro only reads final coaching text.
- Evaluation remains limited by 2D pose, camera quality, and heuristic thresholds.
- Synthetic local demo data is not validation evidence.

## Recommended Future Work

- Implement persisted live `pose_sequence` capture if live backend analysis is required.
- Validate thresholds against expert-labeled real-user video.
- Add stronger camera-angle and full-body quality estimation before analysis.
- Expand production privacy controls, retention policy, consent, and deletion/export workflows.
- Tighten production CORS, secret management, and deployment configuration.
- Archive or remove legacy cognition scaffolding after confirming it is no longer needed by tests or report history.
- Replace internal synthetic demo seeding with sanitized sample-data generation if public sample data is needed.

# TrainUp Evaluation Correctness Audit

Date: 2026-05-14

This audit reviews the current TrainUp movement-analysis pipeline as an interpretable prototype. The system uses rule-based evaluation over 2D MediaPipe landmarks, followed by advanced reasoning layers and optional LLM wording refinement. It should not be presented as clinically validated biomechanics or medical diagnosis.

## Pipeline Overview

1. Upload capture produces video frames for persisted backend analysis. Live capture currently provides browser-side pose overlay/readiness scaffolding and does not yet persist a backend `pose_sequence`.
2. `PerceptionService` extracts an uploaded-video `pose_sequence` with MediaPipe Pose landmarks, frame timestamps, validity flags, and preprocessing metadata.
3. `SessionService.evaluate_session` loads the `pose_sequence`, normalizes left sagittal views into the canonical right-facing orientation, auto-detects dominant side when needed, and calls `Phase2AEvaluator`.
4. `Phase2AEvaluator` attempts deterministic rep-cycle segmentation. When multiple confident cycles are detected, it evaluates each cycle independently, aggregates set-level scores, and persists backward-compatible `evaluation_result` metadata. When rep detection is weak, it falls back to the existing single dominant-cycle phase evaluation.
5. Fuzzy interpretation converts metric scores into linguistic movement severity.
6. IT2 fuzzy interpretation adds uncertainty around fuzzy labels.
7. Deterministic feedback selects actionable issues from the evaluation result. This is the user-facing source of truth.
8. Pedagogical decision adjusts coaching style and intensity from deterministic feedback plus available fuzzy context.
9. Ontology reasoning maps issues to movement concepts, body regions, and related concepts.
10. Choquet aggregation groups linked issues and interaction effects.
11. Temporal modeling summarizes motion timing, control, and phase pacing from pose and evaluation artifacts.
12. Gemini refinement may improve wording only. It must not invent issues, override scores, or replace deterministic evaluation.
13. Kokoro TTS speaks final coaching text only.

## Global Evaluation Rules

- Valid landmarks require visibility of at least `0.50`.
- Metrics with missing landmarks or unusable frames return `NOT_COMPUTABLE`.
- Diagnostic `NOT_COMPUTABLE` issues are not selected as primary feedback.
- Scores are normalized where `1.0` is best and `0.0` is worst.
- Closed-range metrics use `ideal_min..ideal_max`, normally with `ideal_max = 1.0`.
- Severity uses deviation from the target range:
  - `MINOR` when deviation is below the skill-adjusted moderate threshold.
  - `MODERATE` when deviation reaches the skill-adjusted moderate threshold.
  - `SEVERE` when deviation reaches the skill-adjusted severe threshold.
- Skill strictness factors:
  - Beginner: `1.25`, more tolerant.
  - Intermediate: `1.00`.
  - Advanced: `0.75`, stricter.
- Phase scores and overall score are currently unweighted means of computed metric scores.

## Pose Extraction And Pose Sequence

MediaPipe Pose returns normalized `x`, `y`, and `visibility` values. TrainUp stores those normalized landmarks and keeps original timestamps. The perception layer downsamples high-FPS videos for speed, resizes inference frames without changing stored video, and caches pose extraction by video hash and settings.

Known pose-layer limitations:

- This is a 2D landmark system. Depth, camera perspective, occlusion, and lens angle affect measurements.
- No ball, dumbbell, or floor contact object is detected.
- Metrics infer skill quality from body landmarks only.
- Side-specific football/basketball actions depend on dominant-side resolution and visible limbs.
- Low visibility, partial body framing, or short clips can produce missing metrics or poor segmentation.

## Phase Segmentation Audit

The segmentation layer is deterministic and drill-specific. It uses observable body-landmark motion rather than recognizing external events such as ball contact.

| Drill | Segmentation driver | Current audit verdict |
| --- | --- | --- |
| Bodyweight Squat | Bilateral knee-angle drop and bottom position | Reasonable for visible dynamic squats; explicit depth is now scored from the deepest bilateral knee-angle proxy |
| Dumbbell Shoulder Press | Bilateral wrist vertical motion and lockout height | Reasonable for frontal press clips with visible wrists; poor if wrists leave frame |
| Set Shot Form | Dominant wrist vertical motion | Reasonable for visible shooting-arm motion; lower-body timing is not explicitly segmented |
| Defensive Stance | Bilateral knee-angle drop into low stance and recovery | Supports smaller athletic stance movement after lowering the minimum knee-angle motion threshold; still rejects fully static clips |
| Instep Pass | Kicking knee angle plus kicking/support ankle proximity | Prototype-level proxy because ball contact is not observed |
| Basic Shooting Form | Kicking knee angle plus ankle/contact proxy | Prototype-level proxy because ball and goal contact are not observed |

Short clips, low-motion clips, and clips with missing phase-defining landmarks can fail segmentation or create phase windows that do not match the actual movement. This pass changed only the Defensive Stance minimum motion thresholds to support small athletic movement; other segmentation strategies were left unchanged.

## Threshold Reasonability Summary

The current thresholds are internally consistent for a prototype:

- Ideal minimums mostly sit between `0.76` and `0.84`, with the conservative new squat-depth proxy at `0.70` to avoid over-penalizing beginner range of motion from noisy 2D landmarks.
- Moderate deviations are usually `0.07..0.10`.
- Severe deviations are usually `0.16..0.22`.
- Beginner/advanced strictness adjusts those thresholds without changing the raw metric formula.

The thresholds are not yet empirically validated against a labeled dataset of good and bad real-user videos. They should be described as heuristic, interpretable thresholds rather than validated sport-science cutoffs.

## Drill Audit Summary

### Bodyweight Squat

Expected camera angle: `RIGHT_SAGITTAL`, with `LEFT_SAGITTAL` normalized to the right-facing canonical view.

Tracked landmarks: shoulders, hips, knees, ankles.

Phases: `setup`, `descent`, `ascent`.

Phase segmentation: average bilateral knee angle is computed across valid frames. The first valid frame starts the motion, the minimum average knee angle marks the bottom, and the setup/descent boundary is the first pre-bottom frame whose knee angle drops materially from setup. A minimum knee-angle motion delta of `3 deg` is required.

Metrics:

| Phase | Metric | Formula intent | Ideal min | Moderate | Severe |
| --- | --- | --- | ---: | ---: | ---: |
| setup | posture_accuracy | Torso lean near `12 deg`, denominator `30 deg` | 0.82 | 0.08 | 0.18 |
| descent | knee_alignment_score | Bilateral knee x-position relative to hip/ankle line | 0.78 | 0.08 | 0.18 |
| descent | squat_depth | Deepest bilateral knee-angle depth proxy; `115 deg` or lower scores best, `165 deg` is shallow | 0.70 | 0.12 | 0.25 |
| descent | torso_alignment | Torso-lean standard deviation, denominator `15 deg` | 0.80 | 0.08 | 0.18 |
| descent | hip_stability | Mid-hip lateral x range, denominator `0.12` | 0.76 | 0.09 | 0.20 |
| ascent | repetition_consistency | Left/right knee-angle symmetry during ascent, denominator `35 deg` | 0.80 | 0.08 | 0.18 |
| ascent | torso_alignment | Torso-lean standard deviation, denominator `15 deg` | 0.80 | 0.08 | 0.18 |

Good-form expectation: a stable, symmetric squat with visible full body, consistent torso lean, centered hips, and matching knee paths should score medium-high to high.

Bad-form detection:

- Knee collapse can be detected by `knee_alignment_score`.
- Shallow or partial range of motion can be detected by `squat_depth`.
- Excessive torso motion can be detected by `torso_alignment`; broken starting posture can be detected by `posture_accuracy`.
- Lateral hip shift can be detected by `hip_stability`.
- Uneven left/right ascent can be detected by `repetition_consistency`.

Important finding: `repetition_consistency` is a legacy metric id. The current formula measures bilateral knee-angle symmetry in the ascent, not consistency across multiple reps. A single clean rep should not be penalized solely because there is only one rep; it should score well when left and right knee angles match. Tests now cover this behavior. The deterministic feedback text and seed coaching rule were corrected to describe left/right ascent symmetry.

Depth metric note: `squat_depth` is intentionally conservative. It uses the deepest average knee angle in the descent phase as a 2D proxy for range of motion. This catches clear shallow squats without requiring 3D hip-depth estimation. It should still be validated against real camera footage before being treated as a sport-science cutoff.

### Dumbbell Shoulder Press

Expected camera angle: `FRONTAL`.

Tracked landmarks: shoulders, elbows, wrists, hips.

Phases: `setup`, `press`, `lockout`, `return`.

Phase segmentation: bilateral wrist y-position is used to find the overhead lockout. Setup, press, lockout, and return boundaries are derived from wrist motion and fallback fractions. Minimum wrist motion delta is `0.03`.

Metrics:

| Phase | Metric | Formula intent | Ideal min | Moderate | Severe |
| --- | --- | --- | ---: | ---: | ---: |
| setup | posture_accuracy | Torso lean near `4 deg`, denominator `18 deg` | 0.83 | 0.08 | 0.18 |
| press | elbow_extension | Bilateral elbow angle near `145 deg`, denominator `55 deg` | 0.78 | 0.09 | 0.20 |
| press | wrist_elbow_alignment | Wrist-over-elbow x alignment, denominator `0.12` | 0.80 | 0.08 | 0.18 |
| press | torso_alignment | Torso-lean standard deviation, denominator `10 deg` | 0.82 | 0.08 | 0.18 |
| lockout | lockout_control | Elbow angle near `168 deg` plus wrist-height stability | 0.82 | 0.08 | 0.18 |
| lockout | shoulder_symmetry | Shoulder and wrist height symmetry, denominator `0.10` | 0.80 | 0.08 | 0.18 |
| return | wrist_elbow_alignment | Wrist-over-elbow x alignment, denominator `0.12` | 0.78 | 0.09 | 0.20 |
| return | torso_alignment | Torso-lean standard deviation, denominator `10 deg` | 0.82 | 0.08 | 0.18 |

Good-form expectation: a vertical, symmetric press with controlled lockout and quiet torso should score high.

Bad-form detection:

- Uneven arms can be detected by `shoulder_symmetry`.
- Poor lockout can be detected by `lockout_control`.
- Hand path drift can be detected by `wrist_elbow_alignment`.
- Back arch is partially represented by setup posture and torso-lean variability, but a constant arched posture may be under-detected.

### Set Shot Form

Expected camera angle: `FRONTAL`.

Tracked landmarks: shoulders, elbows, wrists, hips, knees, ankles.

Phases: `setup`, `load`, `release`, `follow_through`.

Phase segmentation: dominant wrist y-position drives load and release detection. The highest/lowest wrist positions identify load/release timing.

Metrics:

| Phase | Metric | Formula intent | Ideal min | Moderate | Severe |
| --- | --- | --- | ---: | ---: | ---: |
| setup | posture_accuracy | Torso lean near `8 deg`, denominator `28 deg` | 0.83 | 0.08 | 0.18 |
| setup | balance_stability | Mid-hip lateral x range, denominator `0.09` | 0.79 | 0.09 | 0.20 |
| load | elbow_angle_consistency | Dominant elbow angle near `90 deg`, denominator `50 deg` | 0.80 | 0.08 | 0.18 |
| load | shooting_alignment | Shoulder-elbow-wrist x-line alignment | 0.84 | 0.07 | 0.16 |
| release | shooting_alignment | Shoulder-elbow-wrist x-line alignment | 0.84 | 0.07 | 0.16 |
| release | shoulder_control | Dominant shoulder over dominant hip, denominator `0.18` | 0.81 | 0.08 | 0.18 |
| follow_through | elbow_angle_consistency | Dominant elbow angle near `165 deg`, denominator `45 deg` | 0.80 | 0.08 | 0.18 |
| follow_through | balance_stability | Mid-hip lateral x range, denominator `0.09` | 0.79 | 0.09 | 0.20 |

Good-form expectation: a balanced set shot with aligned shooting arm, controlled shoulder position, and extended follow-through should score high.

Bad-form detection:

- Poor elbow or wrist line can be detected by `shooting_alignment`.
- Incomplete follow-through can be detected by follow-through `elbow_angle_consistency`.
- Balance drift can be detected by `balance_stability`.

Known limitation: knee drive is referenced in product coaching language but is not directly scored by a knee-drive metric in the current evaluator.

### Defensive Stance

Expected camera angle: `FRONTAL`.

Tracked landmarks: shoulders, hips, knees, ankles.

Phases: `setup`, `hold`, `recovery`.

Phase segmentation: average bilateral knee angle identifies the low stance frame and recovery. A minimum knee-angle motion delta of `1.5 deg` is required after the small-motion robustness update.

Metrics:

| Phase | Metric | Formula intent | Ideal min | Moderate | Severe |
| --- | --- | --- | ---: | ---: | ---: |
| setup | stance_width_control | Ankle-width to shoulder-width ratio near `1.30` | 0.81 | 0.08 | 0.18 |
| setup | posture_accuracy | Torso lean near `14 deg`, denominator `25 deg` | 0.80 | 0.09 | 0.20 |
| hold | knee_flexion | Bilateral knee angle near `115 deg`, denominator `45 deg` | 0.80 | 0.08 | 0.18 |
| hold | stance_width_control | Ankle-width to shoulder-width ratio near `1.30` | 0.82 | 0.08 | 0.18 |
| hold | hip_level_stability | Left/right hip height difference, denominator `0.08` | 0.80 | 0.08 | 0.18 |
| hold | torso_alignment | Torso-lean standard deviation, denominator `10 deg` | 0.81 | 0.08 | 0.18 |
| recovery | balance_stability | Mid-hip lateral x range, denominator `0.10` | 0.80 | 0.08 | 0.18 |
| recovery | knee_flexion | Bilateral knee angle near `135 deg`, denominator `55 deg` | 0.78 | 0.09 | 0.20 |

Good-form expectation: a stable athletic stance with correct stance width, loaded knees, level hips, and quiet torso should score high.

Bad-form detection:

- Too upright can be detected by `knee_flexion`.
- Too narrow or too wide stance can be detected by `stance_width_control`.
- Hip drop and torso movement can be detected by `hip_level_stability` and `torso_alignment`.

Segmentation update: the minimum knee-angle motion threshold was lowered from `3.0 deg` to `1.5 deg`, and the boundary delta from `5.0 deg` to `1.5 deg`, so subtle defensive bounce or controlled micro-adjustment can segment successfully. Fully static clips with no meaningful knee-angle change are still rejected.

### Instep Pass

Expected camera angle: `RIGHT_SAGITTAL`, with `LEFT_SAGITTAL` also allowed.

Tracked landmarks: shoulders, hips, knees, ankles.

Phases: `setup`, `backswing`, `contact`, `follow_through`.

Phase segmentation: dominant kicking knee angle and kicking/support ankle positions are used to infer backswing and contact.

Metrics:

| Phase | Metric | Formula intent | Ideal min | Moderate | Severe |
| --- | --- | --- | ---: | ---: | ---: |
| setup | plant_foot_alignment_ratio | Support ankle offset from hip midpoint relative to shoulder width, target `0.55` | 0.78 | 0.09 | 0.20 |
| backswing | instep_backswing_knee_angle | Kicking knee angle near `95 deg`, denominator `45 deg` | 0.78 | 0.09 | 0.20 |
| contact | instep_contact_extension | Kicking knee angle near `160 deg`, denominator `35 deg` | 0.80 | 0.08 | 0.18 |
| contact | instep_torso_tilt | Torso lean near `10 deg`, denominator `25 deg` | 0.79 | 0.09 | 0.20 |
| follow_through | instep_follow_through_stability | Kicking ankle x/y range stability | 0.77 | 0.10 | 0.22 |

Good-form expectation: a stable plant foot, controlled backswing, extended contact, organized torso, and stable follow-through should score high.

Bad-form detection:

- Poor plant-foot location can be detected by `plant_foot_alignment_ratio`.
- Weak or poorly timed kicking-leg shape can be detected by backswing/contact knee-angle metrics.
- Falling away from the pass can be detected by `instep_torso_tilt`.

Known limitation: the ball is not detected. Contact and plant quality are inferred from body landmarks only.

### Basic Shooting Form

Expected camera angle: `RIGHT_SAGITTAL`, with `LEFT_SAGITTAL` also allowed.

Tracked landmarks: shoulders, hips, knees, ankles.

Phases: `setup`, `load`, `swing`, `contact`, `follow_through`.

Phase segmentation: kicking knee angle and support/kicking ankle positions infer load, swing, contact, and follow-through.

Metrics:

| Phase | Metric | Formula intent | Ideal min | Moderate | Severe |
| --- | --- | --- | ---: | ---: | ---: |
| setup | support_foot_distance_ratio | Support ankle offset relative to shoulder width, target `0.60` | 0.78 | 0.09 | 0.20 |
| load | shooting_knee_load | Kicking knee angle near `105 deg`, denominator `50 deg` | 0.78 | 0.09 | 0.20 |
| swing | shooting_swing_velocity | Kicking ankle displacement proxy against target `0.055` | 0.76 | 0.10 | 0.22 |
| contact | shooting_contact_extension | Kicking knee angle near `165 deg`, denominator `35 deg` | 0.80 | 0.08 | 0.18 |
| contact | support_foot_distance_ratio | Support ankle offset relative to shoulder width, target `0.60` | 0.78 | 0.09 | 0.20 |
| follow_through | torso_rotation_stability | Shoulder-hip x-offset standard deviation, denominator `0.08` | 0.78 | 0.09 | 0.20 |
| follow_through | shooting_balance | Hip and support-ankle x stability | 0.78 | 0.09 | 0.20 |

Good-form expectation: stable plant foot, clear leg load, accelerating swing, extended contact, and balanced follow-through should score high.

Bad-form detection:

- Poor plant-foot placement can be detected by `support_foot_distance_ratio`.
- Weak swing acceleration can be detected by `shooting_swing_velocity`.
- Poor contact extension can be detected by `shooting_contact_extension`.
- Excessive trunk movement can be detected by `torso_rotation_stability`.

Known limitation: there is no ball detection, goal target detection, or true 3D approach-angle estimate.

## Final Missing-Metric Audit

No additional metric was added after `squat_depth`. The final audit found candidate coaching indicators, but none met the same low-risk standard because they either require 3D/camera-calibrated interpretation, object/ball context, equipment visibility, or would duplicate an existing deterministic proxy. Preserving scoring stability is safer than adding speculative metrics before real-user validation.

| Drill | Current deterministic metrics | Major candidate indicator | Decision |
| --- | --- | --- | --- |
| Bodyweight Squat | `posture_accuracy`, `knee_alignment_score`, `squat_depth`, `torso_alignment`, `hip_stability`, `repetition_consistency` | Heel pressure / foot pressure distribution | Reject as too noisy. Pressure cannot be measured from 2D landmarks; the current depth, knee-tracking, torso, hip, and bilateral-ascent metrics cover the major visible squat-quality indicators. |
| Dumbbell Shoulder Press | `posture_accuracy`, `elbow_extension`, `wrist_elbow_alignment`, `torso_alignment`, `lockout_control`, `shoulder_symmetry` | Constant lumbar arch / core-bracing compensation | Document only. Existing setup posture and torso-alignment variability cover visible trunk drift, but true lumbar arch is not reliably visible from 2D frontal landmarks and dumbbell load is not observed. |
| Set Shot Form | `posture_accuracy`, `balance_stability`, `elbow_angle_consistency`, `shooting_alignment`, `shoulder_control` | Lower-body loading / knee-drive contribution | Document only. This is an important coaching concept, but the current frontal 2D pose does not distinguish useful knee load from noisy crouch depth robustly enough without camera calibration. |
| Defensive Stance | `stance_width_control`, `posture_accuracy`, `knee_flexion`, `hip_level_stability`, `torso_alignment`, `balance_stability` | Lateral reaction step quality | Reject as too noisy. Stance width, knee flexion, hip level, torso, and balance already cover visible stance quality; reaction-step quality needs intent/direction context and can be confused with camera jitter. |
| Instep Pass | `plant_foot_alignment_ratio`, `instep_backswing_knee_angle`, `instep_contact_extension`, `instep_torso_tilt`, `instep_follow_through_stability` | Ankle lock / true ball-contact point | Reject as too noisy. Ball contact and foot-surface orientation are not observed directly; adding a proxy would overstate what 2D landmarks can support. |
| Basic Shooting Form | `support_foot_distance_ratio`, `shooting_knee_load`, `shooting_swing_velocity`, `shooting_contact_extension`, `torso_rotation_stability`, `shooting_balance` | True approach angle / goal-facing swing line | Reject as too noisy. Current support-foot, load, swing, contact-extension, torso, and balance proxies are deterministic; true approach angle requires field/goal context or camera calibration. |

## Validation Matrix

| Drill | Good/clean expected outcome | Common bad-form case | Expected detection | Edge case |
| --- | --- | --- | --- | --- |
| Bodyweight Squat | High or medium-high score when torso, hips, depth, knee tracking, and left/right ascent symmetry are controlled | Shallow squat or knee valgus | `squat_depth` or `knee_alignment_score` below range | Single clean rep should not be punished by `repetition_consistency`; depth remains a 2D knee-angle proxy |
| Dumbbell Shoulder Press | High score when press path is vertical, lockout controlled, and arms symmetrical | Uneven arms | `shoulder_symmetry` or `lockout_control` below range | Constant back arch may be under-detected if torso lean does not vary |
| Set Shot Form | High score with aligned shooting arm and stable balance | Elbow/wrist off shot line | `shooting_alignment` below range | Knee drive is not directly measured |
| Defensive Stance | High score with loaded knees, stable width, level hips, quiet torso | Too upright | `knee_flexion` below range | Small athletic movement is supported; fully static no-motion clips are still rejected |
| Instep Pass | High score with stable plant, appropriate backswing/contact extension, and balanced follow-through | Poor plant foot | `plant_foot_alignment_ratio` below range | Ball contact is inferred, not observed |
| Basic Shooting Form | High score with stable support foot, clear load, swing, contact extension, and finish balance | Poor plant foot or trunk instability | `support_foot_distance_ratio` or `torso_rotation_stability` below range | No ball/goal context; swing velocity is an ankle-motion proxy |

## Set-Level Analysis Audit

Users can upload a set that contains one rep, multiple reps, partial reps, or repeated attempts. The evaluator now performs deterministic rep-cycle segmentation before the existing phase evaluator runs. This is a prototype set-level extension, not a learned rep counter.

Implemented behavior:

- A single valid rep falls back to the existing single dominant-cycle evaluation and is not penalized for lacking repeated reps.
- Multiple confident cycles are sliced from the existing `pose_sequence` and each cycle is evaluated independently with the same deterministic metric contracts.
- The final result remains backward-compatible and adds `detected_rep_count`, `evaluated_rep_count`, `rep_summaries`, and `set_level_summary` when available.
- Set-level aggregation reports average score, best score, worst score, consistency score, repeated issue metric ids, and the dominant recurring issue.
- Invalid or low-confidence cycles are excluded. If fewer than two cycles can be evaluated successfully, the evaluator falls back to the single dominant-cycle path.

Drill-specific deterministic cycle definitions:

- Bodyweight Squat: bilateral knee-angle peak-to-valley-to-peak cycle, representing setup/descent/ascent.
- Dumbbell Shoulder Press: bilateral wrist-height bottom-to-lockout-to-return cycle.
- Set Shot Form: dominant wrist release/follow-through cycle.
- Defensive Stance: meaningful knee-angle dip/recovery or stance-movement cycle; fully static clips are not treated as ideal cycles.
- Instep Pass: kicking-leg knee-angle load/contact/follow-through cycle.
- Basic Shooting Form: kicking-leg load/swing/contact/follow-through cycle.

Safety gates:

- Rep detection requires minimum motion amplitude, minimum frame spacing, local directional order, and valid landmark visibility.
- Plateau-style top or bottom positions are supported by a balanced local prominence window so held positions do not suppress cycle detection.
- Low-motion jitter is rejected by amplitude checks and does not create fake repetitions.
- Single-rep uploads remain valid and receive `evaluation_mode="single_cycle"`.
- Multi-rep uploads receive `evaluation_mode="multi_rep"` only when at least two detected cycles complete evaluation successfully.

Set-level consistency:

- `consistency_score` combines overall score variation and per-metric normalized-score variation across reps.
- A single poor rep inside an otherwise stronger set produces a consistency warning instead of catastrophically lowering the overall set verdict.
- Repeated moderate/severe issues across reps are surfaced as recurring set-level issues.

## Synthetic Test Findings

The existing Phase 2A tests verify pipeline coverage, response shape, persistence, segmentation registry coverage, and calculator registry coverage for all six drills. They should not be interpreted as proof that the synthetic "happy path" poses are biomechanically ideal. Several existing fixture sequences produce severe issues because their purpose is stable contract execution rather than clean-form validation.

Additional tests were added or updated to cover:

- Bodyweight Squat `repetition_consistency` as bilateral ascent symmetry, including a single-rep case.
- Bodyweight Squat `squat_depth`, including good depth versus shallow depth and missing-landmark handling.
- Defensive Stance small-motion segmentation, including fully static clip rejection.
- Cross-drill common metric formulas where intentionally good synthetic inputs score above intentionally bad synthetic inputs.
- Deterministic feedback wording for Bodyweight Squat `repetition_consistency` and `squat_depth`.
- Single-rep squat fallback metadata without a consistency penalty.
- Multi-rep squat aggregation across three detected reps.
- A shallow squat rep inside an otherwise stronger set producing a set-level consistency warning.
- Dumbbell Shoulder Press multi-rep detection and aggregation.
- Defensive Stance multi-cycle detection and aggregation.
- Noisy low-motion squat input avoiding false rep hallucination.
- Deterministic feedback summary wording that describes performance across the set.

## Issues Found

Low-risk issue fixed:

- Bodyweight Squat `repetition_consistency` feedback wording described changing reps, but the formula measures left/right knee-angle mismatch during ascent. The deterministic feedback template and seed coaching rule now describe bilateral ascent symmetry.
- Bodyweight Squat now includes explicit `squat_depth` scoring and targeted deterministic feedback for shallow depth.
- Defensive Stance segmentation now accepts subtle athletic stance movement while still rejecting fully static no-motion clips.
- Deterministic rep-cycle segmentation and set-level aggregation were added while preserving the existing single-cycle fallback path.

High-risk changes intentionally avoided:

- No existing non-stance scoring thresholds were changed without real validation data.
- No additional non-squat sport metrics were added without validation. Set Shot lower-body loading, follow-through persistence, and football contact quality remain recommended future work rather than speculative scoring changes.
- No segmentation strategy was rewritten.
- No ML-based rep counter or hidden weighting layer was added.
- No Gemini, Kokoro TTS, progress, upload, live, or UI behavior was changed.

## Known Limitations

- The system is best described as rule-based evaluation using interpretable biomechanical indicators.
- Thresholds are prototype heuristics and require further real-user validation.
- 2D landmarks cannot fully capture depth, rotation, or load.
- Ball/equipment contact is inferred from body landmarks and not directly measured.
- Camera angle and body framing strongly affect reliability.
- Short clips, partial visibility, and low-confidence landmarks can produce invalid phases or `NOT_COMPUTABLE` metrics.
- Some seed descriptions mention coaching concepts that are not yet directly scored by a dedicated metric.
- Rep-cycle segmentation is deterministic and conservative; unusual pacing, occlusion, or camera shake can still trigger fallback to the single dominant-cycle path.
- Per-rep aggregation uses prototype heuristics and should be validated on real multi-rep user videos before being described as sport-science validated.

## Demo-Safety Verdict

Current outputs are demo-safe as an academic MVP prototype when described accurately:

- Deterministic evaluation is interpretable and bounded to configured metrics.
- The six implemented drills have explicit phase contracts and metric contracts.
- Feedback is generated from deterministic issues, not from LLM invention.
- Advanced layers add interpretation and coaching context, not raw scoring authority.
- The system should not be claimed to provide clinical-grade biomechanics, medical advice, or fully validated sport-science assessment.

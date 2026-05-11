from __future__ import annotations


def _capture_protocol(
    *allowed_camera_views: str,
    required: bool = True,
    canonical_view: str | None = None,
) -> dict[str, object]:
    return {
        "required": required,
        "allowed_camera_views": list(allowed_camera_views),
        "canonical_view": canonical_view or allowed_camera_views[0],
    }


def _target_metrics(*metrics: str) -> dict[str, list[str]]:
    return {"metrics": list(metrics)}


def _coaching_rules(
    primary_focus: list[str],
    rule_checks: list[dict[str, object]],
    positive_cues: list[str],
    recommendation_templates: list[str],
    thresholds: dict[str, float] | None = None,
) -> dict[str, object]:
    return {
        "primary_focus": primary_focus,
        "thresholds": thresholds or {"minor": 0.15, "moderate": 0.30, "severe": 0.45},
        "rule_checks": rule_checks,
        "positive_cues": positive_cues,
        "recommendation_templates": recommendation_templates,
    }


DRILL_DEMO_VIDEO_URLS_BY_NAME = {
    "Bodyweight Squat": "/videos/drills/bodyweight-squat.mp4",
    "Dumbbell Shoulder Press": "/videos/drills/dumbbell-shoulder-press.mp4",
    "Set Shot Form": "/videos/drills/set-shot-form.mp4",
    "Defensive Stance": "/videos/drills/defensive-stance.mp4",
    "Instep Pass": "/videos/drills/instep-pass.mp4",
    "Basic Shooting Form": "/videos/drills/basic-shooting-form.mp4",
}


DRILL_SEEDS_BY_SPORT = {
    "Gym": [
        {
            "drill_name": "Bodyweight Squat",
            "description": (
                "The bodyweight squat trains coordinated flexion through the hips, knees, and ankles "
                "while teaching the athlete to control depth without losing posture. "
                "It matters because squat mechanics underpin jumping, acceleration, deceleration, and lower-body strength work across sports. "
                "The drill emphasizes even knee tracking, centered foot pressure, and consistent torso position from rep to rep."
            ),
            "target_metrics": _target_metrics(
                "posture_accuracy",
                "knee_alignment_score",
                "torso_alignment",
                "hip_stability",
                "repetition_consistency",
            ),
            "reference_payload": {
                "capture_protocol": _capture_protocol(
                    "RIGHT_SAGITTAL",
                    "LEFT_SAGITTAL",
                    canonical_view="RIGHT_SAGITTAL",
                ),
                "movement_type": "dynamic",
                "phases": ["setup", "descent", "ascent"],
                "tracked_joints": ["shoulders", "hips", "knees", "ankles"],
                "ideal_ranges": {
                    "left_knee_angle": {"min": 78, "max": 108},
                    "right_knee_angle": {"min": 78, "max": 108},
                    "hip_hinge_angle": {"min": 45, "max": 70},
                    "torso_lean": {"min": 8, "max": 22},
                    "ankle_dorsiflexion": {"min": 10, "max": 20},
                },
                "stability_expectations": {
                    "lateral_sway_max": 0.12,
                    "tempo_consistency_min": 0.78,
                    "pelvic_shift_max": 0.10,
                },
                "notes": (
                    "Sit between the hips with the ribs stacked over the pelvis and keep the knees "
                    "tracking over the middle toes throughout the rep."
                ),
            },
            "coaching_rules": _coaching_rules(
                primary_focus=[
                    "knee tracking",
                    "torso alignment",
                    "hip stability",
                    "repeatable depth",
                ],
                rule_checks=[
                    {
                        "metric": "posture_accuracy",
                        "condition": "below_threshold",
                        "expected_min": 0.82,
                        "severity_weight": 0.88,
                        "issue_label": "Chest dropping early in the squat",
                        "coaching_cue": "Brace before you descend and keep your chest stacked over your hips.",
                    },
                    {
                        "metric": "knee_alignment_score",
                        "condition": "below_threshold",
                        "expected_min": 0.78,
                        "severity_weight": 0.93,
                        "issue_label": "Knees collapsing inward",
                        "coaching_cue": "Drive both knees over the middle toes and keep full-foot pressure.",
                    },
                    {
                        "metric": "torso_alignment",
                        "condition": "below_threshold",
                        "expected_min": 0.80,
                        "severity_weight": 0.84,
                        "issue_label": "Torso angle changing too much through the rep",
                        "coaching_cue": "Keep your ribs stacked and let the hips and knees share the load evenly.",
                    },
                    {
                        "metric": "hip_stability",
                        "condition": "below_threshold",
                        "expected_min": 0.76,
                        "severity_weight": 0.86,
                        "issue_label": "Hips shifting side to side",
                        "coaching_cue": "Descend evenly and keep your hips centered between your heels.",
                    },
                    {
                        "metric": "repetition_consistency",
                        "condition": "below_threshold",
                        "expected_min": 0.80,
                        "severity_weight": 0.74,
                        "issue_label": "Depth and tempo changing between repetitions",
                        "coaching_cue": "Use a steady tempo and finish every rep at the same controlled depth.",
                    },
                ],
                positive_cues=[
                    "Good control through the bottom position.",
                    "Your rep rhythm is staying consistent.",
                ],
                recommendation_templates=[
                    "Repeat the squat at a slower tempo and match the same depth on every rep.",
                    "Add a brief pause at the bottom to reinforce hip control and knee tracking.",
                ],
            ),
        },
        {
            "drill_name": "Dumbbell Shoulder Press",
            "description": (
                "The dumbbell shoulder press trains vertical pressing mechanics while challenging the athlete "
                "to stabilize through the trunk and shoulder girdle. "
                "It matters because safe overhead strength depends on stacked joints, controlled elbow travel, and the ability to resist compensation through the spine. "
                "The drill emphasizes smooth pressing paths, consistent lockout, and balance from the first rep to the last."
            ),
            "target_metrics": _target_metrics(
                "posture_accuracy",
                "elbow_extension",
                "wrist_elbow_alignment",
                "lockout_control",
                "shoulder_symmetry",
                "torso_alignment",
            ),
            "reference_payload": {
                "capture_protocol": _capture_protocol("FRONTAL"),
                "movement_type": "dynamic",
                "phases": ["setup", "press", "lockout", "return"],
                "tracked_joints": ["shoulders", "elbows", "wrists", "hips"],
                "ideal_ranges": {
                    "left_elbow_angle": {"min": 82, "max": 172},
                    "right_elbow_angle": {"min": 82, "max": 172},
                    "shoulder_abduction": {"min": 35, "max": 55},
                    "torso_lean": {"min": 0, "max": 10},
                    "press_path_deviation": {"min": 0, "max": 0.10},
                },
                "stability_expectations": {
                    "lateral_sway_max": 0.08,
                    "tempo_consistency_min": 0.76,
                    "lockout_hold_min": 0.20,
                },
                "notes": (
                    "Press the dumbbells vertically with elbows under wrists, shoulders controlled, "
                    "and the ribcage stacked over the pelvis."
                ),
            },
            "coaching_rules": _coaching_rules(
                primary_focus=[
                    "vertical press path",
                    "elbow stacking",
                    "shoulder control",
                    "trunk stability",
                ],
                rule_checks=[
                    {
                        "metric": "posture_accuracy",
                        "condition": "below_threshold",
                        "expected_min": 0.83,
                        "severity_weight": 0.82,
                        "issue_label": "Press initiated from a broken setup posture",
                        "coaching_cue": "Stand tall before pressing and keep your ribcage quiet as the weights move.",
                    },
                    {
                        "metric": "elbow_extension",
                        "condition": "below_threshold",
                        "expected_min": 0.78,
                        "severity_weight": 0.90,
                        "issue_label": "Elbows drifting out of a repeatable pressing path",
                        "coaching_cue": "Keep your elbows slightly in front of the shoulders and press straight up.",
                    },
                    {
                        "metric": "shoulder_symmetry",
                        "condition": "below_threshold",
                        "expected_min": 0.80,
                        "severity_weight": 0.92,
                        "issue_label": "Shoulders shrugging during the press",
                        "coaching_cue": "Set your shoulders down before each rep and finish with controlled upward rotation.",
                    },
                    {
                        "metric": "torso_alignment",
                        "condition": "below_threshold",
                        "expected_min": 0.82,
                        "severity_weight": 0.88,
                        "issue_label": "Lower back arching to finish the rep",
                        "coaching_cue": "Brace your trunk and keep your ribs stacked as you drive overhead.",
                    },
                    {
                        "metric": "lockout_control",
                        "condition": "below_threshold",
                        "expected_min": 0.82,
                        "severity_weight": 0.75,
                        "issue_label": "Weight rocking backward during the press",
                        "coaching_cue": "Stay rooted through the midfoot and squeeze the glutes to stay centered.",
                    },
                ],
                positive_cues=[
                    "The dumbbells are tracking vertically with good control.",
                    "Your lockout position looks stable and balanced.",
                ],
                recommendation_templates=[
                    "Reduce the load slightly and press with a slower tempo to reinforce elbow tracking.",
                    "Pause at forehead height to rehearse shoulder control before finishing overhead.",
                ],
            ),
        },
    ],
    "Football": [
        {
            "drill_name": "Instep Pass",
            "description": (
                "The instep pass trains clean ball striking mechanics for accurate, repeatable short-to-midrange passing. "
                "It matters because reliable passing depends on a quiet support leg, coordinated hip rotation, and a controlled follow-through rather than pure leg speed. "
                "The drill emphasizes plant-foot stability, balanced trunk position, and consistent contact through the center of the foot."
            ),
            "target_metrics": _target_metrics(
                "plant_foot_alignment_ratio",
                "instep_backswing_knee_angle",
                "instep_contact_extension",
                "instep_torso_tilt",
                "instep_follow_through_stability",
            ),
            "reference_payload": {
                "capture_protocol": _capture_protocol(
                    "RIGHT_SAGITTAL",
                    "LEFT_SAGITTAL",
                    canonical_view="RIGHT_SAGITTAL",
                ),
                "movement_type": "dynamic",
                "phases": ["setup", "backswing", "contact", "follow_through"],
                "tracked_joints": ["hips", "knees", "ankles", "shoulders"],
                "ideal_ranges": {
                    "plant_foot_alignment_ratio": {"min": 0.78, "max": 1.00},
                    "backswing_knee_angle_score": {"min": 0.78, "max": 1.00},
                    "contact_knee_extension_score": {"min": 0.80, "max": 1.00},
                    "torso_tilt_score": {"min": 0.79, "max": 1.00},
                    "follow_through_stability": {"min": 0.77, "max": 1.00},
                },
                "stability_expectations": {
                    "lateral_sway_max": 0.14,
                    "tempo_consistency_min": 0.74,
                    "plant_stability_min": 0.78,
                },
                "notes": (
                    "Plant beside the ball, rotate through the hips, and let the passing leg continue "
                    "toward the target without the torso falling away."
                ),
            },
            "coaching_rules": _coaching_rules(
                primary_focus=[
                    "support-leg stability",
                    "hip rotation timing",
                    "torso control",
                    "repeatable contact",
                ],
                rule_checks=[
                    {
                        "metric": "plant_foot_alignment_ratio",
                        "condition": "below_threshold",
                        "expected_min": 0.78,
                        "severity_weight": 0.80,
                        "issue_label": "Support foot is not set consistently beside the ball",
                        "coaching_cue": "Plant beside the ball before the swing leg accelerates.",
                    },
                    {
                        "metric": "instep_backswing_knee_angle",
                        "condition": "below_threshold",
                        "expected_min": 0.78,
                        "severity_weight": 0.91,
                        "issue_label": "Backswing knee flexion is outside the target window",
                        "coaching_cue": "Let the kicking knee fold naturally before driving through the ball.",
                    },
                    {
                        "metric": "instep_contact_extension",
                        "condition": "below_threshold",
                        "expected_min": 0.80,
                        "severity_weight": 0.88,
                        "issue_label": "Kicking leg is not extending cleanly at contact",
                        "coaching_cue": "Strike through the ball with a firm, extending leg.",
                    },
                    {
                        "metric": "instep_torso_tilt",
                        "condition": "below_threshold",
                        "expected_min": 0.79,
                        "severity_weight": 0.84,
                        "issue_label": "Torso leaning away from the pass line",
                        "coaching_cue": "Keep the sternum over the plant leg and finish the chest toward the target.",
                    },
                    {
                        "metric": "instep_follow_through_stability",
                        "condition": "below_threshold",
                        "expected_min": 0.77,
                        "severity_weight": 0.73,
                        "issue_label": "Follow-through path is unstable after contact",
                        "coaching_cue": "Finish the kicking leg through the target line without falling away.",
                    },
                ],
                positive_cues=[
                    "Your support leg is staying calm through contact.",
                    "The follow-through is matching the intended pass line.",
                ],
                recommendation_templates=[
                    "Slow the approach and rehearse planting beside the ball before increasing speed.",
                    "Repeat the pass with a shorter backswing and emphasize finishing through the target.",
                ],
            ),
        },
        {
            "drill_name": "Basic Shooting Form",
            "description": (
                "Basic shooting form trains the mechanics of generating a clean strike on goal with repeatable body shape and balance. "
                "It matters because finishing quality drops quickly when the plant foot, hip drive, and trunk position break down under speed. "
                "The drill emphasizes an organized approach, stable support-leg positioning, and a direct strike path through the ball."
            ),
            "target_metrics": _target_metrics(
                "support_foot_distance_ratio",
                "shooting_knee_load",
                "shooting_swing_velocity",
                "shooting_contact_extension",
                "torso_rotation_stability",
                "shooting_balance",
            ),
            "reference_payload": {
                "capture_protocol": _capture_protocol(
                    "RIGHT_SAGITTAL",
                    "LEFT_SAGITTAL",
                    canonical_view="RIGHT_SAGITTAL",
                ),
                "movement_type": "dynamic",
                "phases": ["setup", "load", "swing", "contact", "follow_through"],
                "tracked_joints": ["hips", "knees", "ankles", "shoulders"],
                "ideal_ranges": {
                    "support_foot_distance_ratio": {"min": 0.78, "max": 1.00},
                    "load_knee_flexion_score": {"min": 0.78, "max": 1.00},
                    "swing_velocity_proxy": {"min": 0.76, "max": 1.00},
                    "contact_leg_extension_score": {"min": 0.80, "max": 1.00},
                    "torso_rotation_stability": {"min": 0.78, "max": 1.00},
                    "follow_through_balance": {"min": 0.78, "max": 1.00},
                },
                "stability_expectations": {
                    "lateral_sway_max": 0.13,
                    "tempo_consistency_min": 0.72,
                    "plant_stability_min": 0.76,
                },
                "notes": (
                    "Use a composed approach, place the support foot beside the ball, and strike through "
                    "with the hips leading while the torso stays organized."
                ),
            },
            "coaching_rules": _coaching_rules(
                primary_focus=[
                    "approach posture",
                    "plant-foot alignment",
                    "hip drive",
                    "stable support leg",
                ],
                rule_checks=[
                    {
                        "metric": "support_foot_distance_ratio",
                        "condition": "below_threshold",
                        "expected_min": 0.78,
                        "severity_weight": 0.79,
                        "issue_label": "Support foot is not arriving at a repeatable striking distance",
                        "coaching_cue": "Set the support foot beside the ball before accelerating the kicking leg.",
                    },
                    {
                        "metric": "shooting_knee_load",
                        "condition": "below_threshold",
                        "expected_min": 0.78,
                        "severity_weight": 0.89,
                        "issue_label": "Kicking knee load is outside the target range",
                        "coaching_cue": "Load the kicking leg before the swing so the strike is not rushed.",
                    },
                    {
                        "metric": "shooting_swing_velocity",
                        "condition": "below_threshold",
                        "expected_min": 0.76,
                        "severity_weight": 0.92,
                        "issue_label": "Swing-leg acceleration proxy is too low",
                        "coaching_cue": "Accelerate the kicking ankle through the ball after the load phase.",
                    },
                    {
                        "metric": "shooting_contact_extension",
                        "condition": "below_threshold",
                        "expected_min": 0.80,
                        "severity_weight": 0.84,
                        "issue_label": "Kicking leg is not extended at contact",
                        "coaching_cue": "Drive through contact with the knee extending toward the target.",
                    },
                    {
                        "metric": "shooting_balance",
                        "condition": "below_threshold",
                        "expected_min": 0.78,
                        "severity_weight": 0.87,
                        "issue_label": "Balance is unstable after the strike",
                        "coaching_cue": "Finish on a stable support leg instead of drifting after contact.",
                    },
                ],
                positive_cues=[
                    "Your support leg is giving you a stable striking platform.",
                    "Hip drive is carrying through the ball cleanly.",
                ],
                recommendation_templates=[
                    "Rehearse the last two approach steps and the plant position before adding more pace.",
                    "Use a slower strike to clean up plant-knee alignment and torso position before increasing power.",
                ],
            ),
        },
    ],
    "Basketball": [
        {
            "drill_name": "Set Shot Form",
            "description": (
                "The set shot form drill trains a repeatable release pattern from a balanced base with the ball traveling on a straight line through the shooting pocket. "
                "It matters because consistent shot making depends on stacked joints, controlled elbow positioning, and a stable center of mass through release. "
                "The drill emphasizes alignment from feet to fingertips, smooth elbow extension, and quiet body balance."
            ),
            "target_metrics": _target_metrics(
                "shooting_alignment",
                "elbow_angle_consistency",
                "shoulder_control",
                "balance_stability",
                "posture_accuracy",
            ),
            "reference_payload": {
                "capture_protocol": _capture_protocol("FRONTAL"),
                "movement_type": "dynamic",
                "phases": ["setup", "load", "release", "follow_through"],
                "tracked_joints": ["shoulders", "elbows", "wrists", "hips", "knees", "ankles"],
                "ideal_ranges": {
                    "shooting_elbow_angle": {"min": 82, "max": 100},
                    "release_wrist_extension": {"min": 55, "max": 85},
                    "shoulder_stack_offset": {"min": 0, "max": 0.10},
                    "knee_flexion_at_set": {"min": 18, "max": 35},
                    "release_line_deviation": {"min": 0, "max": 0.08},
                },
                "stability_expectations": {
                    "lateral_sway_max": 0.09,
                    "tempo_consistency_min": 0.80,
                    "landing_balance_min": 0.82,
                },
                "notes": (
                    "Bring the ball through a straight shooting pocket, keep the elbow under the ball, "
                    "and hold balance through the follow-through."
                ),
            },
            "coaching_rules": _coaching_rules(
                primary_focus=[
                    "shot line alignment",
                    "elbow path",
                    "shoulder stack",
                    "stable release base",
                ],
                rule_checks=[
                    {
                        "metric": "shooting_alignment",
                        "condition": "below_threshold",
                        "expected_min": 0.84,
                        "severity_weight": 0.95,
                        "issue_label": "Ball path drifting off the shooting line",
                        "coaching_cue": "Start with the ball centered and release straight through the middle finger line.",
                    },
                    {
                        "metric": "elbow_angle_consistency",
                        "condition": "below_threshold",
                        "expected_min": 0.80,
                        "severity_weight": 0.90,
                        "issue_label": "Shooting elbow wandering away from a repeatable slot",
                        "coaching_cue": "Keep the elbow tucked under the ball and extend along the same path every rep.",
                    },
                    {
                        "metric": "shoulder_control",
                        "condition": "below_threshold",
                        "expected_min": 0.81,
                        "severity_weight": 0.86,
                        "issue_label": "Lead shoulder rotating open before release",
                        "coaching_cue": "Keep the shooting shoulder stacked to the rim until the ball leaves your hand.",
                    },
                    {
                        "metric": "balance_stability",
                        "condition": "below_threshold",
                        "expected_min": 0.79,
                        "severity_weight": 0.82,
                        "issue_label": "Base shifting during the set and release",
                        "coaching_cue": "Stay centered over both feet and finish with quiet balance on the release.",
                    },
                    {
                        "metric": "posture_accuracy",
                        "condition": "below_threshold",
                        "expected_min": 0.83,
                        "severity_weight": 0.78,
                        "issue_label": "Upper-body posture breaking before the shot",
                        "coaching_cue": "Keep your chest tall and eyes level from the catch into the follow-through.",
                    },
                ],
                positive_cues=[
                    "The shot line stays centered through release.",
                    "Your follow-through is balanced and repeatable.",
                ],
                recommendation_templates=[
                    "Pause at the set point and rehearse elbow-under-ball alignment before releasing.",
                    "Take a small step back in distance and focus on balance through the full follow-through.",
                ],
            ),
        },
        {
            "drill_name": "Defensive Stance",
            "description": (
                "Defensive stance trains the low, reactive base used to stay in front of an opponent without losing balance. "
                "It matters because defensive movement quality depends on consistent stance width, controlled knee bend, and the ability to shift laterally without popping upright. "
                "The drill emphasizes hip hinge discipline, even foot pressure, and stable torso position while holding or moving in stance."
            ),
            "target_metrics": _target_metrics(
                "stance_width_control",
                "knee_flexion",
                "hip_level_stability",
                "torso_alignment",
                "balance_stability",
                "posture_accuracy",
            ),
            "reference_payload": {
                "capture_protocol": _capture_protocol("FRONTAL"),
                "movement_type": "static",
                "phases": ["setup", "hold", "recovery"],
                "tracked_joints": ["hips", "knees", "ankles", "shoulders"],
                "ideal_ranges": {
                    "stance_width_ratio": {"min": 1.10, "max": 1.45},
                    "left_knee_flexion": {"min": 95, "max": 125},
                    "right_knee_flexion": {"min": 95, "max": 125},
                    "hip_hinge_angle": {"min": 18, "max": 35},
                    "torso_lean": {"min": 8, "max": 18},
                },
                "stability_expectations": {
                    "lateral_sway_max": 0.10,
                    "tempo_consistency_min": 0.82,
                    "weight_shift_max": 0.12,
                },
                "notes": (
                    "Hold a wide, loaded base with the hips back, knees bent, and the chest positioned "
                    "slightly forward without collapsing."
                ),
            },
            "coaching_rules": _coaching_rules(
                primary_focus=[
                    "stance width",
                    "knee bend quality",
                    "hip hinge",
                    "lateral balance",
                ],
                rule_checks=[
                    {
                        "metric": "stance_width_control",
                        "condition": "below_threshold",
                        "expected_min": 0.81,
                        "severity_weight": 0.90,
                        "issue_label": "Base width changing too much during the stance",
                        "coaching_cue": "Keep your feet just outside shoulder width and hold that spacing as you move.",
                    },
                    {
                        "metric": "knee_flexion",
                        "condition": "below_threshold",
                        "expected_min": 0.80,
                        "severity_weight": 0.92,
                        "issue_label": "Knees collapsing inward in stance",
                        "coaching_cue": "Push the knees out over the feet and keep pressure through the outer hips.",
                    },
                    {
                        "metric": "hip_level_stability",
                        "condition": "below_threshold",
                        "expected_min": 0.80,
                        "severity_weight": 0.88,
                        "issue_label": "Hips rising out of the loaded position",
                        "coaching_cue": "Sit the hips back and keep them low as you hold or slide in stance.",
                    },
                    {
                        "metric": "torso_alignment",
                        "condition": "below_threshold",
                        "expected_min": 0.81,
                        "severity_weight": 0.84,
                        "issue_label": "Torso pitching too far forward",
                        "coaching_cue": "Lean from the hips, not the spine, and keep the chest strong.",
                    },
                    {
                        "metric": "balance_stability",
                        "condition": "below_threshold",
                        "expected_min": 0.80,
                        "severity_weight": 0.86,
                        "issue_label": "Weight shifting too far side to side",
                        "coaching_cue": "Stay centered between both feet and move without letting the shoulders sway.",
                    },
                ],
                positive_cues=[
                    "Your base is staying wide and controlled.",
                    "You are holding balance well while staying low.",
                ],
                recommendation_templates=[
                    "Hold the stance for shorter intervals and rebuild the same knee bend each rep.",
                    "Add slow lateral slides only after the stance width and torso position stay consistent.",
                ],
            ),
        },
    ],
}

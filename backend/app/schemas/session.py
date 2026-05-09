from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_serializer, model_validator

from app.models.enums import (
    CameraView,
    ComputationStatus,
    DominantSide,
    InputType,
    SessionStatus,
    SeverityLevel,
    SkillLevel,
)
from app.schemas.progress import SessionSummaryResponse
from app.schemas.base import APIBaseModel


class SessionCreateRequest(APIBaseModel):
    sport_id: UUID
    skill_level: SkillLevel
    drill_id: UUID
    input_type: InputType
    camera_view: CameraView | None = None
    dominant_side: DominantSide | None = None


class SessionResponse(APIBaseModel):
    id: UUID
    user_id: UUID
    drill_id: UUID
    sport_id: UUID
    skill_level: SkillLevel
    input_type: InputType
    camera_view: CameraView | None = None
    dominant_side: DominantSide | None = None
    status: SessionStatus
    start_time: datetime
    end_time: datetime | None
    drill_name: str
    sport_name: str


class UploadValidationResult(APIBaseModel):
    is_valid: bool
    content_type: str | None = None
    file_size_bytes: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class CaptureProtocolValidationResult(APIBaseModel):
    is_valid: bool
    reason_code: str
    message: str
    expected_view: CameraView | None = None
    actual_view: CameraView | None = None


class PoseLandmarkCoordinate(APIBaseModel):
    x: float
    y: float
    visibility: float = Field(ge=0, le=1)


class PoseFrameResponse(APIBaseModel):
    session_id: UUID
    frame_index: int = Field(ge=0)
    timestamp_ms: float = Field(ge=0)
    landmarks: dict[str, PoseLandmarkCoordinate] = Field(default_factory=dict)
    frame_valid: bool
    diagnostic_flags: list[str] = Field(default_factory=list)


PoseSequenceStatus = Literal["COMPLETED", "FAILED", "INSUFFICIENT_DATA"]


class PoseProcessingCacheKey(APIBaseModel):
    file_hash: str
    target_pose_fps: float
    max_inference_width: int
    preprocessing_version: str
    pose_model: str


class PoseProcessingMetadata(APIBaseModel):
    original_fps: float | None = None
    target_pose_fps: float
    sampling_stride: int = Field(ge=1)
    original_frame_count: int = Field(ge=0)
    processed_frame_count: int = Field(ge=0)
    valid_frame_count: int = Field(ge=0)
    original_width: int | None = Field(default=None, ge=0)
    original_height: int | None = Field(default=None, ge=0)
    inference_width: int | None = Field(default=None, ge=0)
    inference_height: int | None = Field(default=None, ge=0)
    cache_key: PoseProcessingCacheKey | None = None
    cache_hit: bool = False
    processing_time_ms: float | None = Field(default=None, ge=0)


class PoseSequenceSummaryResponse(APIBaseModel):
    session_id: UUID
    pose_model: Literal["mediapipe_pose"]
    preprocessing_version: Literal["phase1_v0_1_0"]
    frame_count: int = Field(ge=0)
    valid_frame_count: int = Field(ge=0)
    status: PoseSequenceStatus
    diagnostic_flags: list[str] = Field(default_factory=list)
    processing_metadata: PoseProcessingMetadata | None = None


class PoseSequenceResponse(PoseSequenceSummaryResponse):
    sequence_data: list[PoseFrameResponse] = Field(default_factory=list)
    created_at: datetime | None = None


class PerceptionFileMetadata(APIBaseModel):
    file_name: str
    content_type: str
    file_size_bytes: int = Field(ge=0)


class PerceptionProcessingSummary(APIBaseModel):
    frame_count: int = Field(ge=0)
    duration_seconds: float = Field(ge=0)
    fps_estimate: float = Field(ge=0)
    processing_mode: Literal["scaffold"]


class PerceptionKeypointCoordinate(APIBaseModel):
    x: float
    y: float
    z: float


class PerceptionFramePayload(APIBaseModel):
    frame_index: int = Field(ge=0)
    timestamp: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    keypoints: dict[str, PerceptionKeypointCoordinate]


class PerceptionDerivedMotionFeatures(APIBaseModel):
    available_joint_count: int = Field(ge=0)
    missing_frame_ratio: float = Field(ge=0, le=1)
    stability_hint: float = Field(ge=0, le=1)


class PerceptionResult(APIBaseModel):
    source_type: Literal["upload"]
    file_metadata: PerceptionFileMetadata
    processing_summary: PerceptionProcessingSummary
    keypoint_series: list[PerceptionFramePayload]
    derived_motion_features: PerceptionDerivedMotionFeatures


class CognitionProcessingReadiness(APIBaseModel):
    payload_usable: bool
    minimum_frames_met: bool


class CognitionDerivedMetrics(APIBaseModel):
    frame_consistency_score: float = Field(ge=0, le=1)
    coverage_score: float = Field(ge=0, le=1)
    motion_stability_score: float = Field(ge=0, le=1)
    payload_completeness_score: float = Field(ge=0, le=1)


class CognitionResult(APIBaseModel):
    analysis_mode: Literal["scaffold"]
    session_id: UUID
    drill_id: UUID
    processing_readiness: CognitionProcessingReadiness
    derived_metrics: CognitionDerivedMetrics
    diagnostic_flags: list[str] = Field(default_factory=list)


class EvaluationIssueResponse(APIBaseModel):
    metric: str
    actual_score: float = Field(ge=0, le=1)
    expected_min: float | None = Field(default=None, ge=0, le=1)
    expected_max: float | None = Field(default=None, ge=0, le=1)
    deviation: float = Field(ge=0)
    severity_level: SeverityLevel
    issue_label: str
    coaching_cue: str


EvaluationStatus = Literal["COMPLETED", "FAILED", "INSUFFICIENT_DATA"]
IssueDirection = Literal["UNDER_RANGE", "OVER_RANGE", "NONE"]


class MetricEvaluationResultResponse(APIBaseModel):
    metric_id: str | None = None
    metric_name: str
    phase_id: str
    raw_value: float | None = None
    unit: str
    ideal_min: float | None = None
    ideal_max: float | None = None
    deviation: float | None = None
    issue_direction: IssueDirection
    severity_level: SeverityLevel
    normalized_score: float | None = Field(default=None, ge=0, le=1)
    affected_body_part: str
    computation_status: ComputationStatus
    valid_frame_count: int = Field(ge=0)
    formula_version: str
    diagnostic_flags: list[str] = Field(default_factory=list)


class EvaluationFrameRangeResponse(APIBaseModel):
    """Inclusive-overlapping frame range.

    Adjacent phases may share the boundary frame so phase transitions remain
    inspectable by downstream deterministic feedback logic. Zero-length ranges
    are allowed when deterministic boundaries collapse to one frame.
    """

    phase_id: str
    start_frame_index: int = Field(ge=0)
    end_frame_index: int = Field(ge=0)
    start_timestamp_ms: float = Field(ge=0)
    end_timestamp_ms: float = Field(ge=0)
    boundary_mode: Literal["inclusive_overlapping"] = "inclusive_overlapping"


class DeterministicEvaluationIssueResponse(APIBaseModel):
    phase_id: str
    metric_id: str | None = None
    metric_name: str
    severity_level: SeverityLevel
    affected_body_part: str
    deviation: float
    issue_direction: IssueDirection
    computation_status: ComputationStatus = ComputationStatus.COMPUTED
    diagnostic_flags: list[str] = Field(default_factory=list)


class RankedMetricResponse(APIBaseModel):
    phase_id: str
    metric_id: str
    metric_name: str
    score: float = Field(ge=0, le=1)


class PhaseEvaluationResultResponse(APIBaseModel):
    phase_id: str
    frame_range: EvaluationFrameRangeResponse
    metric_results: list[MetricEvaluationResultResponse] = Field(default_factory=list)
    phase_score: float = Field(ge=0, le=1)
    phase_severity: SeverityLevel
    detected_issues: list[DeterministicEvaluationIssueResponse] = Field(default_factory=list)


class DeterministicEvaluationResult(APIBaseModel):
    evaluation_version: str = "phase2c_v0_1_0"
    status: EvaluationStatus
    session_id: UUID
    sport_id: UUID
    skill_level: SkillLevel
    drill_id: UUID
    phase_results: list[PhaseEvaluationResultResponse] = Field(default_factory=list)
    overall_score: float = Field(ge=0, le=1)
    overall_severity: SeverityLevel
    detected_issues: list[DeterministicEvaluationIssueResponse] = Field(default_factory=list)
    strongest_metrics: list[RankedMetricResponse] = Field(default_factory=list)
    weakest_metrics: list[RankedMetricResponse] = Field(default_factory=list)
    diagnostic_flags: list[str] = Field(default_factory=list)
    requested_dominant_side: DominantSide | None = None
    resolved_dominant_side: DominantSide | None = None
    dominant_side_confidence: float | None = Field(default=None, ge=0, le=1)
    dominant_side_diagnostic_flags: list[str] | None = None

    @field_validator("strongest_metrics", "weakest_metrics", mode="before")
    @classmethod
    def _coerce_legacy_ranked_metrics(cls, value: Any) -> Any:
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            ranked = []
            for item in value:
                phase_id, _, metric_name = item.partition(":")
                ranked.append(
                    {
                        "phase_id": phase_id,
                        "metric_id": metric_name or item,
                        "metric_name": metric_name or item,
                        "score": 0.0,
                    }
                )
            return ranked
        return value

    @model_serializer(mode="wrap")
    def _serialize_without_empty_dominant_side_metadata(self, handler):
        payload = handler(self)
        for field_name in (
            "requested_dominant_side",
            "resolved_dominant_side",
            "dominant_side_confidence",
            "dominant_side_diagnostic_flags",
        ):
            if payload.get(field_name) is None:
                payload.pop(field_name, None)
        return payload


FeedbackGenerationStatus = Literal["COMPLETED", "FAILED", "NO_ACTIONABLE_ISSUES"]
FEEDBACK_VERSION = "phase3a_v0_1_0"


class DeterministicFeedbackItemResponse(APIBaseModel):
    phase_id: str
    metric_id: str | None = None
    metric_name: str
    severity_level: SeverityLevel
    affected_body_part: str
    issue_direction: IssueDirection
    issue_title: str
    coaching_cue: str
    improvement_suggestion: str
    priority_rank: int = Field(ge=1)
    deviation: float = Field(ge=0)


class DeterministicFeedbackResult(APIBaseModel):
    feedback_version: str = FEEDBACK_VERSION
    status: FeedbackGenerationStatus
    session_id: UUID
    overall_feedback_summary: str
    prioritized_feedback_items: list[DeterministicFeedbackItemResponse] = Field(
        default_factory=list
    )
    improvement_suggestions: list[str] = Field(default_factory=list)
    diagnostic_flags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


LLMFeedbackGenerationStatus = Literal["COMPLETED", "FAILED"]
LLM_FEEDBACK_VERSION = "phase3b_v0_1_0"


class LLMEnhancedFeedbackItemResponse(APIBaseModel):
    phase_id: str
    metric_id: str | None = None
    metric_name: str
    severity_level: SeverityLevel
    priority_rank: int = Field(ge=1)
    affected_body_part: str
    issue_direction: IssueDirection
    deterministic_coaching_cue: str
    llm_coaching_cue: str
    deterministic_improvement_suggestion: str
    llm_improvement_suggestion: str
    grounding_fields_used: list[str] = Field(default_factory=list)
    fallback_used: bool


class LLMEnhancedSessionSummaryResponse(APIBaseModel):
    deterministic_summary: str
    llm_summary: str
    grounding_fields_used: list[str] = Field(default_factory=list)
    fallback_used: bool


class LLMFeedbackResult(APIBaseModel):
    llm_feedback_version: str = LLM_FEEDBACK_VERSION
    status: LLMFeedbackGenerationStatus = "COMPLETED"
    session_id: UUID
    provider: str
    model: str
    fallback_used: bool
    advanced_context_used: bool = False
    advanced_context_sources: list[str] = Field(default_factory=list)
    context_diagnostic_flags: list[str] = Field(default_factory=list)
    enhanced_feedback_items: list[LLMEnhancedFeedbackItemResponse] = Field(
        default_factory=list
    )
    enhanced_summary: LLMEnhancedSessionSummaryResponse
    diagnostic_flags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


FuzzyInterpretationStatus = Literal[
    "COMPLETED",
    "FAILED",
    "NO_INTERPRETABLE_METRICS",
    "DISABLED",
]
FuzzyBaseLabel = Literal[
    "IDEAL",
    "SLIGHTLY_OFF",
    "MODERATELY_OFF",
    "STRONGLY_OFF",
]
FuzzyMetricLabel = Literal[
    "IDEAL",
    "SLIGHTLY_OFF",
    "MODERATELY_OFF",
    "STRONGLY_OFF",
    "NOT_INTERPRETABLE",
]
DirectionAwareFuzzyLabel = Literal[
    "IDEAL",
    "SLIGHTLY_LOW",
    "MODERATELY_LOW",
    "STRONGLY_LOW",
    "SLIGHTLY_HIGH",
    "MODERATELY_HIGH",
    "STRONGLY_HIGH",
    "NOT_INTERPRETABLE",
]
FUZZY_INTERPRETATION_VERSION = "phase4a_v0_1_0"


class FuzzyMetricInterpretationResponse(APIBaseModel):
    metric_id: str | None = None
    metric_name: str
    phase_id: str
    computation_status: ComputationStatus
    deviation: float | None = Field(default=None, ge=0)
    issue_direction: IssueDirection
    severity_level: SeverityLevel
    affected_body_part: str
    primary_fuzzy_label: FuzzyMetricLabel
    membership_scores: dict[FuzzyBaseLabel, float] = Field(default_factory=dict)
    dominant_label_confidence: float | None = Field(default=None, ge=0, le=1)
    direction_aware_label: DirectionAwareFuzzyLabel
    diagnostic_flags: list[str] = Field(default_factory=list)


class FuzzySummaryResponse(APIBaseModel):
    ideal_count: int = Field(ge=0)
    slightly_off_count: int = Field(ge=0)
    moderately_off_count: int = Field(ge=0)
    strongly_off_count: int = Field(ge=0)
    not_interpretable_count: int = Field(ge=0)
    interpretable_metric_count: int = Field(ge=0)
    dominant_fuzzy_label: FuzzyMetricLabel
    top_concern_areas: list[str] = Field(default_factory=list)


class FuzzyInterpretationResult(APIBaseModel):
    fuzzy_version: str = FUZZY_INTERPRETATION_VERSION
    status: FuzzyInterpretationStatus
    session_id: UUID
    drill_id: UUID
    sport_id: UUID
    skill_level: SkillLevel
    fuzzy_metric_results: list[FuzzyMetricInterpretationResponse] = Field(
        default_factory=list
    )
    fuzzy_summary: FuzzySummaryResponse
    diagnostic_flags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


IT2FuzzyInterpretationStatus = Literal[
    "COMPLETED",
    "FAILED",
    "NO_INTERPRETABLE_METRICS",
    "DISABLED",
]
IT2UncertaintyCategory = Literal[
    "LOW_UNCERTAINTY",
    "MEDIUM_UNCERTAINTY",
    "HIGH_UNCERTAINTY",
    "NOT_INTERPRETABLE",
]
IT2_FUZZY_VERSION = "phase4e_v0_1_0"


class IT2MembershipIntervalResponse(APIBaseModel):
    lower: float = Field(ge=0, le=1)
    upper: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)


class IT2HighestUncertaintyMetricResponse(APIBaseModel):
    phase_id: str | None = None
    metric_id: str | None = None
    uncertainty_width: float | None = Field(default=None, ge=0, le=1)


class IT2UncertaintySummaryResponse(APIBaseModel):
    low_count: int = Field(ge=0)
    medium_count: int = Field(ge=0)
    high_count: int = Field(ge=0)
    not_interpretable_count: int = Field(ge=0)
    average_uncertainty_width: float = Field(ge=0, le=1)
    highest_uncertainty_metric: IT2HighestUncertaintyMetricResponse
    summary_text: str


class IT2FuzzyMetricInterpretationResponse(APIBaseModel):
    phase_id: str
    metric_id: str | None = None
    metric_name: str
    computation_status: ComputationStatus
    deviation: float | None = Field(default=None, ge=0)
    issue_direction: IssueDirection
    severity_level: SeverityLevel
    affected_body_part: str
    type1_primary_label: FuzzyMetricLabel
    type1_direction_aware_label: DirectionAwareFuzzyLabel
    dominant_label_confidence: float | None = Field(default=None, ge=0, le=1)
    uncertainty_width: float | None = Field(default=None, ge=0, le=1)
    uncertainty_category: IT2UncertaintyCategory
    interval_memberships: dict[FuzzyBaseLabel, IT2MembershipIntervalResponse] = Field(
        default_factory=dict
    )
    primary_interval_label: FuzzyMetricLabel
    diagnostic_flags: list[str] = Field(default_factory=list)


class IT2FuzzyInterpretationResult(APIBaseModel):
    it2_fuzzy_version: str = IT2_FUZZY_VERSION
    status: IT2FuzzyInterpretationStatus
    session_id: UUID
    sport_id: UUID
    drill_id: UUID
    skill_level: SkillLevel
    it2_metric_results: list[IT2FuzzyMetricInterpretationResponse] = Field(
        default_factory=list
    )
    uncertainty_summary: IT2UncertaintySummaryResponse
    diagnostic_flags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


PedagogicalDecisionStatus = Literal[
    "COMPLETED",
    "FAILED",
    "NO_ACTIONABLE_FEEDBACK",
]
TeachingStrategy = Literal[
    "single_focus_mastery",
    "dual_focus_refinement",
    "multi_focus_precision",
]
ToneProfile = Literal[
    "supportive_simple",
    "corrective_specific",
    "technical_performance",
]
CorrectionIntensity = Literal["observe", "soft", "corrective", "direct"]
PEDAGOGICAL_DECISION_VERSION = "phase4b_v0_1_0"


class PedagogicalFocusItemResponse(APIBaseModel):
    phase_id: str
    metric_id: str | None = None
    metric_name: str
    severity_level: SeverityLevel
    fuzzy_label: FuzzyMetricLabel | None = None
    dominant_label_confidence: float | None = Field(default=None, ge=0, le=1)
    affected_body_part: str
    priority_rank: int = Field(ge=1)
    teaching_reason: str
    recommended_message_style: str


class PedagogicalSuppressedItemResponse(APIBaseModel):
    phase_id: str
    metric_id: str | None = None
    metric_name: str
    severity_level: SeverityLevel
    priority_rank: int = Field(ge=1)
    suppression_reason: str


class PedagogicalDecisionResult(APIBaseModel):
    pedagogical_version: str = PEDAGOGICAL_DECISION_VERSION
    status: PedagogicalDecisionStatus
    session_id: UUID
    sport_id: UUID
    drill_id: UUID
    skill_level: SkillLevel
    teaching_strategy: TeachingStrategy
    selected_focus_items: list[PedagogicalFocusItemResponse] = Field(
        default_factory=list
    )
    suppressed_items: list[PedagogicalSuppressedItemResponse] = Field(
        default_factory=list
    )
    tone_profile: ToneProfile
    correction_intensity: CorrectionIntensity
    learning_objective: str
    progression_advice: str
    diagnostic_flags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


OntologyReasoningStatus = Literal[
    "COMPLETED",
    "FAILED",
    "NO_SIGNIFICANT_ISSUES",
]
ONTOLOGY_REASONING_VERSION = "phase4c_v0_1_0"


class OntologySeveritySummaryResponse(APIBaseModel):
    severe_count: int = Field(ge=0)
    moderate_count: int = Field(ge=0)


class OntologyConceptGroupResponse(APIBaseModel):
    metrics: list[str] = Field(default_factory=list)
    phases: list[str] = Field(default_factory=list)
    total_weight: float = Field(ge=0)
    severity_summary: OntologySeveritySummaryResponse


class OntologyBodyRegionSummaryResponse(APIBaseModel):
    concepts: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    phases: list[str] = Field(default_factory=list)
    total_weight: float = Field(ge=0)
    severity_summary: OntologySeveritySummaryResponse


class OntologyReasoningResult(APIBaseModel):
    ontology_version: str = ONTOLOGY_REASONING_VERSION
    status: OntologyReasoningStatus
    session_id: UUID
    sport_id: UUID
    drill_id: UUID
    skill_level: SkillLevel
    primary_concept: str | None = None
    secondary_concepts: list[str] = Field(default_factory=list)
    concept_groups: dict[str, OntologyConceptGroupResponse] = Field(
        default_factory=dict
    )
    body_region_summary: dict[str, OntologyBodyRegionSummaryResponse] = Field(
        default_factory=dict
    )
    reasoning_summary: str
    diagnostic_flags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


ChoquetAggregationStatus = Literal[
    "COMPLETED",
    "FAILED",
    "NO_ACTIONABLE_ISSUES",
]
CHOQUET_AGGREGATION_VERSION = "phase4d_v0_1_0"


class ChoquetAggregatedGroupResponse(APIBaseModel):
    concepts: list[str] = Field(default_factory=list)
    input_values: dict[str, float] = Field(default_factory=dict)
    choquet_score: float = Field(ge=0, le=1)
    interaction_detected: bool
    explanation: str


class ChoquetAggregationResult(APIBaseModel):
    choquet_version: str = CHOQUET_AGGREGATION_VERSION
    status: ChoquetAggregationStatus
    session_id: UUID
    sport_id: UUID
    drill_id: UUID
    skill_level: SkillLevel
    concept_aggregation: dict[str, ChoquetAggregatedGroupResponse] = Field(
        default_factory=dict
    )
    body_region_aggregation: dict[str, ChoquetAggregatedGroupResponse] = Field(
        default_factory=dict
    )
    overall_choquet_score: float = Field(ge=0, le=1)
    dominant_interaction_group: str | None = None
    diagnostic_flags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


TemporalModelingStatus = Literal["COMPLETED", "FAILED", "INSUFFICIENT_DATA"]
TemporalState = Literal[
    "STABLE",
    "CONTROLLED",
    "RUSHED",
    "JERKY",
    "INCOMPLETE",
    "UNCERTAIN",
]
TEMPORAL_MODEL_VERSION = "phase4f_v0_1_0"


class TemporalPhaseResultResponse(APIBaseModel):
    phase_id: str
    frame_count: int = Field(ge=0)
    phase_duration_ms: float = Field(ge=0)
    valid_frame_ratio: float = Field(ge=0, le=1)
    average_velocity_proxy: float = Field(ge=0, le=1)
    smoothness_proxy: float = Field(ge=0, le=1)
    acceleration_change_proxy: float = Field(ge=0, le=1)
    temporal_state: TemporalState
    state_confidence: float = Field(ge=0, le=1)
    diagnostic_flags: list[str] = Field(default_factory=list)


class TemporalTransitionResultResponse(APIBaseModel):
    from_phase: str
    to_phase: str
    transition_valid: bool
    transition_gap_ms: float
    phase_order_valid: bool
    diagnostic_flags: list[str] = Field(default_factory=list)


class TemporalModelingResult(APIBaseModel):
    temporal_model_version: str = TEMPORAL_MODEL_VERSION
    status: TemporalModelingStatus
    session_id: UUID
    sport_id: UUID
    drill_id: UUID
    skill_level: SkillLevel
    phase_temporal_results: list[TemporalPhaseResultResponse] = Field(
        default_factory=list
    )
    transition_results: list[TemporalTransitionResultResponse] = Field(
        default_factory=list
    )
    overall_temporal_state: TemporalState
    temporal_summary: str
    diagnostic_flags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class DrillEvaluationResult(APIBaseModel):
    evaluation_mode: Literal["deterministic_scaffold"]
    session_id: UUID
    drill_id: UUID
    drill_name: str
    evaluator_name: str
    metric_scores: dict[str, float] = Field(default_factory=dict)
    issues: list[EvaluationIssueResponse] = Field(default_factory=list)
    summary_flags: list[str] = Field(default_factory=list)
    feedback_count: int = Field(ge=0)


ArtifactType = Literal[
    "perception_payload",
    "cognition_result",
    "evaluation_result",
    "pose_sequence",
    "feedback_result",
    "llm_feedback_result",
    "fuzzy_interpretation_result",
    "it2_fuzzy_interpretation_result",
    "pedagogical_decision_result",
    "ontology_reasoning_result",
    "choquet_aggregation_result",
    "temporal_modeling_result",
]


class SessionArtifactResponse(APIBaseModel):
    id: UUID
    session_id: UUID
    artifact_type: ArtifactType
    payload_json: dict[str, Any]
    created_at: datetime


class FeedbackResponse(APIBaseModel):
    id: UUID
    session_id: UUID
    severity_level: SeverityLevel
    technique_issue: str
    coaching_cue: str
    metric_snapshot: dict[str, Any]
    created_at: datetime


class SessionArtifactsResponse(APIBaseModel):
    artifacts: list[SessionArtifactResponse]
    pose_sequence: PoseSequenceResponse | None = None
    perception_result: PerceptionResult | None = None
    cognition_result: CognitionResult | None = None
    evaluation_result: DeterministicEvaluationResult | None = None
    feedback_result: DeterministicFeedbackResult | None = None
    llm_feedback_result: LLMFeedbackResult | None = None
    fuzzy_interpretation_result: FuzzyInterpretationResult | None = None
    it2_fuzzy_interpretation_result: IT2FuzzyInterpretationResult | None = None
    pedagogical_decision_result: PedagogicalDecisionResult | None = None
    ontology_reasoning_result: OntologyReasoningResult | None = None
    choquet_aggregation_result: ChoquetAggregationResult | None = None
    temporal_modeling_result: TemporalModelingResult | None = None
    session_summary: SessionSummaryResponse | None = None
    feedback: list[FeedbackResponse] = Field(default_factory=list)


class UploadProcessingResponse(APIBaseModel):
    session_id: UUID
    status: SessionStatus
    upload_received: bool
    validation: UploadValidationResult
    capture_validation: CaptureProtocolValidationResult | None = None
    pose_sequence: PoseSequenceSummaryResponse | None = None
    perception_result: PerceptionResult | None = None
    cognition_result: CognitionResult | None = None
    evaluation_result: DeterministicEvaluationResult | None = None
    session_summary: SessionSummaryResponse | None = None
    feedback: list[FeedbackResponse] = Field(default_factory=list)
    artifacts_persisted: list[ArtifactType] = Field(default_factory=list)
    next_step: str


class LiveReadinessRequest(APIBaseModel):
    camera_permission_granted: bool = False
    lighting_ready: bool = False
    framing_ready: bool = False
    space_ready: bool = False
    client_ready: bool = False


class LiveReadinessResponse(APIBaseModel):
    camera_ready: bool
    lighting_ready: bool
    framing_ready: bool
    space_ready: bool
    warnings: list[str] = Field(default_factory=list)


class LiveStartResponse(APIBaseModel):
    session_id: UUID
    status: SessionStatus
    started: bool
    message: str
    readiness: LiveReadinessResponse


class FrameBatchRequest(APIBaseModel):
    frame_count: int = Field(gt=0, le=600)
    timestamps: list[float] = Field(default_factory=list)
    client_ready: bool

    @model_validator(mode="after")
    def validate_timestamp_count(self) -> "FrameBatchRequest":
        if self.timestamps and len(self.timestamps) != self.frame_count:
            raise ValueError("timestamps must contain one entry per frame.")
        return self


class FrameBatchAcceptanceResult(APIBaseModel):
    accepted: bool
    frame_count: int
    message: str


class FrameBatchResponse(APIBaseModel):
    session_id: UUID
    accepted: bool
    frame_count: int
    message: str


class LiveEndRequest(APIBaseModel):
    final_status: SessionStatus

    @field_validator("final_status")
    @classmethod
    def validate_final_status(cls, value: SessionStatus) -> SessionStatus:
        if value not in {SessionStatus.COMPLETED, SessionStatus.ABORTED}:
            raise ValueError("final_status must be COMPLETED or ABORTED.")
        return value

import type { SessionSummary } from "./progress";
import type { SkillLevel } from "./profile";

export type SessionInputType = "UPLOAD" | "LIVE";
export type SessionStatus = "ACTIVE" | "COMPLETED" | "ABORTED";
export type CameraView = "FRONTAL" | "LEFT_SAGITTAL" | "RIGHT_SAGITTAL";
export type DominantSide = "AUTO" | "LEFT" | "RIGHT";
export type StoredDominantSide = Exclude<DominantSide, "AUTO">;
export type SessionAnalysisPipelineStatus =
  | "COMPLETED"
  | "COMPLETED_WITH_WARNINGS"
  | "FAILED";
export type AnalysisState = "IDLE" | "RUNNING" | SessionAnalysisPipelineStatus;
export type AnalysisStepStatus =
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "WARNING"
  | "FAILED";
export type SessionAnalysisStep =
  | "evaluation"
  | "fuzzy"
  | "it2"
  | "deterministic_feedback"
  | "pedagogy"
  | "ontology"
  | "choquet"
  | "temporal"
  | "llm";

export type SessionAnalysisWarning = {
  step: string;
  message: string;
  diagnosticFlags: string[];
};

export type AnalysisProgressStep = {
  id: SessionAnalysisStep;
  label: string;
  status: AnalysisStepStatus;
  required: boolean;
  dependencyNotes?: string;
  warning?: string | null;
};

export type TrainingSession = {
  id: string;
  user_id: string;
  drill_id: string;
  sport_id: string;
  skill_level: SkillLevel;
  input_type: SessionInputType;
  camera_view?: CameraView | null;
  dominant_side?: StoredDominantSide | null;
  status: SessionStatus;
  start_time: string;
  end_time: string | null;
  drill_name: string;
  sport_name: string;
};

export type SessionCreateRequest = {
  sport_id: string;
  skill_level: SkillLevel;
  drill_id: string;
  input_type: SessionInputType;
  camera_view?: CameraView | null;
  dominant_side?: StoredDominantSide | null;
};

export type UploadValidation = {
  is_valid: boolean;
  content_type: string | null;
  file_size_bytes: number;
  warnings: string[];
  errors: string[];
};

export type CaptureProtocolValidation = {
  is_valid: boolean;
  reason_code: string;
  message: string;
  expected_view?: CameraView | null;
  actual_view?: CameraView | null;
};

export type ArtifactType =
  | "perception_payload"
  | "cognition_result"
  | "evaluation_result"
  | "pose_sequence"
  | "feedback_result"
  | "llm_feedback_result"
  | "fuzzy_interpretation_result"
  | "it2_fuzzy_interpretation_result"
  | "pedagogical_decision_result"
  | "ontology_reasoning_result"
  | "choquet_aggregation_result"
  | "temporal_modeling_result"
  | "feedback_tts_result";

export type PoseSequenceStatus = "COMPLETED" | "FAILED" | "INSUFFICIENT_DATA";

export type PoseProcessingCacheKey = {
  file_hash: string;
  target_pose_fps: number;
  max_inference_width: number;
  preprocessing_version: string;
  pose_model: string;
};

export type PoseProcessingMetadata = {
  original_fps?: number | null;
  target_pose_fps: number;
  sampling_stride: number;
  original_frame_count: number;
  processed_frame_count: number;
  valid_frame_count: number;
  original_width?: number | null;
  original_height?: number | null;
  inference_width?: number | null;
  inference_height?: number | null;
  cache_key?: PoseProcessingCacheKey | null;
  cache_hit?: boolean;
  processing_time_ms?: number | null;
};

export type PoseLandmarkCoordinate = {
  x: number;
  y: number;
  visibility: number;
};

export type PoseFrame = {
  session_id: string;
  frame_index: number;
  timestamp_ms: number;
  landmarks: Record<string, PoseLandmarkCoordinate>;
  frame_valid: boolean;
  diagnostic_flags: string[];
};

export type PoseSequenceSummary = {
  session_id: string;
  pose_model: "mediapipe_pose";
  preprocessing_version: "phase1_v0_1_0";
  frame_count: number;
  valid_frame_count: number;
  status: PoseSequenceStatus;
  diagnostic_flags: string[];
  processing_metadata?: PoseProcessingMetadata | null;
};

export type PoseSequence = PoseSequenceSummary & {
  sequence_data: PoseFrame[];
  created_at?: string | null;
};

export type PerceptionFileMetadata = {
  file_name: string;
  content_type: string;
  file_size_bytes: number;
};

export type PerceptionProcessingSummary = {
  frame_count: number;
  duration_seconds: number;
  fps_estimate: number;
  processing_mode: "scaffold";
};

export type PerceptionKeypointCoordinate = {
  x: number;
  y: number;
  z: number;
};

export type PerceptionFramePayload = {
  frame_index: number;
  timestamp: number;
  confidence: number;
  keypoints: Record<string, PerceptionKeypointCoordinate>;
};

export type PerceptionDerivedMotionFeatures = {
  available_joint_count: number;
  missing_frame_ratio: number;
  stability_hint: number;
};

export type PerceptionResult = {
  source_type: "upload";
  file_metadata: PerceptionFileMetadata;
  processing_summary: PerceptionProcessingSummary;
  keypoint_series: PerceptionFramePayload[];
  derived_motion_features: PerceptionDerivedMotionFeatures;
};

export type CognitionProcessingReadiness = {
  payload_usable: boolean;
  minimum_frames_met: boolean;
};

export type CognitionDerivedMetrics = {
  frame_consistency_score: number;
  coverage_score: number;
  motion_stability_score: number;
  payload_completeness_score: number;
};

export type CognitionResult = {
  analysis_mode: "scaffold";
  session_id: string;
  drill_id: string;
  processing_readiness: CognitionProcessingReadiness;
  derived_metrics: CognitionDerivedMetrics;
  diagnostic_flags: string[];
};

export type SeverityLevel = "MINOR" | "MODERATE" | "SEVERE";
export type ComputationStatus = "COMPUTED" | "NOT_COMPUTABLE";
export type IssueDirection = "UNDER_RANGE" | "OVER_RANGE" | "NONE";

export type MetricEvaluationResult = {
  metric_id?: string | null;
  metric_name: string;
  phase_id: string;
  raw_value?: number | null;
  unit: string;
  ideal_min?: number | null;
  ideal_max?: number | null;
  deviation?: number | null;
  issue_direction: IssueDirection;
  severity_level: SeverityLevel;
  normalized_score?: number | null;
  affected_body_part: string;
  computation_status: ComputationStatus;
  valid_frame_count: number;
  formula_version: string;
  diagnostic_flags: string[];
};

export type EvaluationFrameRange = {
  phase_id: string;
  start_frame_index: number;
  end_frame_index: number;
  start_timestamp_ms: number;
  end_timestamp_ms: number;
  boundary_mode: "inclusive_overlapping";
};

export type DeterministicEvaluationIssue = {
  phase_id: string;
  metric_id?: string | null;
  metric_name: string;
  severity_level: SeverityLevel;
  affected_body_part: string;
  deviation: number;
  issue_direction: IssueDirection;
  computation_status: ComputationStatus;
  diagnostic_flags: string[];
};

export type RankedMetric = {
  phase_id: string;
  metric_id: string;
  metric_name: string;
  score: number;
};

export type PhaseEvaluationResult = {
  phase_id: string;
  frame_range: EvaluationFrameRange;
  metric_results: MetricEvaluationResult[];
  phase_score: number;
  phase_severity: SeverityLevel;
  detected_issues: DeterministicEvaluationIssue[];
};

export type RepEvaluationSummary = {
  rep_index: number;
  start_frame_index: number;
  end_frame_index: number;
  start_timestamp_ms: number;
  end_timestamp_ms: number;
  confidence: number;
  overall_score: number;
  overall_severity: SeverityLevel;
  issue_metric_ids: string[];
};

export type SetLevelEvaluationSummary = {
  evaluation_mode: "single_cycle" | "multi_rep";
  average_score: number;
  best_score: number;
  worst_score: number;
  consistency_score: number;
  repeated_issue_metric_ids: string[];
  dominant_recurring_issue_metric_id?: string | null;
  consistency_warning?: string | null;
};

export type DeterministicEvaluationResult = {
  evaluation_version: string;
  status: "COMPLETED" | "FAILED" | "INSUFFICIENT_DATA";
  session_id: string;
  sport_id: string;
  skill_level: SkillLevel;
  drill_id: string;
  phase_results: PhaseEvaluationResult[];
  overall_score: number;
  overall_severity: SeverityLevel;
  detected_issues: DeterministicEvaluationIssue[];
  strongest_metrics: RankedMetric[];
  weakest_metrics: RankedMetric[];
  diagnostic_flags: string[];
  requested_dominant_side?: StoredDominantSide | null;
  resolved_dominant_side?: StoredDominantSide | null;
  dominant_side_confidence?: number | null;
  dominant_side_diagnostic_flags?: string[] | null;
  detected_rep_count?: number | null;
  evaluated_rep_count?: number | null;
  rep_summaries?: RepEvaluationSummary[];
  set_level_summary?: SetLevelEvaluationSummary | null;
};

export type FeedbackGenerationStatus =
  | "COMPLETED"
  | "FAILED"
  | "NO_ACTIONABLE_ISSUES";

export type DeterministicFeedbackItem = {
  phase_id: string;
  metric_id?: string | null;
  metric_name: string;
  severity_level: SeverityLevel;
  affected_body_part: string;
  issue_direction: IssueDirection;
  issue_title: string;
  coaching_cue: string;
  improvement_suggestion: string;
  what_happened?: string;
  why_it_matters?: string;
  what_to_fix?: string;
  next_rep_cue?: string;
  simple_coaching_phrase?: string;
  priority_rank: number;
  deviation: number;
};

export type FeedbackTTSSegments = {
  segment_1: string;
  segment_2: string;
  segment_3: string;
};

export type FeedbackTTSRequest = {
  feedback_item_key?: string | null;
  segments?: FeedbackTTSSegments | null;
};

export type FeedbackTTSResponse = {
  session_id: string;
  model: string;
  voice: string;
  cached: boolean;
  media_type: string;
  audio_base64: string;
  segments: FeedbackTTSSegments;
  text_hash: string;
};

export type DeterministicFeedbackResult = {
  feedback_version: string;
  status: FeedbackGenerationStatus;
  session_id: string;
  overall_feedback_summary: string;
  prioritized_feedback_items: DeterministicFeedbackItem[];
  improvement_suggestions: string[];
  diagnostic_flags: string[];
  created_at?: string | null;
};

export type LLMEnhancedFeedbackItem = {
  phase_id: string;
  metric_id?: string | null;
  metric_name: string;
  severity_level: SeverityLevel;
  priority_rank: number;
  affected_body_part: string;
  issue_direction: IssueDirection;
  deterministic_coaching_cue: string;
  llm_coaching_cue: string;
  llm_main_coaching_cue?: string;
  llm_what_happened?: string;
  llm_why_it_matters?: string;
  llm_what_to_fix?: string;
  llm_next_session_cue?: string;
  deterministic_improvement_suggestion: string;
  llm_improvement_suggestion: string;
  grounding_fields_used: string[];
  fallback_used: boolean;
};

export type LLMEnhancedSessionSummary = {
  deterministic_summary: string;
  llm_summary: string;
  grounding_fields_used: string[];
  fallback_used: boolean;
};

export type LLMFeedbackResult = {
  llm_feedback_version: string;
  status: "COMPLETED" | "FAILED";
  session_id: string;
  provider: string;
  model: string;
  fallback_used: boolean;
  feedback_hash?: string | null;
  cache_hit?: boolean;
  advanced_context_used: boolean;
  advanced_context_sources: string[];
  context_diagnostic_flags: string[];
  enhanced_feedback_items: LLMEnhancedFeedbackItem[];
  enhanced_summary: LLMEnhancedSessionSummary;
  diagnostic_flags: string[];
  created_at?: string | null;
};

export type FuzzyInterpretationStatus =
  | "COMPLETED"
  | "FAILED"
  | "NO_INTERPRETABLE_METRICS"
  | "DISABLED";

export type FuzzyMetricLabel =
  | "IDEAL"
  | "SLIGHTLY_OFF"
  | "MODERATELY_OFF"
  | "STRONGLY_OFF"
  | "NOT_INTERPRETABLE";

export type DirectionAwareFuzzyLabel =
  | "IDEAL"
  | "SLIGHTLY_LOW"
  | "MODERATELY_LOW"
  | "STRONGLY_LOW"
  | "SLIGHTLY_HIGH"
  | "MODERATELY_HIGH"
  | "STRONGLY_HIGH"
  | "NOT_INTERPRETABLE";

export type FuzzyMetricInterpretation = {
  metric_id?: string | null;
  metric_name: string;
  phase_id: string;
  computation_status: ComputationStatus;
  deviation?: number | null;
  issue_direction: IssueDirection;
  severity_level: SeverityLevel;
  affected_body_part: string;
  primary_fuzzy_label: FuzzyMetricLabel;
  membership_scores: Record<string, number>;
  dominant_label_confidence?: number | null;
  direction_aware_label: DirectionAwareFuzzyLabel;
  diagnostic_flags: string[];
};

export type FuzzySummary = {
  ideal_count: number;
  slightly_off_count: number;
  moderately_off_count: number;
  strongly_off_count: number;
  not_interpretable_count: number;
  interpretable_metric_count: number;
  dominant_fuzzy_label: FuzzyMetricLabel;
  top_concern_areas: string[];
};

export type FuzzyInterpretationResult = {
  fuzzy_version: string;
  status: FuzzyInterpretationStatus;
  session_id: string;
  drill_id: string;
  sport_id: string;
  skill_level: SkillLevel;
  fuzzy_metric_results: FuzzyMetricInterpretation[];
  fuzzy_summary: FuzzySummary;
  diagnostic_flags: string[];
  created_at?: string | null;
};

export type IT2FuzzyInterpretationStatus =
  | "COMPLETED"
  | "FAILED"
  | "NO_INTERPRETABLE_METRICS"
  | "DISABLED";

export type IT2UncertaintyCategory =
  | "LOW_UNCERTAINTY"
  | "MEDIUM_UNCERTAINTY"
  | "HIGH_UNCERTAINTY"
  | "NOT_INTERPRETABLE";

export type IT2MembershipInterval = {
  lower: number;
  upper: number;
  width: number;
};

export type IT2HighestUncertaintyMetric = {
  phase_id?: string | null;
  metric_id?: string | null;
  uncertainty_width?: number | null;
};

export type IT2UncertaintySummary = {
  low_count: number;
  medium_count: number;
  high_count: number;
  not_interpretable_count: number;
  average_uncertainty_width: number;
  highest_uncertainty_metric: IT2HighestUncertaintyMetric;
  summary_text: string;
};

export type IT2FuzzyMetricInterpretation = {
  phase_id: string;
  metric_id?: string | null;
  metric_name: string;
  computation_status: ComputationStatus;
  deviation?: number | null;
  issue_direction: IssueDirection;
  severity_level: SeverityLevel;
  affected_body_part: string;
  type1_primary_label: FuzzyMetricLabel;
  type1_direction_aware_label: DirectionAwareFuzzyLabel;
  dominant_label_confidence?: number | null;
  uncertainty_width?: number | null;
  uncertainty_category: IT2UncertaintyCategory;
  interval_memberships: Record<string, IT2MembershipInterval>;
  primary_interval_label: FuzzyMetricLabel;
  diagnostic_flags: string[];
};

export type IT2FuzzyInterpretationResult = {
  it2_fuzzy_version: string;
  status: IT2FuzzyInterpretationStatus;
  session_id: string;
  sport_id: string;
  drill_id: string;
  skill_level: SkillLevel;
  it2_metric_results: IT2FuzzyMetricInterpretation[];
  uncertainty_summary: IT2UncertaintySummary;
  diagnostic_flags: string[];
  created_at?: string | null;
};

export type PedagogicalDecisionStatus =
  | "COMPLETED"
  | "FAILED"
  | "NO_ACTIONABLE_FEEDBACK";

export type TeachingStrategy =
  | "single_focus_mastery"
  | "dual_focus_refinement"
  | "multi_focus_precision";

export type ToneProfile =
  | "supportive_simple"
  | "corrective_specific"
  | "technical_performance";

export type CorrectionIntensity =
  | "observe"
  | "soft"
  | "corrective"
  | "direct";

export type PedagogicalFocusItem = {
  phase_id: string;
  metric_id?: string | null;
  metric_name: string;
  severity_level: SeverityLevel;
  fuzzy_label?: FuzzyMetricLabel | null;
  dominant_label_confidence?: number | null;
  affected_body_part: string;
  priority_rank: number;
  teaching_reason: string;
  recommended_message_style: string;
};

export type PedagogicalSuppressedItem = {
  phase_id: string;
  metric_id?: string | null;
  metric_name: string;
  severity_level: SeverityLevel;
  priority_rank: number;
  suppression_reason: string;
};

export type PedagogicalDecisionResult = {
  pedagogical_version: string;
  status: PedagogicalDecisionStatus;
  session_id: string;
  sport_id: string;
  drill_id: string;
  skill_level: SkillLevel;
  teaching_strategy: TeachingStrategy;
  selected_focus_items: PedagogicalFocusItem[];
  suppressed_items: PedagogicalSuppressedItem[];
  tone_profile: ToneProfile;
  correction_intensity: CorrectionIntensity;
  learning_objective: string;
  progression_advice: string;
  diagnostic_flags: string[];
  created_at?: string | null;
};

export type OntologyReasoningStatus =
  | "COMPLETED"
  | "FAILED"
  | "NO_SIGNIFICANT_ISSUES";

export type OntologySeveritySummary = {
  severe_count: number;
  moderate_count: number;
};

export type OntologyConceptGroup = {
  metrics: string[];
  phases: string[];
  total_weight: number;
  severity_summary: OntologySeveritySummary;
};

export type OntologyBodyRegionSummary = {
  concepts: string[];
  metrics: string[];
  phases: string[];
  total_weight: number;
  severity_summary: OntologySeveritySummary;
};

export type OntologyReasoningResult = {
  ontology_version: string;
  status: OntologyReasoningStatus;
  session_id: string;
  sport_id: string;
  drill_id: string;
  skill_level: SkillLevel;
  primary_concept?: string | null;
  secondary_concepts: string[];
  concept_groups: Record<string, OntologyConceptGroup>;
  body_region_summary: Record<string, OntologyBodyRegionSummary>;
  reasoning_summary: string;
  diagnostic_flags: string[];
  created_at?: string | null;
};

export type ChoquetAggregationStatus =
  | "COMPLETED"
  | "FAILED"
  | "NO_ACTIONABLE_ISSUES";

export type ChoquetAggregatedGroup = {
  concepts: string[];
  input_values: Record<string, number>;
  choquet_score: number;
  interaction_detected: boolean;
  explanation: string;
};

export type ChoquetAggregationResult = {
  choquet_version: string;
  status: ChoquetAggregationStatus;
  session_id: string;
  sport_id: string;
  drill_id: string;
  skill_level: SkillLevel;
  concept_aggregation: Record<string, ChoquetAggregatedGroup>;
  body_region_aggregation: Record<string, ChoquetAggregatedGroup>;
  overall_choquet_score: number;
  dominant_interaction_group?: string | null;
  diagnostic_flags: string[];
  created_at?: string | null;
};

export type TemporalModelingStatus =
  | "COMPLETED"
  | "FAILED"
  | "INSUFFICIENT_DATA";

export type TemporalState =
  | "STABLE"
  | "CONTROLLED"
  | "RUSHED"
  | "JERKY"
  | "INCOMPLETE"
  | "UNCERTAIN";

export type TemporalPhaseResult = {
  phase_id: string;
  frame_count: number;
  phase_duration_ms: number;
  valid_frame_ratio: number;
  average_velocity_proxy: number;
  smoothness_proxy: number;
  acceleration_change_proxy: number;
  temporal_state: TemporalState;
  state_confidence: number;
  diagnostic_flags: string[];
};

export type TemporalTransitionResult = {
  from_phase: string;
  to_phase: string;
  transition_valid: boolean;
  transition_gap_ms: number;
  phase_order_valid: boolean;
  diagnostic_flags: string[];
};

export type TemporalModelingResult = {
  temporal_model_version: string;
  status: TemporalModelingStatus;
  session_id: string;
  sport_id: string;
  drill_id: string;
  skill_level: SkillLevel;
  phase_temporal_results: TemporalPhaseResult[];
  transition_results: TemporalTransitionResult[];
  overall_temporal_state: TemporalState;
  temporal_summary: string;
  diagnostic_flags: string[];
  created_at?: string | null;
};

export type SessionFeedback = {
  id: string;
  session_id: string;
  severity_level: SeverityLevel;
  technique_issue: string;
  coaching_cue: string;
  metric_snapshot: Record<string, unknown>;
  created_at: string;
};

export type SessionArtifact = {
  id: string;
  session_id: string;
  artifact_type: ArtifactType;
  payload_json: Record<string, unknown>;
  created_at: string;
};

export type SessionArtifactsResponse = {
  artifacts: SessionArtifact[];
  pose_sequence?: PoseSequence | null;
  perception_result?: PerceptionResult | null;
  cognition_result?: CognitionResult | null;
  evaluation_result?: DeterministicEvaluationResult | null;
  feedback_result?: DeterministicFeedbackResult | null;
  llm_feedback_result?: LLMFeedbackResult | null;
  fuzzy_interpretation_result?: FuzzyInterpretationResult | null;
  it2_fuzzy_interpretation_result?: IT2FuzzyInterpretationResult | null;
  pedagogical_decision_result?: PedagogicalDecisionResult | null;
  ontology_reasoning_result?: OntologyReasoningResult | null;
  choquet_aggregation_result?: ChoquetAggregationResult | null;
  temporal_modeling_result?: TemporalModelingResult | null;
  session_summary?: SessionSummary | null;
  feedback: SessionFeedback[];
};

export type UploadProcessingResponse = {
  session_id: string;
  status: SessionStatus;
  upload_received: boolean;
  validation: UploadValidation;
  capture_validation?: CaptureProtocolValidation;
  pose_sequence?: PoseSequenceSummary;
  perception_result?: PerceptionResult;
  cognition_result?: CognitionResult;
  evaluation_result?: DeterministicEvaluationResult;
  session_summary?: SessionSummary;
  feedback: SessionFeedback[];
  artifacts_persisted: ArtifactType[];
  next_step: string;
};

export type UploadValidationResponse = UploadProcessingResponse;

export type LiveReadinessRequest = {
  camera_permission_granted: boolean;
  lighting_ready: boolean;
  framing_ready: boolean;
  space_ready: boolean;
  client_ready: boolean;
};

export type LiveReadinessResponse = {
  camera_ready: boolean;
  lighting_ready: boolean;
  framing_ready: boolean;
  space_ready: boolean;
  warnings: string[];
};

export type LiveStartResponse = {
  session_id: string;
  status: SessionStatus;
  started: boolean;
  message: string;
  readiness: LiveReadinessResponse;
};

export type FrameBatchRequest = {
  frame_count: number;
  timestamps: number[];
  client_ready: boolean;
};

export type FrameBatchResponse = {
  session_id: string;
  accepted: boolean;
  frame_count: number;
  message: string;
};

export type LiveEndRequest = {
  final_status: Extract<SessionStatus, "COMPLETED" | "ABORTED">;
};

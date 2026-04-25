import type { SessionSummary } from "./progress";
import type { SkillLevel } from "./profile";

export type SessionInputType = "UPLOAD" | "LIVE";
export type SessionStatus = "ACTIVE" | "COMPLETED" | "ABORTED";
export type CameraView = "FRONTAL" | "LEFT_SAGITTAL" | "RIGHT_SAGITTAL";
export type DominantSide = "LEFT" | "RIGHT";

export type TrainingSession = {
  id: string;
  user_id: string;
  drill_id: string;
  sport_id: string;
  skill_level: SkillLevel;
  input_type: SessionInputType;
  camera_view?: CameraView | null;
  dominant_side?: DominantSide | null;
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
  camera_view?: CameraView;
  dominant_side?: DominantSide;
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
  | "fuzzy_interpretation_result";

export type PoseSequenceStatus = "COMPLETED" | "FAILED" | "INSUFFICIENT_DATA";

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
  priority_rank: number;
  deviation: number;
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

export type SessionInputType = "UPLOAD" | "LIVE";
export type SessionStatus = "ACTIVE" | "COMPLETED" | "ABORTED";

export type TrainingSession = {
  id: string;
  user_id: string;
  drill_id: string;
  sport_id: string;
  input_type: SessionInputType;
  status: SessionStatus;
  start_time: string;
  end_time: string | null;
  drill_name: string;
  sport_name: string;
};

export type SessionCreateRequest = {
  drill_id: string;
  input_type: SessionInputType;
};

export type UploadValidation = {
  is_valid: boolean;
  content_type: string | null;
  file_size_bytes: number;
  warnings: string[];
  errors: string[];
};

export type ArtifactType =
  | "perception_payload"
  | "cognition_result"
  | "evaluation_result";

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

export type EvaluationIssue = {
  metric: string;
  actual_score: number;
  expected_min?: number | null;
  expected_max?: number | null;
  deviation: number;
  severity_level: SeverityLevel;
  issue_label: string;
  coaching_cue: string;
};

export type DrillEvaluationResult = {
  evaluation_mode: "deterministic_scaffold";
  session_id: string;
  drill_id: string;
  drill_name: string;
  evaluator_name: string;
  metric_scores: Record<string, number>;
  issues: EvaluationIssue[];
  summary_flags: string[];
  feedback_count: number;
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
  perception_result?: PerceptionResult;
  cognition_result?: CognitionResult;
  evaluation_result?: DrillEvaluationResult;
  feedback: SessionFeedback[];
};

export type UploadProcessingResponse = {
  session_id: string;
  status: SessionStatus;
  upload_received: boolean;
  validation: UploadValidation;
  perception_result?: PerceptionResult;
  cognition_result?: CognitionResult;
  evaluation_result?: DrillEvaluationResult;
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

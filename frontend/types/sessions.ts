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

export type UploadValidationResponse = {
  session_id: string;
  status: SessionStatus;
  upload_received: boolean;
  validation: UploadValidation;
  next_step: string;
};

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

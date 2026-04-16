import { apiRequest } from "../lib/api";
import type {
  FrameBatchRequest,
  FrameBatchResponse,
  LiveEndRequest,
  LiveReadinessRequest,
  LiveStartResponse,
  SessionCreateRequest,
  TrainingSession,
  UploadValidationResponse
} from "../types/sessions";

export function createSession(payload: SessionCreateRequest) {
  return apiRequest<TrainingSession>("/sessions", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getSession(sessionId: string) {
  return apiRequest<TrainingSession>(`/sessions/${sessionId}`);
}

export function getRecentSessions(limit = 10) {
  return apiRequest<TrainingSession[]>(`/sessions/recent?limit=${limit}`);
}

export function submitSessionUpload(sessionId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<UploadValidationResponse>(`/sessions/${sessionId}/upload`, {
    method: "POST",
    body: formData
  });
}

export function startLiveSession(
  sessionId: string,
  payload: LiveReadinessRequest
) {
  return apiRequest<LiveStartResponse>(`/sessions/${sessionId}/live/start`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function submitLiveFrameBatch(
  sessionId: string,
  payload: FrameBatchRequest
) {
  return apiRequest<FrameBatchResponse>(`/sessions/${sessionId}/live/frame-batch`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function endLiveSession(sessionId: string, payload: LiveEndRequest) {
  return apiRequest<TrainingSession>(`/sessions/${sessionId}/live/end`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

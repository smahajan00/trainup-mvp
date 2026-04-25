import { apiRequest } from "../lib/api";
import type {
  DeterministicFeedbackResult,
  FrameBatchRequest,
  FrameBatchResponse,
  DeterministicEvaluationResult,
  FuzzyInterpretationResult,
  LLMFeedbackResult,
  LiveEndRequest,
  LiveReadinessRequest,
  LiveStartResponse,
  SessionArtifactsResponse,
  SessionCreateRequest,
  TrainingSession,
  UploadProcessingResponse
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

export function getSessionArtifacts(sessionId: string) {
  return apiRequest<SessionArtifactsResponse>(`/sessions/${sessionId}/artifacts`);
}

export function evaluateSession(sessionId: string) {
  return apiRequest<DeterministicEvaluationResult>(`/sessions/${sessionId}/evaluate`, {
    method: "POST"
  });
}

export function generateSessionFeedback(sessionId: string) {
  return apiRequest<DeterministicFeedbackResult>(`/sessions/${sessionId}/feedback`, {
    method: "POST"
  });
}

export function generateFuzzySessionInterpretation(sessionId: string) {
  return apiRequest<FuzzyInterpretationResult>(
    `/sessions/${sessionId}/interpret/fuzzy`,
    {
      method: "POST"
    }
  );
}

export function generateLLMSessionFeedback(sessionId: string) {
  return apiRequest<LLMFeedbackResult>(`/sessions/${sessionId}/feedback/llm`, {
    method: "POST"
  });
}

export function submitSessionUpload(sessionId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<UploadProcessingResponse>(`/sessions/${sessionId}/upload`, {
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

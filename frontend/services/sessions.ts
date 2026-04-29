import { apiRequest } from "../lib/api";
import type {
  ChoquetAggregationResult,
  DeterministicFeedbackResult,
  FrameBatchRequest,
  FrameBatchResponse,
  DeterministicEvaluationResult,
  FuzzyInterpretationResult,
  IT2FuzzyInterpretationResult,
  LLMFeedbackResult,
  LiveEndRequest,
  LiveReadinessRequest,
  LiveStartResponse,
  OntologyReasoningResult,
  PedagogicalDecisionResult,
  SessionArtifactsResponse,
  SessionCreateRequest,
  TemporalModelingResult,
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

export function runSessionEvaluation(sessionId: string) {
  return apiRequest<DeterministicEvaluationResult>(`/sessions/${sessionId}/evaluate`, {
    method: "POST"
  });
}

export function generateDeterministicSessionFeedback(sessionId: string) {
  return apiRequest<DeterministicFeedbackResult>(`/sessions/${sessionId}/feedback`, {
    method: "POST"
  });
}

export function runSessionFuzzyInterpretation(sessionId: string) {
  return apiRequest<FuzzyInterpretationResult>(
    `/sessions/${sessionId}/interpret/fuzzy`,
    {
      method: "POST"
    }
  );
}

export function runSessionIT2FuzzyInterpretation(sessionId: string) {
  return apiRequest<IT2FuzzyInterpretationResult>(
    `/sessions/${sessionId}/interpret/it2-fuzzy`,
    {
      method: "POST"
    }
  );
}

export function runSessionPedagogy(sessionId: string) {
  return apiRequest<PedagogicalDecisionResult>(`/sessions/${sessionId}/pedagogy`, {
    method: "POST"
  });
}

export function runSessionOntologyReasoning(sessionId: string) {
  return apiRequest<OntologyReasoningResult>(`/sessions/${sessionId}/ontology`, {
    method: "POST"
  });
}

export function runSessionChoquetAggregation(sessionId: string) {
  return apiRequest<ChoquetAggregationResult>(
    `/sessions/${sessionId}/aggregate/choquet`,
    {
      method: "POST"
    }
  );
}

export function runSessionTemporalModeling(sessionId: string) {
  return apiRequest<TemporalModelingResult>(`/sessions/${sessionId}/model/temporal`, {
    method: "POST"
  });
}

export function generateLLMSessionFeedback(sessionId: string) {
  return apiRequest<LLMFeedbackResult>(`/sessions/${sessionId}/feedback/llm`, {
    method: "POST"
  });
}

export function uploadSessionVideo(sessionId: string, file: File) {
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

export const evaluateSession = runSessionEvaluation;
export const generateSessionFeedback = generateDeterministicSessionFeedback;
export const generateFuzzySessionInterpretation = runSessionFuzzyInterpretation;
export const submitSessionUpload = uploadSessionVideo;

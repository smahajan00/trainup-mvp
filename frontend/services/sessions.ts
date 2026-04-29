import { apiRequest } from "../lib/api";
import type {
  AnalysisStepStatus,
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
  SessionAnalysisStep,
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

export const SESSION_ANALYSIS_PIPELINE: ReadonlyArray<{
  id: SessionAnalysisStep;
  label: string;
}> = [
  { id: "evaluation", label: "Evaluating movement" },
  { id: "fuzzy", label: "Interpreting performance" },
  { id: "it2", label: "Refining uncertainty" },
  { id: "pedagogy", label: "Selecting coaching focus" },
  { id: "ontology", label: "Mapping movement concepts" },
  { id: "choquet", label: "Combining issue patterns" },
  { id: "temporal", label: "Reviewing timing" },
  { id: "feedback", label: "Generating coaching feedback" },
  { id: "llm", label: "Enhancing coaching language" }
];

export type SessionAnalysisPipelineOutput = {
  evaluation: DeterministicEvaluationResult;
  fuzzy: FuzzyInterpretationResult;
  it2: IT2FuzzyInterpretationResult;
  pedagogy: PedagogicalDecisionResult;
  ontology: OntologyReasoningResult;
  choquet: ChoquetAggregationResult;
  temporal: TemporalModelingResult;
  feedback: DeterministicFeedbackResult;
  llm: LLMFeedbackResult;
  artifacts: SessionArtifactsResponse;
};

type RunSessionAnalysisOptions = {
  onProgress?: (update: {
    stepId: SessionAnalysisStep;
    status: AnalysisStepStatus;
  }) => void;
};

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

export async function runSessionAnalysisPipeline(
  sessionId: string,
  options: RunSessionAnalysisOptions = {}
) : Promise<SessionAnalysisPipelineOutput> {
  const { onProgress } = options;
  const results: Partial<Omit<SessionAnalysisPipelineOutput, "artifacts">> = {};

  const pipeline = [
    {
      id: "evaluation" as const,
      run: () => runSessionEvaluation(sessionId)
    },
    {
      id: "fuzzy" as const,
      run: () => runSessionFuzzyInterpretation(sessionId)
    },
    {
      id: "it2" as const,
      run: () => runSessionIT2FuzzyInterpretation(sessionId)
    },
    {
      id: "pedagogy" as const,
      run: () => runSessionPedagogy(sessionId)
    },
    {
      id: "ontology" as const,
      run: () => runSessionOntologyReasoning(sessionId)
    },
    {
      id: "choquet" as const,
      run: () => runSessionChoquetAggregation(sessionId)
    },
    {
      id: "temporal" as const,
      run: () => runSessionTemporalModeling(sessionId)
    },
    {
      id: "feedback" as const,
      run: () => generateDeterministicSessionFeedback(sessionId)
    },
    {
      id: "llm" as const,
      run: () => generateLLMSessionFeedback(sessionId)
    }
  ];

  for (const step of pipeline) {
    onProgress?.({ stepId: step.id, status: "RUNNING" });

    try {
      const result = await step.run();
      (results as Record<SessionAnalysisStep, unknown>)[step.id] = result;
      onProgress?.({ stepId: step.id, status: "COMPLETED" });
    } catch (error) {
      onProgress?.({ stepId: step.id, status: "FAILED" });
      throw error;
    }
  }

  const artifacts = await getSessionArtifacts(sessionId);
  return {
    ...(results as Omit<SessionAnalysisPipelineOutput, "artifacts">),
    artifacts
  };
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

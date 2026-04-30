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
  SessionAnalysisPipelineStatus,
  SessionAnalysisStep,
  SessionAnalysisWarning,
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

type SessionAnalysisResultKey =
  | "evaluation"
  | "fuzzy"
  | "it2"
  | "feedback"
  | "pedagogy"
  | "ontology"
  | "choquet"
  | "temporal"
  | "llm";

type SessionAnalysisPipelineStep<TResult = unknown> = {
  id: SessionAnalysisStep;
  label: string;
  service: (sessionId: string) => Promise<TResult>;
  resultKey: SessionAnalysisResultKey;
  required: boolean;
  dependencyNotes?: string;
  validate: (
    result: TResult
  ) => {
    ok: boolean;
    message?: string;
    diagnosticFlags: string[];
  };
};

type SessionAnalysisPipelineStepResults = {
  evaluation: DeterministicEvaluationResult;
  fuzzy: FuzzyInterpretationResult;
  it2: IT2FuzzyInterpretationResult;
  feedback: DeterministicFeedbackResult;
  pedagogy: PedagogicalDecisionResult;
  ontology: OntologyReasoningResult;
  choquet: ChoquetAggregationResult;
  temporal: TemporalModelingResult;
  llm: LLMFeedbackResult;
};

export type SessionAnalysisPipelineOutput =
  Partial<SessionAnalysisPipelineStepResults> & {
    status: SessionAnalysisPipelineStatus;
    completedSteps: string[];
    failedRequiredStep?: string;
    warnings: SessionAnalysisWarning[];
    artifacts?: SessionArtifactsResponse;
  };

type RunSessionAnalysisOptions = {
  onProgress?: (update: {
    stepId: SessionAnalysisStep;
    status: AnalysisStepStatus;
    warning?: SessionAnalysisWarning;
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

const REQUIRED_DEPENDENCY_FAILURE_FLAGS = [
  "MISSING_POSE_SEQUENCE",
  "MISSING_FEEDBACK_RESULT",
  "EVALUATION_NOT_COMPLETED"
];

const OPTIONAL_SUCCESS_STATUSES: Partial<Record<SessionAnalysisStep, string[]>> = {
  fuzzy: ["COMPLETED", "NO_INTERPRETABLE_METRICS", "DISABLED"],
  it2: ["COMPLETED", "NO_INTERPRETABLE_METRICS", "DISABLED"],
  pedagogy: ["COMPLETED", "NO_ACTIONABLE_FEEDBACK"],
  ontology: ["COMPLETED", "NO_SIGNIFICANT_ISSUES"],
  choquet: ["COMPLETED", "NO_ACTIONABLE_ISSUES"],
  temporal: ["COMPLETED"],
  llm: ["COMPLETED"]
};

function getErrorText(error: unknown) {
  return error instanceof Error ? error.message : "Unexpected analysis error.";
}

function getStatus(result: unknown) {
  if (result && typeof result === "object" && "status" in result) {
    const status = (result as { status?: unknown }).status;
    return typeof status === "string" ? status : null;
  }

  return null;
}

function getDiagnosticFlags(result: unknown) {
  if (!result || typeof result !== "object") {
    return [];
  }

  const resultWithFlags = result as {
    diagnostic_flags?: unknown;
    context_diagnostic_flags?: unknown;
    dominant_side_diagnostic_flags?: unknown;
  };

  const flags = [
    ...(Array.isArray(resultWithFlags.diagnostic_flags)
      ? resultWithFlags.diagnostic_flags
      : []),
    ...(Array.isArray(resultWithFlags.context_diagnostic_flags)
      ? resultWithFlags.context_diagnostic_flags
      : []),
    ...(Array.isArray(resultWithFlags.dominant_side_diagnostic_flags)
      ? resultWithFlags.dominant_side_diagnostic_flags
      : [])
  ].filter((flag): flag is string => typeof flag === "string" && flag.length > 0);

  return Array.from(new Set(flags));
}

function hasRequiredDependencyFailure(diagnosticFlags: string[]) {
  return diagnosticFlags.some(
    (flag) =>
      REQUIRED_DEPENDENCY_FAILURE_FLAGS.includes(flag) ||
      flag === "EVALUATION_STATUS:FAILED" ||
      flag.startsWith("EVALUATION_STATUS:FAILED")
  );
}

function buildStepWarning(
  step: SessionAnalysisStep | string,
  message: string,
  diagnosticFlags: string[] = []
) : SessionAnalysisWarning {
  return {
    step,
    message,
    diagnosticFlags: Array.from(new Set(diagnosticFlags))
  };
}

function addWarning(
  warnings: SessionAnalysisWarning[],
  warning: SessionAnalysisWarning
) {
  const alreadyRecorded = warnings.some(
    (existingWarning) =>
      existingWarning.step === warning.step &&
      existingWarning.message === warning.message &&
      existingWarning.diagnosticFlags.join("|") === warning.diagnosticFlags.join("|")
  );

  if (!alreadyRecorded) {
    warnings.push(warning);
  }
}

function validateEvaluationResult(result: DeterministicEvaluationResult) {
  const diagnosticFlags = getDiagnosticFlags(result);

  if (hasRequiredDependencyFailure(diagnosticFlags)) {
    return {
      ok: false,
      message: "Analysis could not be completed because evaluation dependencies were missing.",
      diagnosticFlags
    };
  }

  if (result.status !== "COMPLETED") {
    return {
      ok: false,
      message: `Analysis could not be completed because evaluation ended with status ${result.status}.`,
      diagnosticFlags
    };
  }

  return { ok: true, diagnosticFlags };
}

function validateDeterministicFeedbackResult(result: DeterministicFeedbackResult) {
  const diagnosticFlags = getDiagnosticFlags(result);

  if (hasRequiredDependencyFailure(diagnosticFlags)) {
    return {
      ok: false,
      message: "Analysis could not be completed because feedback dependencies were missing.",
      diagnosticFlags
    };
  }

  if (result.status !== "COMPLETED" && result.status !== "NO_ACTIONABLE_ISSUES") {
    return {
      ok: false,
      message: `Analysis could not be completed because feedback ended with status ${result.status}.`,
      diagnosticFlags
    };
  }

  return { ok: true, diagnosticFlags };
}

function validateOptionalResult(
  stepId: SessionAnalysisStep,
  result: unknown
) {
  const status = getStatus(result);
  const diagnosticFlags = getDiagnosticFlags(result);

  if (hasRequiredDependencyFailure(diagnosticFlags)) {
    return {
      ok: false,
      message: `${stepId} could not run because a required upstream artifact was missing.`,
      diagnosticFlags
    };
  }

  if (
    stepId === "llm" &&
    result &&
    typeof result === "object" &&
    "fallback_used" in result &&
    (result as { fallback_used?: unknown }).fallback_used === true
  ) {
    return {
      ok: false,
      message: "LLM enhancement was unavailable; deterministic coaching feedback is being shown.",
      diagnosticFlags
    };
  }

  const successStatuses = OPTIONAL_SUCCESS_STATUSES[stepId] ?? ["COMPLETED"];

  if (status && !successStatuses.includes(status)) {
    return {
      ok: false,
      message: `${stepId} ended with status ${status}.`,
      diagnosticFlags
    };
  }

  return { ok: true, diagnosticFlags };
}

function validateFinalArtifacts(artifacts: SessionArtifactsResponse) {
  if (!artifacts.evaluation_result) {
    return buildStepWarning(
      "evaluation",
      "Analysis could not be completed because the evaluation artifact is missing.",
      ["MISSING_EVALUATION_RESULT"]
    );
  }

  const evaluationValidation = validateEvaluationResult(artifacts.evaluation_result);
  if (!evaluationValidation.ok) {
    return buildStepWarning(
      "evaluation",
      evaluationValidation.message ?? "Analysis could not be completed because evaluation failed.",
      evaluationValidation.diagnosticFlags
    );
  }

  if (!artifacts.feedback_result) {
    return buildStepWarning(
      "deterministic_feedback",
      "Analysis could not be completed because deterministic feedback is missing.",
      ["MISSING_FEEDBACK_RESULT"]
    );
  }

  const feedbackValidation = validateDeterministicFeedbackResult(
    artifacts.feedback_result
  );
  if (!feedbackValidation.ok) {
    return buildStepWarning(
      "deterministic_feedback",
      feedbackValidation.message ??
        "Analysis could not be completed because deterministic feedback failed.",
      feedbackValidation.diagnosticFlags
    );
  }

  return null;
}

export const SESSION_ANALYSIS_PIPELINE: ReadonlyArray<SessionAnalysisPipelineStep> = [
  {
    id: "evaluation",
    label: "Evaluating movement",
    service: runSessionEvaluation,
    resultKey: "evaluation",
    required: true,
    dependencyNotes: "Requires a pose_sequence artifact.",
    validate: (result) =>
      validateEvaluationResult(result as DeterministicEvaluationResult)
  },
  {
    id: "fuzzy",
    label: "Interpreting performance",
    service: runSessionFuzzyInterpretation,
    resultKey: "fuzzy",
    required: false,
    dependencyNotes: "Requires completed evaluation.",
    validate: (result) => validateOptionalResult("fuzzy", result)
  },
  {
    id: "it2",
    label: "Refining uncertainty",
    service: runSessionIT2FuzzyInterpretation,
    resultKey: "it2",
    required: false,
    dependencyNotes: "Requires completed evaluation and fuzzy-compatible metrics.",
    validate: (result) => validateOptionalResult("it2", result)
  },
  {
    id: "deterministic_feedback",
    label: "Building coaching feedback",
    service: generateDeterministicSessionFeedback,
    resultKey: "feedback",
    required: true,
    dependencyNotes: "Requires completed deterministic evaluation.",
    validate: (result) =>
      validateDeterministicFeedbackResult(result as DeterministicFeedbackResult)
  },
  {
    id: "pedagogy",
    label: "Selecting coaching focus",
    service: runSessionPedagogy,
    resultKey: "pedagogy",
    required: false,
    dependencyNotes: "Requires deterministic feedback before coaching focus selection.",
    validate: (result) => validateOptionalResult("pedagogy", result)
  },
  {
    id: "ontology",
    label: "Mapping movement concepts",
    service: runSessionOntologyReasoning,
    resultKey: "ontology",
    required: false,
    dependencyNotes: "Requires deterministic feedback and evaluation context.",
    validate: (result) => validateOptionalResult("ontology", result)
  },
  {
    id: "choquet",
    label: "Combining issue patterns",
    service: runSessionChoquetAggregation,
    resultKey: "choquet",
    required: false,
    dependencyNotes: "Requires ontology reasoning and deterministic feedback.",
    validate: (result) => validateOptionalResult("choquet", result)
  },
  {
    id: "temporal",
    label: "Reviewing timing",
    service: runSessionTemporalModeling,
    resultKey: "temporal",
    required: false,
    dependencyNotes: "Requires pose sequence and evaluation phase ranges.",
    validate: (result) => validateOptionalResult("temporal", result)
  },
  {
    id: "llm",
    label: "Preparing coaching summary",
    service: generateLLMSessionFeedback,
    resultKey: "llm",
    required: false,
    dependencyNotes: "Runs last and falls back to deterministic feedback when unavailable.",
    validate: (result) => validateOptionalResult("llm", result)
  }
];

export async function runSessionAnalysisPipeline(
  sessionId: string,
  options: RunSessionAnalysisOptions = {}
) : Promise<SessionAnalysisPipelineOutput> {
  const { onProgress } = options;
  const results: Partial<SessionAnalysisPipelineStepResults> = {};
  const completedSteps: string[] = [];
  const warnings: SessionAnalysisWarning[] = [];

  async function buildFailedResult(
    failedRequiredStep: string,
    warning: SessionAnalysisWarning
  ) : Promise<SessionAnalysisPipelineOutput> {
    addWarning(warnings, warning);

    let artifacts: SessionArtifactsResponse | undefined;
    try {
      artifacts = await getSessionArtifacts(sessionId);
    } catch {
      artifacts = undefined;
    }

    return {
      ...results,
      status: "FAILED",
      completedSteps,
      failedRequiredStep,
      warnings,
      artifacts
    };
  }

  for (const step of SESSION_ANALYSIS_PIPELINE) {
    onProgress?.({ stepId: step.id, status: "RUNNING" });

    try {
      const result = await step.service(sessionId);
      (results as Record<SessionAnalysisResultKey, unknown>)[step.resultKey] = result;
      const validation = step.validate(result);

      if (!validation.ok) {
        const warning = buildStepWarning(
          step.id,
          validation.message ?? `${step.label} did not complete successfully.`,
          validation.diagnosticFlags
        );

        if (step.required) {
          onProgress?.({ stepId: step.id, status: "FAILED", warning });
          return buildFailedResult(step.id, warning);
        }

        addWarning(warnings, warning);
        onProgress?.({ stepId: step.id, status: "WARNING", warning });
        continue;
      }

      completedSteps.push(step.id);
      onProgress?.({ stepId: step.id, status: "COMPLETED" });
    } catch (error) {
      const warning = buildStepWarning(
        step.id,
        `${step.label} failed: ${getErrorText(error)}`,
        []
      );

      if (step.required) {
        onProgress?.({ stepId: step.id, status: "FAILED", warning });
        return buildFailedResult(step.id, warning);
      }

      addWarning(warnings, warning);
      onProgress?.({ stepId: step.id, status: "WARNING", warning });
    }
  }

  let artifacts: SessionArtifactsResponse;
  try {
    artifacts = await getSessionArtifacts(sessionId);
  } catch (error) {
    const warning = buildStepWarning(
      "artifacts",
      `Analysis artifacts could not be loaded: ${getErrorText(error)}`,
      []
    );
    addWarning(warnings, warning);

    return {
      ...results,
      status: "FAILED",
      completedSteps,
      failedRequiredStep: "artifacts",
      warnings
    };
  }

  const artifactFailure = validateFinalArtifacts(artifacts);
  if (artifactFailure) {
    addWarning(warnings, artifactFailure);

    return {
      ...results,
      status: "FAILED",
      completedSteps,
      failedRequiredStep: artifactFailure.step,
      warnings,
      artifacts
    };
  }

  return {
    ...results,
    status: warnings.length ? "COMPLETED_WITH_WARNINGS" : "COMPLETED",
    completedSteps,
    warnings,
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

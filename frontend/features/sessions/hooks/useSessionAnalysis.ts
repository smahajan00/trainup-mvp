import { useState } from "react";

import { getErrorMessage } from "../../../lib/api";
import {
  runSessionAnalysisPipeline,
  SESSION_ANALYSIS_PIPELINE
} from "../../../services/sessions";
import type {
  AnalysisProgressStep,
  AnalysisState,
  SessionArtifactsResponse,
  SessionAnalysisStep
} from "../../../types/sessions";

function buildAnalysisSteps(): AnalysisProgressStep[] {
  return SESSION_ANALYSIS_PIPELINE.map((step) => ({
    id: step.id,
    label: step.label,
    status: "PENDING"
  }));
}

function updateStepStatus(
  steps: AnalysisProgressStep[],
  stepId: SessionAnalysisStep,
  status: AnalysisProgressStep["status"]
) : AnalysisProgressStep[] {
  return steps.map((step) =>
    step.id === stepId
      ? ({ ...step, status } satisfies AnalysisProgressStep)
      : step.status === "RUNNING" && status === "RUNNING"
        ? ({ ...step, status: "COMPLETED" } satisfies AnalysisProgressStep)
        : step
  );
}

function deriveAnalysisFailureMessage(artifacts: SessionArtifactsResponse) {
  const evaluationStatus = artifacts.evaluation_result?.status;

  if (!evaluationStatus || evaluationStatus !== "COMPLETED") {
    return "Analysis failed. Try again.";
  }

  if (artifacts.feedback_result?.status === "FAILED") {
    return "Analysis failed. Try again.";
  }

  if (artifacts.llm_feedback_result?.status === "FAILED") {
    return "Analysis failed. Try again.";
  }

  return null;
}

export function useSessionAnalysis(
  sessionId: string,
  onComplete: (artifacts: SessionArtifactsResponse) => void
) {
  const [analysisState, setAnalysisState] = useState<AnalysisState>("IDLE");
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisSteps, setAnalysisSteps] = useState<AnalysisProgressStep[]>(
    buildAnalysisSteps
  );

  async function runAnalysis() {
    setAnalysisState("RUNNING");
    setAnalysisError(null);
    setAnalysisSteps(buildAnalysisSteps());

    try {
      const result = await runSessionAnalysisPipeline(sessionId, {
        onProgress: ({ stepId, status }) => {
          setAnalysisSteps((currentSteps) =>
            updateStepStatus(currentSteps, stepId, status)
          );
        }
      });

      onComplete(result.artifacts);

      const failureMessage = deriveAnalysisFailureMessage(result.artifacts);
      if (failureMessage) {
        setAnalysisState("FAILED");
        setAnalysisError(failureMessage);
        return result;
      }

      setAnalysisState("COMPLETED");
      return result;
    } catch (error) {
      setAnalysisState("FAILED");
      setAnalysisError(getErrorMessage(error));
      return null;
    }
  }

  function resetAnalysis() {
    setAnalysisState("IDLE");
    setAnalysisError(null);
    setAnalysisSteps(buildAnalysisSteps());
  }

  return {
    analysisError,
    analysisState,
    analysisSteps,
    resetAnalysis,
    runAnalysis
  };
}

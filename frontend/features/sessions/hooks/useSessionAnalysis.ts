import { useState } from "react";

import { getErrorMessage } from "../../../lib/api";
import {
  runSessionAnalysisPipeline,
  SESSION_ANALYSIS_PIPELINE
} from "../../../services/sessions";
import type {
  AnalysisProgressStep,
  AnalysisState,
  SessionAnalysisWarning,
  SessionArtifactsResponse,
  SessionAnalysisStep
} from "../../../types/sessions";

function buildAnalysisSteps(): AnalysisProgressStep[] {
  return SESSION_ANALYSIS_PIPELINE.map((step) => ({
    id: step.id,
    label: step.label,
    required: step.required,
    dependencyNotes: step.dependencyNotes,
    status: "PENDING"
  }));
}

function updateStepStatus(
  steps: AnalysisProgressStep[],
  stepId: SessionAnalysisStep,
  status: AnalysisProgressStep["status"],
  warning?: SessionAnalysisWarning
) : AnalysisProgressStep[] {
  return steps.map((step) =>
    step.id === stepId
      ? ({
          ...step,
          status,
          warning: warning?.message ?? null
        } satisfies AnalysisProgressStep)
      : step.status === "RUNNING" && status === "RUNNING"
        ? ({ ...step, status: "COMPLETED" } satisfies AnalysisProgressStep)
        : step
  );
}

function derivePoseFailureMessage(artifacts?: SessionArtifactsResponse) {
  const poseSequence = artifacts?.pose_sequence;
  const poseFlags = poseSequence?.diagnostic_flags ?? [];

  if (
    poseSequence &&
    (poseSequence.status === "FAILED" || poseSequence.status === "INSUFFICIENT_DATA")
  ) {
    if (
      poseFlags.includes("POSE_EXTRACTION_FAILURE") ||
      poseFlags.includes("VIDEO_UNREADABLE") ||
      poseFlags.includes("ZERO_FRAMES") ||
      poseFlags.includes("ZERO_VALID_FRAMES")
    ) {
      return "Pose extraction failed. Try MP4 format, better lighting, or check that the full body is visible.";
    }
  }

  return null;
}

function getRequiredFailureMessage(
  failedRequiredStep: string | undefined,
  warnings: SessionAnalysisWarning[],
  artifacts?: SessionArtifactsResponse
) {
  const poseFailureMessage = derivePoseFailureMessage(artifacts);
  if (poseFailureMessage) {
    return poseFailureMessage;
  }

  const matchingWarning =
    warnings.find((warning) => warning.step === failedRequiredStep) ??
    warnings[warnings.length - 1] ??
    null;

  if (failedRequiredStep === "evaluation") {
    return (
      matchingWarning?.message ??
      "Analysis could not be completed because evaluation failed."
    );
  }

  if (failedRequiredStep === "deterministic_feedback") {
    return (
      matchingWarning?.message ??
      "Analysis could not be completed because feedback failed."
    );
  }

  return matchingWarning?.message ?? "Analysis failed. Try again.";
}

export function useSessionAnalysis(
  sessionId: string,
  onComplete: (artifacts: SessionArtifactsResponse) => void
) {
  const [analysisState, setAnalysisState] = useState<AnalysisState>("IDLE");
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisWarnings, setAnalysisWarnings] = useState<SessionAnalysisWarning[]>(
    []
  );
  const [currentStep, setCurrentStep] = useState<SessionAnalysisStep | null>(null);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [analysisSteps, setAnalysisSteps] = useState<AnalysisProgressStep[]>(
    buildAnalysisSteps
  );

  async function runAnalysis() {
    setAnalysisState("RUNNING");
    setAnalysisError(null);
    setAnalysisWarnings([]);
    setCurrentStep(null);
    setCompletedSteps([]);
    setAnalysisSteps(buildAnalysisSteps());

    try {
      const result = await runSessionAnalysisPipeline(sessionId, {
        onProgress: ({ stepId, status, warning }) => {
          setCurrentStep(status === "RUNNING" ? stepId : null);
          if (status === "COMPLETED") {
            setCompletedSteps((currentSteps) =>
              currentSteps.includes(stepId)
                ? currentSteps
                : [...currentSteps, stepId]
            );
          }

          if (warning) {
            setAnalysisWarnings((currentWarnings) => [
              ...currentWarnings.filter(
                (currentWarning) =>
                  currentWarning.step !== warning.step ||
                  currentWarning.message !== warning.message
              ),
              warning
            ]);
          }

          setAnalysisSteps((currentSteps) =>
            updateStepStatus(currentSteps, stepId, status, warning)
          );
        }
      });

      if (result.artifacts) {
        onComplete(result.artifacts);
      }

      setCurrentStep(null);
      setCompletedSteps(result.completedSteps);
      setAnalysisWarnings(result.warnings);

      if (result.status === "FAILED") {
        setAnalysisState("FAILED");
        setAnalysisError(
          getRequiredFailureMessage(
            result.failedRequiredStep,
            result.warnings,
            result.artifacts
          )
        );
        return result;
      }

      setAnalysisState(result.status);
      return result;
    } catch (error) {
      setAnalysisState("FAILED");
      setAnalysisError(getErrorMessage(error));
      setCurrentStep(null);
      return null;
    }
  }

  function resetAnalysis() {
    setAnalysisState("IDLE");
    setAnalysisError(null);
    setAnalysisWarnings([]);
    setCurrentStep(null);
    setCompletedSteps([]);
    setAnalysisSteps(buildAnalysisSteps());
  }

  return {
    analysisError,
    analysisState,
    analysisSteps,
    analysisWarnings,
    completedSteps,
    currentStep,
    resetAnalysis,
    runAnalysis
  };
}

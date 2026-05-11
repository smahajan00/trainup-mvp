import { CheckCircle2, CircleAlert, CircleDashed, LoaderCircle } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { SectionTitle } from "../../app-shell/components/SectionTitle";
import type {
  AnalysisProgressStep,
  AnalysisState,
  SessionAnalysisStep,
  SessionAnalysisWarning
} from "../../../types/sessions";

type AnalysisProgressCardProps = {
  analysisState: AnalysisState;
  analysisSteps: AnalysisProgressStep[];
  analysisError?: string | null;
  analysisWarnings?: SessionAnalysisWarning[];
  currentStep?: SessionAnalysisStep | null;
};

const GROUPS = [
  {
    id: "movement",
    title: "Evaluating movement",
    stepIds: ["evaluation"]
  },
  {
    id: "interpretation",
    title: "Interpreting performance",
    stepIds: ["fuzzy", "it2"]
  },
  {
    id: "feedback",
    title: "Building coaching feedback",
    stepIds: ["deterministic_feedback"]
  },
  {
    id: "advanced",
    title: "Adding advanced insights",
    stepIds: ["pedagogy", "ontology", "choquet", "temporal"]
  },
  {
    id: "summary",
    title: "Refining coaching feedback",
    stepIds: ["llm"]
  }
] as const;

function getGroupStatus(
  analysisSteps: AnalysisProgressStep[],
  stepIds: readonly string[]
) {
  const steps = analysisSteps.filter((step) => stepIds.includes(step.id));

  if (steps.some((step) => step.status === "FAILED")) {
    return "FAILED";
  }

  if (steps.some((step) => step.status === "RUNNING")) {
    return "RUNNING";
  }

  if (steps.some((step) => step.status === "WARNING")) {
    return "WARNING";
  }

  if (steps.length && steps.every((step) => step.status === "COMPLETED")) {
    return "COMPLETED";
  }

  return "PENDING";
}

export function AnalysisProgressCard({
  analysisState,
  analysisSteps,
  analysisError,
  analysisWarnings = [],
  currentStep
}: AnalysisProgressCardProps) {
  const activeStep =
    analysisSteps.find((step) => step.id === currentStep) ??
    analysisSteps.find((step) => step.status === "RUNNING") ??
    null;
  const hasWarnings =
    analysisState === "COMPLETED_WITH_WARNINGS" || analysisWarnings.length > 0;

  return (
    <InfoCard>
      <SectionTitle
        eyebrow="Analysis"
        title="Analyze Performance"
        description={
          analysisState === "RUNNING"
            ? activeStep?.id === "llm"
              ? "Refining coaching feedback..."
              : "Breaking down your movement..."
            : analysisState === "COMPLETED"
              ? "Performance breakdown complete."
              : analysisState === "COMPLETED_WITH_WARNINGS"
                ? "Core coaching feedback is ready with advanced insight warnings."
              : analysisState === "FAILED"
                ? "Analysis could not be completed because evaluation/feedback failed."
                : "Run the full performance pipeline when your input is ready."
        }
      />

      <div className="mt-6 flex flex-wrap gap-2">
        <Badge
          variant={
            analysisState === "COMPLETED"
              ? "success"
              : analysisState === "COMPLETED_WITH_WARNINGS"
                ? "warning"
              : analysisState === "FAILED"
                ? "danger"
                : analysisState === "RUNNING"
                  ? "warning"
                  : "slate"
          }
        >
          {analysisState}
        </Badge>
        {activeStep ? <Badge variant="slate">{activeStep.label}</Badge> : null}
      </div>

      <div className="mt-6 space-y-3">
        {GROUPS.map((group) => {
          const status = getGroupStatus(analysisSteps, group.stepIds);

          return (
            <div
              key={group.id}
              className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 transition-colors duration-300"
            >
              {status === "COMPLETED" ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-300" />
              ) : status === "FAILED" ? (
                <CircleAlert className="h-5 w-5 text-rose-300" />
              ) : status === "WARNING" ? (
                <CircleAlert className="h-5 w-5 text-amber-300" />
              ) : status === "RUNNING" ? (
                <LoaderCircle className="h-5 w-5 animate-spin text-primary" />
              ) : (
                <CircleDashed className="h-5 w-5 text-white/40" />
              )}
              <div>
                <span className="text-sm text-white/90">{group.title}</span>
                {status === "WARNING" ? (
                  <p className="mt-1 text-xs text-amber-100/80">
                    Warning: optional step did not complete cleanly.
                  </p>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>

      {hasWarnings && analysisState !== "FAILED" ? (
        <div className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-4 text-sm leading-7 text-amber-100">
          <p>
            Some advanced insights could not be generated, but your core coaching feedback is ready.
          </p>
          {analysisWarnings.length ? (
            <ul className="mt-3 space-y-2">
              {analysisWarnings.map((warning) => (
                <li key={`${warning.step}-${warning.message}`}>
                  {warning.message}
                  {warning.diagnosticFlags.length
                    ? ` (${warning.diagnosticFlags.join(", ")})`
                    : ""}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {analysisError ? (
        <div className="mt-6 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-4 text-sm leading-7 text-rose-100">
          {analysisError}
        </div>
      ) : null}
    </InfoCard>
  );
}

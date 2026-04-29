import { CheckCircle2, CircleAlert, CircleDashed, LoaderCircle } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { SectionTitle } from "../../app-shell/components/SectionTitle";
import type { AnalysisProgressStep, AnalysisState } from "../../../types/sessions";

type AnalysisProgressCardProps = {
  analysisState: AnalysisState;
  analysisSteps: AnalysisProgressStep[];
  analysisError?: string | null;
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
    stepIds: ["fuzzy", "it2", "pedagogy", "ontology", "choquet", "temporal"]
  },
  {
    id: "coaching",
    title: "Generating coaching feedback",
    stepIds: ["feedback", "llm"]
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

  if (steps.every((step) => step.status === "COMPLETED")) {
    return "COMPLETED";
  }

  if (steps.some((step) => step.status === "RUNNING")) {
    return "RUNNING";
  }

  return "PENDING";
}

export function AnalysisProgressCard({
  analysisState,
  analysisSteps,
  analysisError
}: AnalysisProgressCardProps) {
  const activeStep =
    analysisSteps.find((step) => step.status === "RUNNING") ?? null;

  return (
    <InfoCard>
      <SectionTitle
        eyebrow="Analysis"
        title="Analyze Session"
        description={
          analysisState === "RUNNING"
            ? "Analyzing your session..."
            : analysisState === "COMPLETED"
              ? "Analysis complete."
              : analysisState === "FAILED"
                ? "Analysis failed. Try again."
                : "Run the full analysis pipeline when your input is ready."
        }
      />

      <div className="mt-6 flex flex-wrap gap-2">
        <Badge
          variant={
            analysisState === "COMPLETED"
              ? "success"
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
              className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4"
            >
              {status === "COMPLETED" ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-300" />
              ) : status === "FAILED" ? (
                <CircleAlert className="h-5 w-5 text-rose-300" />
              ) : status === "RUNNING" ? (
                <LoaderCircle className="h-5 w-5 animate-spin text-primary" />
              ) : (
                <CircleDashed className="h-5 w-5 text-white/40" />
              )}
              <span className="text-sm text-white/90">{group.title}</span>
            </div>
          );
        })}
      </div>

      {analysisError ? (
        <div className="mt-6 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-4 text-sm leading-7 text-rose-100">
          {analysisError}
        </div>
      ) : null}
    </InfoCard>
  );
}

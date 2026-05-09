import { Badge } from "../../../components/ui/badge";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { SectionTitle } from "../../app-shell/components/SectionTitle";

type ImprovementPlanCardProps = {
  focusItems: string[];
  learningObjective?: string | null;
  progressionAdvice?: string | null;
  correctionIntensity?: string | null;
  improvementSuggestions: string[];
  skillLevelLabel: string;
};

export function ImprovementPlanCard({
  focusItems,
  learningObjective,
  progressionAdvice,
  correctionIntensity,
  improvementSuggestions,
  skillLevelLabel
}: ImprovementPlanCardProps) {
  const primaryFocus = focusItems[0] ?? null;
  const supportingFocusItems = focusItems.slice(1);

  return (
    <InfoCard className="p-5 sm:p-6">
      <SectionTitle
        eyebrow="Plan"
        title="Improvement Plan"
        description="A focused plan for the next few reps."
      />

      <div className="mt-5 grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-2xl border border-primary/18 bg-primary/10 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-[10px] uppercase tracking-[0.2em] text-primary">
              Focus
            </p>
            <Badge variant="slate">{skillLevelLabel}</Badge>
          </div>
          {primaryFocus ? (
            <>
              <p className="mt-3 break-words text-base font-semibold leading-7 text-white">
                {primaryFocus}
              </p>
              {supportingFocusItems.length ? (
                <ul className="mt-3 space-y-1 text-sm leading-6 text-white/78">
                  {supportingFocusItems.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
            </>
          ) : (
            <p className="mt-3 text-sm leading-6 text-white/85">
              Analyze a session to unlock coaching cues.
            </p>
          )}

          {learningObjective ? (
            <div className="mt-4 rounded-2xl border border-white/10 bg-background-dark/35 px-4 py-3">
              <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
                Learning objective
              </p>
              <p className="mt-2 text-sm leading-6 text-white/85">
                {learningObjective}
              </p>
            </div>
          ) : null}
        </div>

        <div className="grid gap-4">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
              Coaching intensity
            </p>
            <div className="mt-3">
              <Badge variant="accent">{correctionIntensity ?? "Balanced"}</Badge>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
              Progression advice
            </p>
            <p className="mt-2 text-sm leading-6 text-white/85">
              {progressionAdvice ?? "Log a few more analyzed sessions to unlock progression guidance."}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
          Next reps
        </p>
        {improvementSuggestions.length ? (
          <ul className="mt-3 grid gap-2 text-sm leading-6 text-white/85 lg:grid-cols-2">
            {improvementSuggestions.map((suggestion) => (
              <li
                key={suggestion}
                className="rounded-2xl border border-white/10 bg-background-dark/35 px-4 py-3"
              >
                {suggestion}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm leading-6 text-white/85">
            Improvement suggestions will appear after coaching feedback is generated.
          </p>
        )}
      </div>
    </InfoCard>
  );
}

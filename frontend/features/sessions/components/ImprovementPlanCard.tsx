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
  const coachCue = improvementSuggestions[0] ?? primaryFocus ?? null;
  const nextReps = improvementSuggestions.slice(0, 3);

  return (
    <InfoCard className="p-5 sm:p-6">
      <SectionTitle
        eyebrow="Plan"
        title="Improvement Plan"
        description="Keep the next set simple: one focus, one correction, three cleaner reps."
      />

      <div className="mt-5 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="rounded-2xl border border-primary/18 bg-[linear-gradient(135deg,rgba(255,122,0,0.14),rgba(255,255,255,0.035))] p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-[10px] uppercase tracking-[0.2em] text-primary">
              Focus
            </p>
            <Badge variant="slate">{skillLevelLabel}</Badge>
          </div>
          {primaryFocus ? (
            <>
              <p className="mt-3 break-words font-display text-xl font-bold leading-7 text-white">
                {primaryFocus}
              </p>
            </>
          ) : (
            <p className="mt-3 text-sm leading-6 text-white/85">
              Analyze a session to unlock coaching cues.
            </p>
          )}

          <div className="mt-4 rounded-2xl border border-white/10 bg-background-dark/35 px-4 py-3">
            <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
              Coach cue
            </p>
            <p className="mt-2 text-sm leading-6 text-white/85">
              {coachCue ?? "Repeat the same clean shape before adding speed."}
            </p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
              Drill correction
            </p>
            <p className="mt-2 text-sm leading-6 text-white/85">
              {learningObjective ?? "Make the correction at a controlled pace before increasing intensity."}
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
              Progression
            </p>
            <p className="mt-2 text-sm leading-6 text-white/85">
              {progressionAdvice ?? "Log a few more analyzed sessions to unlock progression guidance."}
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 md:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
                Coaching intensity
              </p>
              <Badge variant="accent">{correctionIntensity ?? "Balanced"}</Badge>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
          Next 3 reps
        </p>
        {nextReps.length ? (
          <ul className="mt-3 grid gap-2 text-sm leading-6 text-white/85 lg:grid-cols-2">
            {nextReps.map((suggestion, index) => (
              <li
                key={suggestion}
                className="rounded-2xl border border-white/10 bg-background-dark/35 px-4 py-3"
              >
                <span className="mr-2 font-semibold text-primary">Rep {index + 1}:</span>
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

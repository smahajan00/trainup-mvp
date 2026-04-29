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
  return (
    <InfoCard>
      <SectionTitle
        eyebrow="Plan"
        title="Improvement Plan"
        description={`This ${skillLevelLabel.toLowerCase()} session plan keeps the next focus areas concise, coachable, and easy to repeat.`}
      />

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Focus items
            </p>
          {focusItems.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {focusItems.map((item) => (
                <Badge key={item} variant="accent">
                  {item}
                </Badge>
              ))}
            </div>
          ) : (
              <p className="mt-3 text-sm leading-6 text-white/85">
                Analyze a session to unlock coaching cues.
              </p>
            )}

          {learningObjective ? (
            <div className="mt-5">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Learning objective
              </p>
              <p className="mt-3 text-sm leading-6 text-white/85">
                {learningObjective}
              </p>
            </div>
          ) : null}
        </div>

        <div className="grid gap-4">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Coaching intensity
            </p>
            <p className="mt-3 text-sm font-semibold text-white">
              {correctionIntensity ?? "Balanced"}
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Progression advice
            </p>
            <p className="mt-3 text-sm leading-6 text-white/85">
              {progressionAdvice ?? "Log a few more analyzed sessions to unlock progression guidance."}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
        <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
          Next reps
        </p>
        {improvementSuggestions.length ? (
          <ul className="mt-3 space-y-2 text-sm leading-6 text-white/85">
            {improvementSuggestions.map((suggestion) => (
              <li key={suggestion}>{suggestion}</li>
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

import { Badge } from "../../../components/ui/badge";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { SectionTitle } from "../../app-shell/components/SectionTitle";
import {
  dedupeCoachingTexts,
  professionalizeCoachingCopy
} from "./session-results-utils";

type ImprovementPlanCardProps = {
  focusItems: string[];
  learningObjective?: string | null;
  progressionAdvice?: string | null;
  correctionIntensity?: string | null;
  improvementSuggestions: string[];
  skillLevelLabel: string;
  excludedTexts?: string[];
};

function compactPriorityText(value: string) {
  const firstSentence = value.split(/(?<=[.!?])\s+/)[0]?.trim() || value;

  if (firstSentence.length <= 150) {
    return firstSentence;
  }

  return `${firstSentence.slice(0, 147).trim()}...`;
}

export function ImprovementPlanCard({
  focusItems,
  learningObjective,
  progressionAdvice,
  correctionIntensity,
  improvementSuggestions,
  skillLevelLabel,
  excludedTexts = []
}: ImprovementPlanCardProps) {
  const primaryFocus = focusItems[0] ?? null;
  const priorityItems = dedupeCoachingTexts(
    [
      ...focusItems,
      ...improvementSuggestions,
      learningObjective,
      progressionAdvice
    ].map(professionalizeCoachingCopy),
    excludedTexts.map(professionalizeCoachingCopy)
  )
    .map(compactPriorityText)
    .slice(0, 3);
  const displayPrimaryFocus = professionalizeCoachingCopy(primaryFocus);

  return (
    <InfoCard className="p-5 sm:p-6">
      <SectionTitle
        eyebrow="Plan"
        title="Training Priorities"
        description="Concise priorities for the next training block."
      />

      <div className="mt-5 rounded-2xl border border-primary/18 bg-[linear-gradient(135deg,rgba(255,122,0,0.12),rgba(255,255,255,0.035))] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-[10px] uppercase tracking-[0.2em] text-primary">
            Priority Focus
          </p>
          <div className="flex flex-wrap gap-2">
            <Badge variant="slate">{skillLevelLabel}</Badge>
            <Badge variant="accent">{correctionIntensity ?? "Balanced"}</Badge>
          </div>
        </div>
        {displayPrimaryFocus ? (
          <p className="mt-3 max-w-3xl break-words font-display text-xl font-bold leading-7 text-white">
            {displayPrimaryFocus}
          </p>
        ) : (
          <p className="mt-3 text-sm leading-6 text-white/85">
            Analyze a session to unlock training priorities.
          </p>
        )}
      </div>

      <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
        {priorityItems.length ? (
          <ul className="grid gap-2 text-sm leading-6 text-white/85">
            {priorityItems.map((item) => (
              <li key={item} className="flex gap-3">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm leading-6 text-white/85">
            Training priorities will appear after coaching feedback is generated.
          </p>
        )}
      </div>
    </InfoCard>
  );
}

import { Badge } from "../../../components/ui/badge";
import { InfoCard } from "../../app-shell/components/InfoCard";
import type { SeverityLevel } from "../../../types/sessions";
import { getSeverityVariant } from "./session-results-utils";

type CoachingFeedbackCardProps = {
  title: string;
  severity?: SeverityLevel | null;
  whatHappened: string;
  whyItHappened: string;
  whatToFix: string;
  nextAction: string;
  isEnhanced: boolean;
  backupNote?: string | null;
};

export function CoachingFeedbackCard({
  title,
  severity,
  whatHappened,
  whyItHappened,
  whatToFix,
  nextAction,
  isEnhanced,
  backupNote
}: CoachingFeedbackCardProps) {
  return (
    <InfoCard className="h-full border-white/10 p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
            Coaching cue
          </p>
          <h3 className="mt-2 line-clamp-2 font-display text-2xl font-bold text-white">
            {title}
          </h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={isEnhanced ? "success" : "slate"}>
            {isEnhanced ? "AI-enhanced" : "Rule-based"}
          </Badge>
          {severity ? (
            <Badge variant={getSeverityVariant(severity)}>{severity}</Badge>
          ) : null}
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <div className="space-y-3">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
              What happened
            </p>
            <p className="mt-2 text-sm leading-6 text-white/85">{whatHappened}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
              Why it happened
            </p>
            <p className="mt-2 text-sm leading-6 text-white/85">{whyItHappened}</p>
          </div>
        </div>

        <div className="space-y-3">
          <div className="rounded-2xl border border-primary/20 bg-primary/10 p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-primary">
              What to fix
            </p>
            <p className="mt-2 text-sm leading-6 text-white/90">{whatToFix}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
              Next action
            </p>
            <p className="mt-2 text-sm leading-6 text-white/85">{nextAction}</p>
          </div>
        </div>
      </div>

      {backupNote ? (
        <div className="mt-4 rounded-2xl border border-primary/15 bg-primary/10 px-4 py-4 text-sm leading-6 text-white/85">
          <span className="font-semibold text-white">Baseline cue:</span>{" "}
          {backupNote}
        </div>
      ) : null}
    </InfoCard>
  );
}

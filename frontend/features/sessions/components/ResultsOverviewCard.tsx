import { Activity, AlertTriangle, Gauge, Sparkles } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { SectionTitle } from "../../app-shell/components/SectionTitle";

type OverviewStatus = {
  label: string;
  variant: "success" | "warning" | "danger";
};

type ResultsOverviewCardProps = {
  overallScore: string;
  overallScoreValue?: number | null;
  strongestArea: string;
  mainLimitation: string;
  poseQualitySummary: string;
  movementConcept?: string | null;
};

function buildOverviewStatus(score?: number | null): OverviewStatus | null {
  if (score === undefined || score === null) {
    return null;
  }

  const scorePercent = score <= 1 ? score * 100 : score;

  if (scorePercent >= 85) {
    return { label: "STRONG", variant: "success" };
  }

  if (scorePercent >= 70) {
    return { label: "GOOD", variant: "success" };
  }

  if (scorePercent >= 50) {
    return { label: "NEEDS WORK", variant: "warning" };
  }

  return { label: "HIGH PRIORITY", variant: "danger" };
}

export function ResultsOverviewCard({
  overallScore,
  overallScoreValue,
  strongestArea,
  mainLimitation,
  poseQualitySummary,
  movementConcept
}: ResultsOverviewCardProps) {
  const overviewStatus = buildOverviewStatus(overallScoreValue);

  return (
    <InfoCard>
      <SectionTitle
        eyebrow="Results"
        title="Performance Overview"
        description="Start with the quick read, then move into the coaching cues that matter most."
      />

      <div className="mt-6 flex flex-wrap gap-2">
        {overviewStatus ? (
          <Badge variant={overviewStatus.variant}>{overviewStatus.label}</Badge>
        ) : null}
        {movementConcept ? <Badge variant="slate">{movementConcept}</Badge> : null}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-4">
        <div className="rounded-2xl border border-primary/20 bg-primary/10 p-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-primary/25 bg-primary/10 text-primary">
            <Gauge className="h-5 w-5" />
          </div>
          <p className="mt-4 text-xs uppercase tracking-[0.22em] text-primary/80">
            Overall score
          </p>
          <p className="mt-3 text-3xl font-bold text-white">{overallScore}</p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-emerald-400/20 bg-emerald-500/10 text-emerald-200">
            <Sparkles className="h-5 w-5" />
          </div>
          <p className="mt-4 text-xs uppercase tracking-[0.22em] text-muted-gray">
            Strongest area
          </p>
          <p className="mt-3 text-sm font-semibold leading-6 text-white">
            {strongestArea}
          </p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-amber-400/20 bg-amber-500/10 text-amber-200">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <p className="mt-4 text-xs uppercase tracking-[0.22em] text-muted-gray">
            Main limitation
          </p>
          <p className="mt-3 text-sm font-semibold leading-6 text-white">
            {mainLimitation}
          </p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] text-white/80">
            <Activity className="h-5 w-5" />
          </div>
          <p className="mt-4 text-xs uppercase tracking-[0.22em] text-muted-gray">
            Pose quality
          </p>
          <p className="mt-3 text-sm leading-6 text-white/85">
            {poseQualitySummary}
          </p>
        </div>
      </div>
    </InfoCard>
  );
}

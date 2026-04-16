"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, PlayCircle, UploadCloud } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { CTAButton } from "../../../components/ui/cta-button";
import { SkeletonLoader } from "../../../components/ui/skeleton-loader";
import { AppShell } from "../../../features/app-shell/components/AppShell";
import { EmptyState } from "../../../features/app-shell/components/EmptyState";
import { InfoCard } from "../../../features/app-shell/components/InfoCard";
import { SectionTitle } from "../../../features/app-shell/components/SectionTitle";
import {
  formatEnumLabel,
  formatTokenLabel
} from "../../../lib/formatters";
import { getDrillById } from "../../../services/drills";
import type { DrillDetail } from "../../../types/drills";

function DrillDetailContent({ drillId }: { drillId: string }) {
  const [drill, setDrill] = useState<DrillDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    async function loadDrill() {
      setError(null);

      try {
        const drillDetail = await getDrillById(drillId);
        if (!ignore) {
          setDrill(drillDetail);
        }
      } catch (loadError) {
        if (!ignore) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load drill details."
          );
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    loadDrill();

    return () => {
      ignore = true;
    };
  }, [drillId]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader className="h-72" />
        <div className="grid gap-5 xl:grid-cols-2">
          <SkeletonLoader className="h-64" />
          <SkeletonLoader className="h-64" />
        </div>
        <SkeletonLoader className="h-72" />
      </div>
    );
  }

  if (error || !drill) {
    return (
      <EmptyState
        icon={PlayCircle}
        title="Drill detail unavailable"
        description={error ?? "We couldn't load this drill right now."}
        action={
          <CTAButton asChild>
            <Link href="/sports">Back to Sports</Link>
          </CTAButton>
        }
      />
    );
  }

  const metrics = drill.target_metrics.metrics ?? [];
  const phases = drill.reference_payload.phases ?? [];
  const joints = drill.reference_payload.tracked_joints ?? [];
  const primaryFocus = drill.coaching_rules.primary_focus ?? [];
  const positiveCues = drill.coaching_rules.positive_cues ?? [];
  const recommendationTemplates =
    drill.coaching_rules.recommendation_templates ?? [];
  const idealRanges = Object.entries(drill.reference_payload.ideal_ranges ?? {});
  const stabilityExpectations = Object.entries(
    drill.reference_payload.stability_expectations ?? {}
  );

  return (
    <div className="space-y-8">
      <InfoCard className="relative overflow-hidden border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.16),_transparent_35%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))]">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap gap-2">
              <Badge variant="accent">{drill.sport_name}</Badge>
              <Badge variant="slate">{formatEnumLabel(drill.difficulty_level)}</Badge>
            </div>
            <h2 className="mt-5 font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">
              {drill.drill_name}
            </h2>
            <p className="mt-4 text-sm leading-7 text-muted-gray sm:text-base">
              {drill.description}
            </p>
          </div>

          <div className="grid w-full gap-3 xl:max-w-sm">
            <Button
              disabled
              className="justify-between rounded-2xl bg-primary/80 px-5 py-6 text-primary-foreground opacity-100 disabled:cursor-not-allowed disabled:opacity-65"
            >
              <span className="flex items-center gap-2">
                <PlayCircle className="h-4 w-4" />
                Start Live Session
              </span>
              <Badge variant="warning">Soon</Badge>
            </Button>
            <Button
              disabled
              variant="outline"
              className="justify-between rounded-2xl px-5 py-6 text-white/90 opacity-100 disabled:cursor-not-allowed disabled:opacity-65"
            >
              <span className="flex items-center gap-2">
                <UploadCloud className="h-4 w-4" />
                Upload Video
              </span>
              <Badge variant="warning">Soon</Badge>
            </Button>
            <p className="text-sm leading-7 text-muted-gray">
              Live analysis and upload-based review are coming soon. This page
              currently explains what the drill trains and what the later engine
              will evaluate.
            </p>
          </div>
        </div>
      </InfoCard>

      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <InfoCard>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
            Overview
          </p>
          <h3 className="mt-4 font-display text-2xl font-bold text-white">
            Movement breakdown
          </h3>
          <p className="mt-4 text-sm leading-7 text-muted-gray">
            {drill.reference_payload.notes ?? drill.description}
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Movement Type
              </p>
              <p className="mt-3 text-base font-semibold text-white">
                {formatTokenLabel(drill.reference_payload.movement_type ?? "dynamic")}
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Phases
              </p>
              <p className="mt-3 text-base font-semibold text-white">
                {phases.length}
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Tracked Joints
              </p>
              <p className="mt-3 text-base font-semibold text-white">
                {joints.length}
              </p>
            </div>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Phases
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {phases.map((phase) => (
                  <Badge key={phase} variant="slate">
                    {formatTokenLabel(phase)}
                  </Badge>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Tracked joints
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {joints.map((joint) => (
                  <Badge key={joint} variant="slate">
                    {formatTokenLabel(joint)}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </InfoCard>

        <InfoCard>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
            Target Metrics
          </p>
          <h3 className="mt-4 font-display text-2xl font-bold text-white">
            What later scoring will watch
          </h3>
          <div className="mt-6 flex flex-wrap gap-3">
            {metrics.map((metric) => (
              <div
                key={metric}
                className="rounded-2xl border border-primary/15 bg-primary/10 px-4 py-3 text-sm font-semibold text-white"
              >
                {formatTokenLabel(metric)}
              </div>
            ))}
          </div>
        </InfoCard>
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <InfoCard>
          <SectionTitle
            eyebrow="Coaching Focus"
            title="Primary focus cues"
            description="These focus areas are pulled directly from the drill's coaching rules."
          />
          <div className="mt-6 flex flex-wrap gap-2">
            {primaryFocus.map((item) => (
              <Badge key={item} variant="accent">
                {formatTokenLabel(item)}
              </Badge>
            ))}
          </div>
        </InfoCard>

        <InfoCard>
          <SectionTitle
            eyebrow="Positive Cues"
            title="What good reps look like"
            description="Positive cues frame the movement qualities TrainUp wants the athlete to repeat."
          />
          <ul className="mt-6 space-y-3">
            {positiveCues.map((cue) => (
              <li
                key={cue}
                className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-7 text-white/85"
              >
                {cue}
              </li>
            ))}
          </ul>
        </InfoCard>

        <InfoCard>
          <SectionTitle
            eyebrow="Recommendations"
            title="How the athlete can clean up form"
            description="These templates guide what future feedback will recommend after a review."
          />
          <ul className="mt-6 space-y-3">
            {recommendationTemplates.map((item) => (
              <li
                key={item}
                className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-7 text-white/85"
              >
                {item}
              </li>
            ))}
          </ul>
        </InfoCard>
      </div>

      <div className="space-y-5">
        <SectionTitle
          eyebrow="Reference Expectations"
          title="Ideal ranges and stability targets"
          description="These expectations come directly from the seeded reference payload and explain the drill's deterministic movement targets."
          action={
            <Link
              href={`/sports/${drill.sport_id}/drills`}
              className="inline-flex items-center gap-2 text-sm font-semibold text-primary transition-colors hover:text-primary/80"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to drill list
            </Link>
          }
        />

        <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
          <InfoCard>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
              Ideal Ranges
            </p>
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {idealRanges.map(([key, value]) => (
                <div
                  key={key}
                  className="rounded-2xl border border-white/10 bg-white/[0.04] p-4"
                >
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    {formatTokenLabel(key)}
                  </p>
                  <p className="mt-3 text-lg font-semibold text-white">
                    {value.min ?? 0} - {value.max ?? 0}
                  </p>
                </div>
              ))}
            </div>
          </InfoCard>

          <InfoCard>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
              Stability Expectations
            </p>
            <div className="mt-6 space-y-3">
              {stabilityExpectations.map(([key, value]) => (
                <div
                  key={key}
                  className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3"
                >
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    {formatTokenLabel(key)}
                  </p>
                  <p className="mt-2 text-base font-semibold text-white">
                    {String(value)}
                  </p>
                </div>
              ))}
            </div>
          </InfoCard>
        </div>
      </div>
    </div>
  );
}

export default function DrillDetailPage({
  params
}: {
  params: { drillId: string };
}) {
  return (
    <AppShell
      eyebrow="Drill Detail"
      title="Inspect the movement before the athlete performs it"
      description="This detail view is designed as a premium pre-analysis screen that explains movement intent, target metrics, and the coaching logic behind the drill."
      capsule="Catalog detail"
      actions={
        <CTAButton asChild>
          <Link href="/sports">All Sports</Link>
        </CTAButton>
      }
    >
      {() => <DrillDetailContent drillId={params.drillId} />}
    </AppShell>
  );
}

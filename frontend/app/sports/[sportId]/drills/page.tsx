"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Layers3 } from "lucide-react";

import { CTAButton } from "../../../../components/ui/cta-button";
import { SkeletonLoader } from "../../../../components/ui/skeleton-loader";
import { AppShell } from "../../../../features/app-shell/components/AppShell";
import { EmptyState } from "../../../../features/app-shell/components/EmptyState";
import { InfoCard } from "../../../../features/app-shell/components/InfoCard";
import { SectionTitle } from "../../../../features/app-shell/components/SectionTitle";
import { DrillCard } from "../../../../features/drills/components/DrillCard";
import { getSportPreset } from "../../../../lib/sport-presets";
import { getDrillsBySport } from "../../../../services/drills";
import { getSports } from "../../../../services/sports";
import type { DrillListItem } from "../../../../types/drills";
import type { ProfileResponse } from "../../../../types/profile";
import type { SportOption } from "../../../../types/sports";

function SportDrillsContent({
  sportId,
  profile
}: {
  sportId: string;
  profile: ProfileResponse | null;
}) {
  const [sport, setSport] = useState<SportOption | null>(null);
  const [drills, setDrills] = useState<DrillListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    async function loadDrills() {
      setError(null);

      try {
        const [sports, drillItems] = await Promise.all([
          getSports(),
          getDrillsBySport(sportId)
        ]);

        if (ignore) {
          return;
        }

        setSport(sports.find((item) => item.id === sportId) ?? null);
        setDrills(drillItems);
      } catch (loadError) {
        if (!ignore) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load drills for this sport."
          );
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    loadDrills();

    return () => {
      ignore = true;
    };
  }, [sportId]);

  const preset = getSportPreset(sport?.sport_name ?? "Training");

  return (
    <div className="space-y-8">
      <InfoCard className="relative overflow-hidden">
        <div className={`absolute inset-0 bg-gradient-to-br ${preset.glowClass}`} />
        <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
              {preset.badge}
            </p>
            <h2 className="mt-4 font-display text-4xl font-bold text-white">
              {sport?.sport_name ?? "Drill Library"}
            </h2>
            <p className="mt-4 text-sm leading-7 text-muted-gray">
              {sport
                ? preset.subtitle
                : "Open a drill to continue."}
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <CTAButton asChild className="rounded-2xl">
              <Link href="/sports">Browse Other Sports</Link>
            </CTAButton>
            {profile?.sport_id === sportId ? (
              <CTAButton
                asChild
                className="rounded-2xl border border-white/10 bg-white/[0.04] text-white shadow-none hover:bg-white/[0.07]"
              >
                <Link href="/dashboard">Back to Dashboard</Link>
              </CTAButton>
            ) : null}
          </div>
        </div>
      </InfoCard>

      <div className="space-y-5">
        <SectionTitle
          eyebrow="Drills"
          title={`${drills.length || 0} drills`}
          description="Pick a drill to continue."
          action={
            <Link
              href="/sports"
              className="inline-flex items-center gap-2 text-sm font-semibold text-primary transition-colors hover:text-primary/80"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to sports
            </Link>
          }
        />

        {isLoading ? (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            <SkeletonLoader className="h-[320px]" />
            <SkeletonLoader className="h-[320px]" />
            <SkeletonLoader className="h-[320px]" />
          </div>
        ) : error ? (
          <EmptyState
            icon={Layers3}
            title="Unable to load this drill library"
            description={error}
          />
        ) : drills.length === 0 ? (
          <EmptyState
            icon={Layers3}
            title="No drills available yet"
            description="This sport exists, but no drills have been published into the catalog for it yet."
          />
        ) : (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {drills.map((drill) => (
              <DrillCard key={drill.id} drill={drill} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function SportDrillsPage({
  params
}: {
  params: { sportId: string };
}) {
  return (
    <AppShell
      eyebrow="Drills"
      title="Browse drills"
      description="Open a drill and start."
      capsule="Catalog"
      actions={
        <CTAButton asChild>
          <Link href="/sports">All Sports</Link>
        </CTAButton>
      }
    >
      {({ profile }) => (
        <SportDrillsContent sportId={params.sportId} profile={profile} />
      )}
    </AppShell>
  );
}

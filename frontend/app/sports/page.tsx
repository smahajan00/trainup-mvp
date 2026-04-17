"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Layers3, Radar } from "lucide-react";

import { CTAButton } from "../../components/ui/cta-button";
import { SkeletonLoader } from "../../components/ui/skeleton-loader";
import { AppShell } from "../../features/app-shell/components/AppShell";
import { EmptyState } from "../../features/app-shell/components/EmptyState";
import { InfoCard } from "../../features/app-shell/components/InfoCard";
import { SectionTitle } from "../../features/app-shell/components/SectionTitle";
import { SportCard } from "../../features/sports/components/SportCard";
import { sortSportsByPresetOrder } from "../../lib/sport-presets";
import { getDrillsBySport } from "../../services/drills";
import { getSports } from "../../services/sports";
import type { ProfileResponse } from "../../types/profile";
import type { SportOption } from "../../types/sports";

type SportSummary = SportOption & {
  drillCount: number;
};

function SportsPageContent({ profile }: { profile: ProfileResponse | null }) {
  const [sports, setSports] = useState<SportSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    async function loadSports() {
      setError(null);

      try {
        const sportOptions = sortSportsByPresetOrder(await getSports());
        const drillCollections = await Promise.all(
          sportOptions.map((sport) => getDrillsBySport(sport.id))
        );

        if (ignore) {
          return;
        }

        setSports(
          sportOptions.map((sport, index) => ({
            ...sport,
            drillCount: drillCollections[index].length
          }))
        );
      } catch (loadError) {
        if (!ignore) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load the sports catalog."
          );
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    loadSports();

    return () => {
      ignore = true;
    };
  }, []);

  return (
    <div className="space-y-8">
      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <InfoCard className="relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.14),_transparent_38%)]" />
          <div className="relative z-10">
            <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
              Sports
            </p>
            <h2 className="mt-4 font-display text-3xl font-bold text-white">
              Browse by sport
            </h2>
            <p className="mt-4 max-w-2xl text-sm text-muted-gray">
              Pick a sport. Open its drills.
            </p>
          </div>
        </InfoCard>
        <InfoCard>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
            Your sport
          </p>
          <h3 className="mt-4 font-display text-2xl font-bold text-white">
            {profile ? profile.sport_name : "Profile not configured"}
          </h3>
          <p className="mt-3 text-sm text-muted-gray">
            {profile
              ? "Your sport is highlighted below."
              : "Set your sport to personalize this page."}
          </p>
          <div className="mt-6 flex gap-3">
            <CTAButton asChild className="rounded-2xl">
              <Link href={profile ? `/sports/${profile.sport_id}/drills` : "/profile"}>
                {profile ? "Open My Sport" : "Set Profile"}
              </Link>
            </CTAButton>
          </div>
        </InfoCard>
      </div>

      <div className="space-y-5">
        <SectionTitle
          eyebrow="Available"
          title="Sport library"
          description="Open Gym, Football, or Basketball."
        />

        {isLoading ? (
          <div className="grid gap-5 lg:grid-cols-3">
            <SkeletonLoader className="h-[340px]" />
            <SkeletonLoader className="h-[340px]" />
            <SkeletonLoader className="h-[340px]" />
          </div>
        ) : error ? (
          <EmptyState
            icon={Layers3}
            title="Sports catalog unavailable"
            description={error}
          />
        ) : (
          <div className="grid gap-5 lg:grid-cols-3">
            {sports.map((sport) => (
              <SportCard
                key={sport.id}
                sport={sport}
                drillCount={sport.drillCount}
                highlighted={profile?.sport_id === sport.id}
              />
            ))}
          </div>
        )}
      </div>

      <InfoCard>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
              Next
            </p>
            <h3 className="mt-4 font-display text-2xl font-bold text-white">
              Review sessions after each upload
            </h3>
            <p className="mt-3 max-w-2xl text-sm text-muted-gray">
              Pick a drill to start.
            </p>
          </div>
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
            <Radar className="h-5 w-5" />
          </div>
        </div>
      </InfoCard>
    </div>
  );
}

export default function SportsPage() {
  return (
    <AppShell
      eyebrow="Catalog"
      title="Browse sports"
      description="Choose a sport and open drills."
      capsule="Training"
      actions={
        <CTAButton asChild>
          <Link href="/dashboard">Back to Dashboard</Link>
        </CTAButton>
      }
    >
      {({ profile }) => <SportsPageContent profile={profile} />}
    </AppShell>
  );
}

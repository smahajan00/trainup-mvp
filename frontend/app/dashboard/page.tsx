"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ClipboardCheck,
  Compass,
  Dumbbell,
  Gauge,
  Sparkles,
  UserRound
} from "lucide-react";

import { CTAButton } from "../../components/ui/cta-button";
import { SkeletonLoader } from "../../components/ui/skeleton-loader";
import { EmptyState } from "../../features/app-shell/components/EmptyState";
import { AppShell } from "../../features/app-shell/components/AppShell";
import { InfoCard } from "../../features/app-shell/components/InfoCard";
import { SectionTitle } from "../../features/app-shell/components/SectionTitle";
import { StatCard } from "../../features/app-shell/components/StatCard";
import { ProfileSummaryCard } from "../../features/dashboard/components/ProfileSummaryCard";
import { QuickActionCard } from "../../features/dashboard/components/QuickActionCard";
import { SportCard } from "../../features/sports/components/SportCard";
import { calculateProfileCompletion } from "../../lib/formatters";
import { sortSportsByPresetOrder } from "../../lib/sport-presets";
import { getDrillsBySport } from "../../services/drills";
import { getSports } from "../../services/sports";
import type { CurrentUserResponse } from "../../types/auth";
import type { ProfileResponse } from "../../types/profile";
import type { SportOption } from "../../types/sports";

type SportSummary = SportOption & {
  drillCount: number;
};

function DashboardContent({
  user,
  profile
}: {
  user: CurrentUserResponse | null;
  profile: ProfileResponse | null;
}) {
  const [sportSummaries, setSportSummaries] = useState<SportSummary[]>([]);
  const [isLoadingSports, setIsLoadingSports] = useState(true);
  const [sportsError, setSportsError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    async function loadCatalog() {
      setSportsError(null);

      try {
        const sports = await getSports();
        const orderedSports = sortSportsByPresetOrder(sports);
        const drillCollections = await Promise.all(
          orderedSports.map((sport) => getDrillsBySport(sport.id))
        );

        if (ignore) {
          return;
        }

        setSportSummaries(
          orderedSports.map((sport, index) => ({
            ...sport,
            drillCount: drillCollections[index].length
          }))
        );
      } catch (error) {
        if (!ignore) {
          setSportsError(
            error instanceof Error
              ? error.message
              : "Unable to load sports right now."
          );
        }
      } finally {
        if (!ignore) {
          setIsLoadingSports(false);
        }
      }
    }

    loadCatalog();

    return () => {
      ignore = true;
    };
  }, []);

  const availableDrills = sportSummaries.reduce(
    (total, sport) => total + sport.drillCount,
    0
  );
  const profileCompletion = calculateProfileCompletion(profile);
  const startTrainingHref = profile
    ? `/sports/${profile.sport_id}/drills`
    : "/profile";
  const trainingReady = profile ? "Ready" : "Profile first";

  return (
    <div className="space-y-8">
      <InfoCard className="relative overflow-hidden border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.16),_transparent_35%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))]">
        <div className="absolute inset-y-0 right-0 hidden w-2/5 bg-[radial-gradient(circle_at_center,_rgba(255,122,0,0.18),_transparent_55%)] lg:block" />
        <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-primary">
              Welcome back
            </p>
            <h2 className="mt-4 font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">
              {user?.full_name
                ? `${user.full_name}, keep your movement work sharp.`
                : "Build a clean training rhythm."}
            </h2>
            <p className="mt-4 text-sm leading-7 text-muted-gray sm:text-base">
              Browse sport-specific drills, reinforce technique expectations,
              and get the platform ready for later live and upload-based
              coaching analysis.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <CTAButton asChild>
                <Link href={startTrainingHref}>Start Training</Link>
              </CTAButton>
              <CTAButton
                asChild
                className="border border-white/10 bg-white/[0.04] text-white shadow-none hover:bg-white/[0.07]"
              >
                <Link href="/sports">Browse Sports</Link>
              </CTAButton>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-3 lg:w-[420px]">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Focus
              </p>
              <p className="mt-3 text-sm font-semibold text-white">
                Catalog-driven drill selection
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Mode
              </p>
              <p className="mt-3 text-sm font-semibold text-white">
                {trainingReady}
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Sport
              </p>
              <p className="mt-3 text-sm font-semibold text-white">
                {profile?.sport_name ?? "Set profile"}
              </p>
            </div>
          </div>
        </div>
      </InfoCard>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <ProfileSummaryCard profile={profile} />

        {profile ? (
          <InfoCard className="relative overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.14),_transparent_42%)]" />
            <div className="relative z-10">
              <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
                Readiness
              </p>
              <h3 className="mt-4 font-display text-3xl font-bold text-white">
                Training mode ready
              </h3>
              <p className="mt-4 text-sm leading-7 text-muted-gray">
                Your current sport and skill profile are set, so the drill
                library can already surface the right movement context for this
                athlete.
              </p>
              <div className="mt-8 grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Profile completion
                  </p>
                  <p className="mt-3 text-3xl font-bold text-white">
                    {profileCompletion}%
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Next module
                  </p>
                  <p className="mt-3 text-sm font-semibold text-white">
                    Live and upload analysis coming soon
                  </p>
                </div>
              </div>
            </div>
          </InfoCard>
        ) : (
          <EmptyState
            icon={ClipboardCheck}
            title="Complete onboarding to unlock a sharper dashboard"
            description="Your drill browsing flow already works, but adding athlete context makes later analysis and coaching feedback much more meaningful."
            action={
              <CTAButton asChild>
                <Link href="/profile">Complete Profile</Link>
              </CTAButton>
            }
          />
        )}
      </div>

      <div className="space-y-5">
        <SectionTitle
          eyebrow="Quick Actions"
          title="Move through the product fast"
          description="These shortcuts keep the current phase focused on browsing sports, exploring drills, and maintaining athlete context."
        />
        <div className="grid gap-5 lg:grid-cols-3">
          <QuickActionCard
            title="Browse Sports"
            description="Open the sports catalog and move straight into Gym, Football, or Basketball drill browsing."
            href="/sports"
            icon={Compass}
            badge="Catalog"
          />
          <QuickActionCard
            title="Continue Training"
            description="Jump directly into your selected sport's drill library if your profile is configured."
            href={startTrainingHref}
            icon={Dumbbell}
            badge={profile ? "Recommended" : "Set profile"}
          />
          <QuickActionCard
            title="View Profile"
            description="Keep sport context, skill level, and physical attributes current before training sessions begin."
            href="/profile"
            icon={UserRound}
            badge="Athlete data"
          />
        </div>
      </div>

      <div className="space-y-5">
        <SectionTitle
          eyebrow="System Status"
          title="Honest platform readiness"
          description="These signals use real profile and catalog data available in the current TrainUp phase. No analytics are being faked."
        />
        <div className="grid gap-5 xl:grid-cols-4">
          <StatCard
            label="Available Sports"
            value={String(sportSummaries.length || 0)}
            description="Seeded sports currently available for browsing in the authenticated catalog."
            icon={Compass}
          />
          <StatCard
            label="Available Drills"
            value={String(availableDrills)}
            description="Real drill count derived from the seeded backend catalog across all sports."
            icon={Dumbbell}
          />
          <StatCard
            label="Profile Completion"
            value={`${profileCompletion}%`}
            description="Calculated from the fields currently configured in the athlete profile."
            icon={ClipboardCheck}
            tone={profile ? "success" : "warning"}
          />
          <StatCard
            label="Training Mode Ready"
            value={trainingReady}
            description="Live analysis and upload review are not built yet, but the browsing and onboarding layer is ready."
            icon={Gauge}
            tone={profile ? "success" : "warning"}
          />
        </div>
      </div>

      <div className="space-y-5">
        <SectionTitle
          eyebrow="Featured Training"
          title="Browse the current drill catalog"
          description="Each sport card opens into a focused drill library powered by the seeded backend data."
          action={
            <CTAButton asChild className="rounded-2xl">
              <Link href="/sports">Open Sports Hub</Link>
            </CTAButton>
          }
        />

        {isLoadingSports ? (
          <div className="grid gap-5 lg:grid-cols-3">
            <SkeletonLoader className="h-[340px]" />
            <SkeletonLoader className="h-[340px]" />
            <SkeletonLoader className="h-[340px]" />
          </div>
        ) : sportsError ? (
          <EmptyState
            icon={Sparkles}
            title="Sports catalog unavailable"
            description={sportsError}
          />
        ) : (
          <div className="grid gap-5 lg:grid-cols-3">
            {sportSummaries.map((sport) => (
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
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AppShell
      eyebrow="Performance Workspace"
      title="Your training command center"
      description="A premium overview of athlete context, catalog readiness, and the fastest paths into the sports and drill library."
      capsule="Post-login shell"
      actions={
        <CTAButton asChild>
          <Link href="/sports">Start Training</Link>
        </CTAButton>
      }
    >
      {({ user, profile }) => <DashboardContent user={user} profile={profile} />}
    </AppShell>
  );
}

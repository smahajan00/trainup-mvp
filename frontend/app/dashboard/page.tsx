"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  BarChart3,
  ClipboardCheck,
  Compass,
  Dumbbell,
  Gauge,
  History,
  LineChart,
  Sparkles
} from "lucide-react";

import { Button } from "../../components/ui/button";
import { CTAButton } from "../../components/ui/cta-button";
import { SkeletonLoader } from "../../components/ui/skeleton-loader";
import { EmptyState } from "../../features/app-shell/components/EmptyState";
import { AppShell } from "../../features/app-shell/components/AppShell";
import { InfoCard } from "../../features/app-shell/components/InfoCard";
import { SectionTitle } from "../../features/app-shell/components/SectionTitle";
import { StatCard } from "../../features/app-shell/components/StatCard";
import { ProfileSummaryCard } from "../../features/dashboard/components/ProfileSummaryCard";
import { QuickActionCard } from "../../features/dashboard/components/QuickActionCard";
import { RecentSessionCard } from "../../features/sessions/components/RecentSessionCard";
import { SportCard } from "../../features/sports/components/SportCard";
import {
  calculateProfileCompletion,
  formatDateTime,
  formatEnumLabel
} from "../../lib/formatters";
import { sortSportsByPresetOrder } from "../../lib/sport-presets";
import { getDrillsBySport } from "../../services/drills";
import { getRecentProgress } from "../../services/progress";
import { getSports } from "../../services/sports";
import type { CurrentUserResponse } from "../../types/auth";
import type { ProfileResponse } from "../../types/profile";
import type {
  RecentMetricProgress,
  RecentProgressSession
} from "../../types/progress";
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
  const [recentSessions, setRecentSessions] = useState<RecentProgressSession[]>([]);
  const [recentMetrics, setRecentMetrics] = useState<RecentMetricProgress[]>([]);
  const [isLoadingProgress, setIsLoadingProgress] = useState(true);
  const [progressError, setProgressError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    async function loadCatalog() {
      setSportsError(null);
      setProgressError(null);

      try {
        const [sports, progressResult] = await Promise.all([
          getSports(),
          getRecentProgress(4, 20)
        ]);
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
        setRecentSessions(progressResult.recent_sessions);
        setRecentMetrics(progressResult.recent_metrics);
      } catch (error) {
        if (!ignore) {
          setSportsError(
            error instanceof Error ? error.message : "Unable to load sports right now."
          );
          setProgressError(
            error instanceof Error
              ? error.message
              : "Unable to load recent progress right now."
          );
        }
      } finally {
        if (!ignore) {
          setIsLoadingSports(false);
          setIsLoadingProgress(false);
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
  const startTrainingHref = profile ? `/sports/${profile.sport_id}/drills` : "/profile";
  const latestMetricsByName = recentMetrics.reduce<Record<string, RecentMetricProgress>>(
    (accumulator, metric) => {
      if (!accumulator[metric.metric_name]) {
        accumulator[metric.metric_name] = metric;
      }
      return accumulator;
    },
    {}
  );
  const performanceSnapshot = Object.values(latestMetricsByName).slice(0, 6);
  const metricGroups = recentMetrics.reduce<Record<string, RecentMetricProgress[]>>(
    (accumulator, metric) => {
      if (!accumulator[metric.metric_name]) {
        accumulator[metric.metric_name] = [];
      }
      accumulator[metric.metric_name].push(metric);
      return accumulator;
    },
    {}
  );
  const trendCandidate =
    Object.values(metricGroups).sort((left, right) => right.length - left.length)[0] ?? [];
  const trendMetricName = trendCandidate[0]?.metric_name ?? null;
  const trendSeries = [...trendCandidate].reverse().slice(-5);
  const processedSessionCount = recentSessions.length;
  const trackedMetricCount = performanceSnapshot.length;

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
              {user?.full_name ? `${user.full_name}, stay sharp.` : "Stay ready to train."}
            </h2>
            <p className="mt-4 text-sm text-muted-gray sm:text-base">
              Start a session, check your latest work, and jump into full performance analytics when you want the deeper picture.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <CTAButton asChild>
                <Link href={startTrainingHref}>Start Training</Link>
              </CTAButton>
              <Button
                asChild
                variant="outline"
                className="border-white/10 bg-white/[0.04] text-white"
              >
                <Link href="/progress">View Progress</Link>
              </Button>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-3 lg:w-[420px]">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">Focus</p>
              <p className="mt-3 text-sm font-semibold text-white">Start your next drill</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Progress
              </p>
              <p className="mt-3 text-sm font-semibold text-white">
                {processedSessionCount} recent sessions
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">Sport</p>
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
              <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">Readiness</p>
              <h3 className="mt-4 font-display text-3xl font-bold text-white">
                Training mode ready
              </h3>
              <p className="mt-4 text-sm text-muted-gray">
                Your setup is ready for new sessions and detailed progress reviews.
              </p>
              <div className="mt-8 grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Profile completion
                  </p>
                  <p className="mt-3 text-3xl font-bold text-white">{profileCompletion}%</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Next module
                  </p>
                  <p className="mt-3 text-sm font-semibold text-white">
                    Full progress analytics
                  </p>
                </div>
              </div>
            </div>
          </InfoCard>
        ) : (
          <EmptyState
            icon={ClipboardCheck}
            title="Finish setup"
            description="Set your profile to personalize training."
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
          eyebrow="Actions"
          title="Move fast"
          description="Pick your next step."
        />
        <div className="grid gap-5 lg:grid-cols-3">
          <QuickActionCard
            title="Choose Sport"
            description="Open Gym, Football, or Basketball and pick a drill."
            href="/sports"
            icon={Compass}
            badge="Catalog"
          />
          <QuickActionCard
            title="Start Training"
            description="Jump straight into your current sport flow."
            href={startTrainingHref}
            icon={Dumbbell}
            badge={profile ? "Recommended" : "Set profile"}
          />
          <QuickActionCard
            title="View Progress"
            description="Open the full analytics page with trends and drill comparison."
            href="/progress"
            icon={LineChart}
            badge="Analytics"
          />
        </div>
      </div>

      <div className="space-y-5">
        <SectionTitle
          eyebrow="Recent"
          title="Recent sessions"
          description="Open your latest reviews."
        />

        {isLoadingProgress ? (
          <div className="grid gap-5 xl:grid-cols-4">
            <SkeletonLoader className="h-[240px]" />
            <SkeletonLoader className="h-[240px]" />
            <SkeletonLoader className="h-[240px]" />
            <SkeletonLoader className="h-[240px]" />
          </div>
        ) : progressError ? (
          <EmptyState
            icon={History}
            title="Recent sessions unavailable"
            description={progressError}
          />
        ) : recentSessions.length === 0 ? (
          <EmptyState
            icon={History}
            title="No sessions yet"
            description="Upload a video to start tracking."
            action={
              <CTAButton asChild>
                <Link href="/sports">Start With a Drill</Link>
              </CTAButton>
            }
          />
        ) : (
          <div className="grid gap-5 xl:grid-cols-4">
            {recentSessions.map((session) => (
              <RecentSessionCard key={session.session_id} session={session} />
            ))}
          </div>
        )}
      </div>

      <div className="space-y-5">
        <SectionTitle
          eyebrow="Snapshot"
          title="Latest metrics"
          description="Your latest saved scores."
          action={
            <Button
              asChild
              variant="outline"
              className="border-white/10 bg-white/[0.04] text-white"
            >
              <Link href="/progress">Open Full Progress</Link>
            </Button>
          }
        />
        <div className="grid gap-5 xl:grid-cols-4">
          <StatCard
            label="Recent Sessions"
            value={String(processedSessionCount)}
            description="Latest saved reviews."
            icon={History}
          />
          <StatCard
            label="Tracked Metrics"
            value={String(trackedMetricCount)}
            description="Metrics saved so far."
            icon={Gauge}
          />
          <StatCard
            label="Profile Completion"
            value={`${profileCompletion}%`}
            description="Setup progress."
            icon={ClipboardCheck}
            tone={profile ? "success" : "warning"}
          />
          <StatCard
            label="Available Drills"
            value={String(availableDrills)}
            description="Drills ready now."
            icon={Dumbbell}
          />
        </div>

        {isLoadingProgress ? (
          <div className="grid gap-5 lg:grid-cols-2">
            <SkeletonLoader className="h-[260px]" />
            <SkeletonLoader className="h-[260px]" />
          </div>
        ) : progressError ? (
          <EmptyState
            icon={BarChart3}
            title="Progress snapshot unavailable"
            description={progressError}
          />
        ) : (
          <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
            <InfoCard>
              <SectionTitle
                eyebrow="Metrics"
                title="Performance snapshot"
                description="Your latest saved values."
              />
              {performanceSnapshot.length ? (
                <div className="mt-6 grid gap-3">
                  {performanceSnapshot.map((metric) => (
                    <div
                      key={metric.progress_id}
                      className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-white">
                            {formatEnumLabel(metric.metric_name)}
                          </p>
                          <p className="mt-2 text-sm text-muted-gray">
                            {metric.drill_name} · {formatDateTime(metric.created_at)}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-2xl font-bold text-white">
                            {metric.metric_value.toFixed(2)}
                          </p>
                          <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                            {metric.metric_unit}
                          </p>
                        </div>
                      </div>
                      <div className="mt-4 h-2 rounded-full bg-white/10">
                        <div
                          className="h-2 rounded-full bg-primary"
                          style={{ width: `${Math.max(metric.metric_value * 100, 8)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-6 text-sm text-muted-gray">Upload a video to track scores.</p>
              )}
            </InfoCard>

            <InfoCard>
              <SectionTitle
                eyebrow="Trend"
                title={trendMetricName ? formatEnumLabel(trendMetricName) : "No trend yet"}
                description="Last five saved values."
              />
              {trendSeries.length ? (
                <div className="mt-6 space-y-3">
                  {trendSeries.map((metric, index) => (
                    <div
                      key={metric.progress_id}
                      className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-white">
                          Session {index + 1}
                        </p>
                        <p className="text-sm text-muted-gray">
                          {formatDateTime(metric.created_at)}
                        </p>
                      </div>
                      <p className="mt-3 text-2xl font-bold text-white">
                        {metric.metric_value.toFixed(2)}
                      </p>
                      <p className="mt-2 text-sm text-muted-gray">{metric.drill_name}</p>
                      <div className="mt-4 h-2 rounded-full bg-white/10">
                        <div
                          className="h-2 rounded-full bg-primary"
                          style={{ width: `${Math.max(metric.metric_value * 100, 8)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-6 text-sm text-muted-gray">More sessions will unlock trends.</p>
              )}
            </InfoCard>
          </div>
        )}
      </div>

      <div className="space-y-5">
        <SectionTitle
          eyebrow="Featured"
          title="Browse drills"
          description="Pick a sport and continue."
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
      eyebrow="Dashboard"
      title="Your training home"
      description="Start sessions, review recent work, and jump into analytics."
      capsule="Ready"
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

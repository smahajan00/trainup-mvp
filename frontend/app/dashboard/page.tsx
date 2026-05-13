"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  ClipboardCheck,
  Compass,
  Dumbbell,
  Gauge,
  History,
  LineChart,
  Sparkles,
  Trophy
} from "lucide-react";

import { Button } from "../../components/ui/button";
import { CTAButton } from "../../components/ui/cta-button";
import { SkeletonLoader } from "../../components/ui/skeleton-loader";
import { EmptyState } from "../../features/app-shell/components/EmptyState";
import { AppShell } from "../../features/app-shell/components/AppShell";
import { InfoCard } from "../../features/app-shell/components/InfoCard";
import { SectionTitle } from "../../features/app-shell/components/SectionTitle";
import { StatCard } from "../../features/app-shell/components/StatCard";
import { QuickActionCard } from "../../features/dashboard/components/QuickActionCard";
import { RecentSessionCard } from "../../features/sessions/components/RecentSessionCard";
import { SportCard } from "../../features/sports/components/SportCard";
import { formatEnumLabel } from "../../lib/formatters";
import { sortSportsByPresetOrder } from "../../lib/sport-presets";
import { getDrillsBySport } from "../../services/drills";
import { getRecentProgress } from "../../services/progress";
import { getSports } from "../../services/sports";
import type { CurrentUserResponse } from "../../types/auth";
import type { ProfileResponse } from "../../types/profile";
import type {
  RecentMetricProgress,
  RecentProgressResponse,
  RecentProgressSession
} from "../../types/progress";
import type { SportOption } from "../../types/sports";

type SportSummary = SportOption & {
  drillCount: number;
};

function formatPercent(value: number | null) {
  return value === null ? "--" : `${value.toFixed(0)}%`;
}

function getAverageScore(sessions: RecentProgressSession[]) {
  if (!sessions.length) {
    return null;
  }

  return (
    sessions.reduce((total, session) => total + session.overall_accuracy, 0) /
    sessions.length
  );
}

function getBestScore(sessions: RecentProgressSession[]) {
  if (!sessions.length) {
    return null;
  }

  return Math.max(...sessions.map((session) => session.overall_accuracy));
}

function getTrendLabel(sessions: RecentProgressSession[]) {
  if (sessions.length < 2) {
    return "Need data";
  }

  const delta = sessions[0].overall_accuracy - sessions[1].overall_accuracy;
  if (Math.abs(delta) < 1) {
    return "Stable";
  }

  return delta > 0 ? "Improving" : "Needs attention";
}

function getPrimaryFocus(metrics: RecentMetricProgress[]) {
  const metric = metrics[0]?.metric_name;
  return metric ? formatEnumLabel(metric) : "No focus yet";
}

function getFirstName(fullName: string | null | undefined) {
  const trimmedName = fullName?.trim();
  return trimmedName ? trimmedName.split(/\s+/)[0] : null;
}

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
  const [monthlyProgress, setMonthlyProgress] = useState<RecentProgressResponse | null>(
    null
  );
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
          getRecentProgress(4, 20, "monthly")
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
        setMonthlyProgress(progressResult);
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
  const startTrainingHref = profile ? `/sports/${profile.sport_id}/drills` : "/profile";
  const monthlySessionCount =
    monthlyProgress?.total_analyzed_sessions ?? recentSessions.length;
  const averageScore = useMemo(
    () => monthlyProgress?.average_score ?? getAverageScore(recentSessions),
    [monthlyProgress?.average_score, recentSessions]
  );
  const bestScore = useMemo(
    () => monthlyProgress?.best_score ?? getBestScore(recentSessions),
    [monthlyProgress?.best_score, recentSessions]
  );
  const trendLabel = useMemo(
    () => monthlyProgress?.trend_label ?? getTrendLabel(recentSessions),
    [monthlyProgress?.trend_label, recentSessions]
  );
  const primaryFocus = useMemo(() => getPrimaryFocus(recentMetrics), [recentMetrics]);
  const firstName = getFirstName(user?.full_name);

  return (
    <div className="space-y-12 md:space-y-14">
      <InfoCard className="border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.16),_transparent_35%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))] p-7 md:p-8">
        <div className="pointer-events-none absolute inset-y-0 right-0 hidden w-2/5 bg-[radial-gradient(circle_at_center,_rgba(255,122,0,0.14),_transparent_60%)] lg:block" />
        <div className="relative z-10 grid gap-7 lg:grid-cols-[minmax(0,1fr)_340px] lg:items-center">
          <div className="min-w-0 overflow-hidden">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">
              Ready to train smarter?
            </p>
            <h1 className="mt-4 max-w-4xl break-words font-display text-5xl font-bold leading-[1.04] tracking-tight text-white [text-wrap:balance] md:text-6xl">
              {firstName
                ? `${firstName}, build your next breakthrough.`
                : "Build your next breakthrough."}
            </h1>
            <p className="mt-5 line-clamp-3 max-w-2xl break-words text-sm leading-relaxed text-neutral-300 md:text-base">
              Start a training flow, review recent reps, and jump into the performance dashboard whenever you want the deeper story.
            </p>
            <div className="mt-5 inline-flex max-w-full rounded-full border border-primary/20 bg-primary/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-primary">
              <span className="line-clamp-1 break-words">
                Turn every rep into feedback.
              </span>
            </div>
            <div className="mt-7 flex flex-wrap gap-3">
              <CTAButton asChild>
                <Link href={startTrainingHref}>Start Training</Link>
              </CTAButton>
              <Button asChild variant="outline">
                <Link href="/progress">Open Performance Dashboard</Link>
              </Button>
            </div>
          </div>

          <div className="grid min-w-0 gap-3 self-center sm:grid-cols-3 lg:grid-cols-1">
            <div className="min-h-[92px] min-w-0 overflow-hidden rounded-3xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-neutral-400">Focus</p>
              <p className="mt-3 line-clamp-2 break-words text-base font-semibold text-white">
                Launch your next rep
              </p>
            </div>
            <div className="min-h-[92px] min-w-0 overflow-hidden rounded-3xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-neutral-400">
                Dashboard
              </p>
              <p className="mt-3 line-clamp-2 break-words text-base font-semibold text-white">
                {monthlySessionCount} sessions this month
              </p>
            </div>
            <div className="min-h-[92px] min-w-0 overflow-hidden rounded-3xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-neutral-400">Sport</p>
              <p className="mt-3 line-clamp-2 break-words text-base font-semibold text-white">
                {profile?.sport_name ?? "Set profile"}
              </p>
            </div>
          </div>
        </div>
      </InfoCard>

      <section className="space-y-7">
        <SectionTitle
          eyebrow="Actions"
          title="Pick your next move"
          description="Three clear paths: start training, choose a sport, or open analytics."
        />
        <div className="grid gap-7 lg:grid-cols-3">
          <QuickActionCard
            title="Start Training"
            description="Open the recommended drill flow."
            href={startTrainingHref}
            icon={Dumbbell}
            badge={profile ? "Recommended" : "Profile"}
          />
          <QuickActionCard
            title="Choose Sport"
            description="Browse drills by training area."
            href="/sports"
            icon={Compass}
            badge="Catalog"
          />
          <QuickActionCard
            title="View Analytics"
            description="Track trends and focus areas."
            href="/progress"
            icon={LineChart}
            badge="Dashboard"
          />
        </div>
      </section>

      <section className="space-y-7">
        <SectionTitle
          eyebrow="Recent"
          title="Recent Sessions"
          description="Showing latest 4 analyzed sessions this month."
        />

        {isLoadingProgress ? (
          <div className="grid gap-7 md:grid-cols-2 xl:grid-cols-4">
            <SkeletonLoader className="h-72" />
            <SkeletonLoader className="h-72" />
            <SkeletonLoader className="h-72" />
            <SkeletonLoader className="h-72" />
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
            description="Log your first session to start building your performance story."
            action={
              <CTAButton asChild>
                <Link href="/sports">Start With a Drill</Link>
              </CTAButton>
            }
          />
        ) : (
          <div className="grid gap-7 md:grid-cols-2 xl:grid-cols-4">
            {recentSessions.map((session) => (
              <RecentSessionCard key={session.session_id} session={session} />
            ))}
          </div>
        )}
      </section>

      <section className="space-y-7">
        <SectionTitle
          eyebrow="Insight"
          title="Performance Insight"
          description="One clean read on score, trend, and current focus."
          action={
            <Button asChild variant="outline">
              <Link href="/progress">Open Performance Dashboard</Link>
            </Button>
          }
        />

        {isLoadingProgress ? (
          <div className="grid gap-7 md:grid-cols-2 xl:grid-cols-4">
            <SkeletonLoader className="h-48" />
            <SkeletonLoader className="h-48" />
            <SkeletonLoader className="h-48" />
            <SkeletonLoader className="h-48" />
          </div>
        ) : progressError ? (
          <EmptyState
            icon={BarChart3}
            title="Performance insight unavailable"
            description={progressError}
          />
        ) : (
          <div className="grid gap-7 md:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Average Score"
              value={formatPercent(averageScore)}
              description="Average this month"
              icon={Gauge}
            />
            <StatCard
              label="Best Score"
              value={formatPercent(bestScore)}
              description="Best this month"
              icon={Trophy}
              tone="success"
            />
            <StatCard
              label="Trend"
              value={trendLabel}
              description="Monthly trend"
              icon={LineChart}
              tone={trendLabel === "Needs attention" ? "warning" : "success"}
            />
            <StatCard
              label="Key Focus"
              value={primaryFocus}
              description="Latest tracked metric"
              icon={ClipboardCheck}
            />
          </div>
        )}
      </section>

      <section className="space-y-7">
        <SectionTitle
          eyebrow="Sports"
          title="Sports Hub"
          description={`${availableDrills} drills available across your training catalog.`}
          action={
            <CTAButton asChild>
              <Link href="/sports">Open Sports Hub</Link>
            </CTAButton>
          }
        />

        {isLoadingSports ? (
          <div className="grid gap-7 lg:grid-cols-3">
            <SkeletonLoader className="h-80" />
            <SkeletonLoader className="h-80" />
            <SkeletonLoader className="h-80" />
          </div>
        ) : sportsError ? (
          <EmptyState
            icon={Sparkles}
            title="Sports catalog unavailable"
            description={sportsError}
          />
        ) : (
          <div className="grid gap-7 lg:grid-cols-3">
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
      </section>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AppShell
      eyebrow="Home"
      title="Your training home"
      description="Start training, revisit recent sessions, and open the performance dashboard when you want deeper analytics."
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

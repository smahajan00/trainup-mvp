"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  ClipboardCheck,
  Gauge,
  History,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
  Trophy
} from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { CTAButton } from "../../../components/ui/cta-button";
import { Select } from "../../../components/ui/select";
import { SkeletonLoader } from "../../../components/ui/skeleton-loader";
import { EmptyState } from "../../app-shell/components/EmptyState";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { SectionTitle } from "../../app-shell/components/SectionTitle";
import {
  buildAnalyzedSession,
  buildDashboardInsightSummary,
  buildDrillComparisonData,
  buildMetricImprovementData,
  buildRecurringInsightSummary,
  buildScoreTrendData,
  buildTrendSummary,
  formatScoreLabel,
  getDrillOptionsForSport,
  getSeverityVariant
} from "../analytics-utils";
import { AnalyticsKpiCard } from "./AnalyticsKpiCard";
import { MetricImprovementChartCard } from "./MetricImprovementChartCard";
import { ScoreTrendChartCard } from "./ScoreTrendChartCard";
import { getErrorMessage } from "../../../lib/api";
import {
  calculateProfileCompletion,
  formatDateTime,
  formatEnumLabel
} from "../../../lib/formatters";
import { getDrillsBySport } from "../../../services/drills";
import { getRecentProgress } from "../../../services/progress";
import { getSessionArtifacts } from "../../../services/sessions";
import { getSports } from "../../../services/sports";
import type { CurrentUserResponse } from "../../../types/auth";
import type { DrillListItem } from "../../../types/drills";
import type { ProfileResponse } from "../../../types/profile";
import type {
  RecentMetricProgress,
  RecentProgressSession
} from "../../../types/progress";
import type { SessionArtifactsResponse } from "../../../types/sessions";
import type { SportOption } from "../../../types/sports";

type ProgressAnalyticsViewProps = {
  user: CurrentUserResponse | null;
  profile: ProfileResponse | null;
};

type SportSummary = SportOption & {
  drillCount: number;
};

const FILTER_SPORT_ORDER = ["Gym", "Basketball", "Football"];

function sortDashboardSports(sports: SportOption[]) {
  return [...sports].sort((left, right) => {
    const leftIndex = FILTER_SPORT_ORDER.indexOf(left.sport_name);
    const rightIndex = FILTER_SPORT_ORDER.indexOf(right.sport_name);
    const resolvedLeft = leftIndex === -1 ? Number.MAX_SAFE_INTEGER : leftIndex;
    const resolvedRight = rightIndex === -1 ? Number.MAX_SAFE_INTEGER : rightIndex;

    return resolvedLeft - resolvedRight;
  });
}

function getTrendTone(direction: "up" | "down" | "flat" | "insufficient") {
  if (direction === "up") {
    return "success" as const;
  }

  if (direction === "down") {
    return "danger" as const;
  }

  if (direction === "flat") {
    return "warning" as const;
  }

  return "slate" as const;
}

export function ProgressAnalyticsView({
  user,
  profile
}: ProgressAnalyticsViewProps) {
  const [sportSummaries, setSportSummaries] = useState<SportSummary[]>([]);
  const [drillsBySport, setDrillsBySport] = useState<Record<string, DrillListItem[]>>(
    {}
  );
  const [recentSessions, setRecentSessions] = useState<RecentProgressSession[]>([]);
  const [recentMetrics, setRecentMetrics] = useState<RecentMetricProgress[]>([]);
  const [artifactsBySessionId, setArtifactsBySessionId] = useState<
    Record<string, SessionArtifactsResponse>
  >({});
  const [selectedSportId, setSelectedSportId] = useState("all");
  const [selectedDrillId, setSelectedDrillId] = useState("all");
  const [isLoading, setIsLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    async function loadDashboard() {
      setDashboardError(null);

      try {
        const [sports, progressResult] = await Promise.all([
          getSports(),
          getRecentProgress(10, 50)
        ]);

        const orderedSports = sortDashboardSports(sports);
        const drillResults = await Promise.allSettled(
          orderedSports.map((sport) => getDrillsBySport(sport.id))
        );
        const nextDrillsBySport: Record<string, DrillListItem[]> = {};

        drillResults.forEach((result, index) => {
          nextDrillsBySport[orderedSports[index].id] =
            result.status === "fulfilled" ? result.value : [];
        });

        const artifactResults = await Promise.allSettled(
          progressResult.recent_sessions.map((session) =>
            getSessionArtifacts(session.session_id)
          )
        );
        const nextArtifacts: Record<string, SessionArtifactsResponse> = {};

        artifactResults.forEach((result, index) => {
          if (result.status === "fulfilled") {
            nextArtifacts[progressResult.recent_sessions[index].session_id] = result.value;
          }
        });

        if (ignore) {
          return;
        }

        setSportSummaries(
          orderedSports.map((sport) => ({
            ...sport,
            drillCount: nextDrillsBySport[sport.id]?.length ?? 0
          }))
        );
        setDrillsBySport(nextDrillsBySport);
        setRecentSessions(progressResult.recent_sessions);
        setRecentMetrics(progressResult.recent_metrics);
        setArtifactsBySessionId(nextArtifacts);
      } catch (error) {
        if (!ignore) {
          setDashboardError(getErrorMessage(error));
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    loadDashboard();

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    setSelectedDrillId("all");
  }, [selectedSportId]);

  const profileCompletion = calculateProfileCompletion(profile);
  const startTrainingHref = profile ? `/sports/${profile.sport_id}/drills` : "/sports";
  const availableDrills = sportSummaries.reduce(
    (total, sport) => total + sport.drillCount,
    0
  );
  const selectedSport =
    selectedSportId === "all"
      ? null
      : sportSummaries.find((sport) => sport.id === selectedSportId) ?? null;
  const selectedSportName = selectedSport?.sport_name ?? null;
  const drillOptions = getDrillOptionsForSport(selectedSportId, drillsBySport);
  const selectedDrill =
    selectedDrillId === "all"
      ? null
      : drillOptions.find((drill) => drill.id === selectedDrillId) ?? null;
  const selectedDrillName = selectedDrill?.drill_name ?? null;
  const filteredSessions = recentSessions.filter((session) => {
    if (selectedSportName && session.sport_name !== selectedSportName) {
      return false;
    }

    if (selectedDrillName && session.drill_name !== selectedDrillName) {
      return false;
    }

    return true;
  });
  const filteredMetrics = recentMetrics.filter((metric) => {
    if (selectedSportName && metric.sport_name !== selectedSportName) {
      return false;
    }

    if (selectedDrillName && metric.drill_name !== selectedDrillName) {
      return false;
    }

    return true;
  });
  const analyzedSessions = filteredSessions.map((session) =>
    buildAnalyzedSession(session, artifactsBySessionId[session.session_id])
  );
  const scoreTrendData = buildScoreTrendData(analyzedSessions);
  const metricImprovementData = buildMetricImprovementData(filteredMetrics);
  const drillComparisonData = buildDrillComparisonData(analyzedSessions);
  const recurringInsight = buildRecurringInsightSummary(analyzedSessions);
  const trendSummary = buildTrendSummary(analyzedSessions);
  const coachingInsightSummary = buildDashboardInsightSummary(
    analyzedSessions,
    recurringInsight
  );
  const averageScore = analyzedSessions.length
    ? analyzedSessions.reduce((total, session) => total + session.overall_accuracy, 0) /
      analyzedSessions.length
    : null;
  const bestScore = analyzedSessions.length
    ? Math.max(...analyzedSessions.map((session) => session.overall_accuracy))
    : null;
  const mostCommonIssue = recurringInsight.mostCommonIssue;
  const activeScopeLabel =
    selectedSportName && selectedDrillName
      ? `${selectedSportName} · ${selectedDrillName}`
      : selectedSportName
        ? `${selectedSportName} · All Drills`
        : "All Sports";
  const hasAnySessions = recentSessions.length > 0;
  const hasFilteredSessions = analyzedSessions.length > 0;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader className="h-72" />
        <SkeletonLoader className="h-40" />
        <div className="grid gap-5 xl:grid-cols-5">
          <SkeletonLoader className="h-44" />
          <SkeletonLoader className="h-44" />
          <SkeletonLoader className="h-44" />
          <SkeletonLoader className="h-44" />
          <SkeletonLoader className="h-44" />
        </div>
        <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
          <SkeletonLoader className="h-[380px]" />
          <SkeletonLoader className="h-[380px]" />
        </div>
        <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
          <SkeletonLoader className="h-[360px]" />
          <SkeletonLoader className="h-[360px]" />
        </div>
      </div>
    );
  }

  if (dashboardError) {
    return (
      <EmptyState
        icon={BarChart3}
        title="Analytics dashboard unavailable"
        description={dashboardError}
        action={
          <CTAButton asChild>
            <Link href="/sports">Start Training</Link>
          </CTAButton>
        }
      />
    );
  }

  return (
    <div className="space-y-8">
      <InfoCard className="relative overflow-hidden border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.18),_transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))]">
        <div className="absolute inset-y-0 right-0 hidden w-2/5 bg-[radial-gradient(circle_at_center,_rgba(255,122,0,0.18),_transparent_55%)] lg:block" />
        <div className="relative z-10 flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap gap-2">
              <Badge variant="accent">Performance Dashboard</Badge>
              <Badge variant="slate">{selectedSportName ?? "All Sports"}</Badge>
              {profile?.skill_level ? (
                <Badge variant="slate">{formatEnumLabel(profile.skill_level)}</Badge>
              ) : null}
            </div>
            <h2 className="mt-5 font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">
              {user?.full_name
                ? `${user.full_name}, track your training story.`
                : "Track your training story."}
            </h2>
            <p className="mt-4 max-w-2xl text-sm text-muted-gray sm:text-base">
              Review score trends, recurring weaknesses, drill performance, and coaching signals from your recent analyzed sessions.
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
                <Link href="/sports">
                  Browse Sports
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 xl:w-[430px]">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Active scope
              </p>
              <p className="mt-3 text-sm font-semibold text-white">{activeScopeLabel}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Sessions in view
              </p>
              <p className="mt-3 text-sm font-semibold text-white">
                {analyzedSessions.length}
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Data window
              </p>
              <p className="mt-3 text-sm font-semibold text-white">Up to 10 sessions</p>
            </div>
          </div>
        </div>
      </InfoCard>

      <InfoCard>
        <SectionTitle
          eyebrow="Filters"
          title="Filter your analytics"
          description="Switch the sport focus, then narrow the dashboard to a specific drill when you need a tighter comparison."
          action={
            selectedSportId !== "all" || selectedDrillId !== "all" ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setSelectedSportId("all");
                  setSelectedDrillId("all");
                }}
              >
                Reset Filters
              </Button>
            ) : null
          }
        />

        <div className="mt-6 flex flex-wrap gap-3">
          <Button
            type="button"
            variant={selectedSportId === "all" ? "default" : "outline"}
            className="rounded-2xl"
            onClick={() => setSelectedSportId("all")}
          >
            All Sports
          </Button>
          {sportSummaries.map((sport) => (
            <Button
              key={sport.id}
              type="button"
              variant={selectedSportId === sport.id ? "default" : "outline"}
              className="rounded-2xl"
              onClick={() => setSelectedSportId(sport.id)}
            >
              {sport.sport_name}
            </Button>
          ))}
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Drill filter
            </p>
            <div className="mt-3">
              <Select
                value={selectedDrillId}
                disabled={selectedSportId === "all" || drillOptions.length === 0}
                onChange={(event) => setSelectedDrillId(event.target.value)}
              >
                <option value="all" className="bg-slate text-white">
                  All Drills
                </option>
                {drillOptions.map((drill) => (
                  <option key={drill.id} value={drill.id} className="bg-slate text-white">
                    {drill.drill_name}
                  </option>
                ))}
              </Select>
            </div>
            <p className="mt-3 text-sm leading-6 text-muted-gray">
              {selectedSportId === "all"
                ? "Select a sport to unlock drill-level filtering."
                : drillOptions.length
                  ? "Compare sessions inside a single drill or keep the full sport view."
                  : "No drills are available for this sport yet."}
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Analytics coverage
            </p>
            <p className="mt-3 text-sm leading-7 text-white/85">
              TrainUp uses the recent progress endpoint for up to 10 completed sessions and 50 saved metric values, then applies sport and drill filters client-side.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge variant="accent">{availableDrills} drills indexed</Badge>
              <Badge variant="slate">{recentMetrics.length} metrics loaded</Badge>
              <Badge variant="slate">{profileCompletion}% profile complete</Badge>
            </div>
          </div>
        </div>
      </InfoCard>

      {!hasAnySessions ? (
        <EmptyState
          icon={History}
          title="No analyzed sessions yet"
          description="Complete a few training sessions to unlock score trends, drill comparison, and recurring weakness analytics."
          action={
            <CTAButton asChild>
              <Link href="/sports">Start With a Drill</Link>
            </CTAButton>
          }
        />
      ) : !hasFilteredSessions ? (
        <InfoCard>
          <SectionTitle
            eyebrow="No Match"
            title="No sessions in this filter"
            description="Your current sport and drill filter combination has no completed sessions yet."
          />
          <div className="mt-6 flex flex-wrap gap-3">
            <Button
              type="button"
              onClick={() => {
                setSelectedSportId("all");
                setSelectedDrillId("all");
              }}
            >
              Show All Sports
            </Button>
            <Button asChild variant="outline">
              <Link href="/sports">Start Training</Link>
            </Button>
          </div>
        </InfoCard>
      ) : (
        <>
          <div className="grid gap-5 xl:grid-cols-5">
            <AnalyticsKpiCard
              label="Sessions Completed"
              value={String(analyzedSessions.length)}
              description="Completed reviews in the current analytics view."
              icon={ClipboardCheck}
              tone="accent"
            />
            <AnalyticsKpiCard
              label="Average Score"
              value={formatScoreLabel(averageScore)}
              description="Average overall score across the filtered sessions."
              icon={Gauge}
              tone="success"
            />
            <AnalyticsKpiCard
              label="Best Score"
              value={formatScoreLabel(bestScore)}
              description="Best performance captured inside this filter scope."
              icon={Trophy}
              tone="accent"
            />
            <AnalyticsKpiCard
              label="Current Trend"
              value={trendSummary.value}
              description="How the latest scored session compares with the previous one."
              icon={trendSummary.direction === "down" ? TrendingDown : TrendingUp}
              tone={getTrendTone(trendSummary.direction)}
            />
            <AnalyticsKpiCard
              label="Most Common Issue"
              value={mostCommonIssue ?? "Need more sessions"}
              description="The issue label that appears most often in recent coaching results."
              icon={ShieldAlert}
              tone="warning"
            />
          </div>

          <div className="grid gap-5 xl:grid-cols-[1.18fr_0.82fr]">
            <ScoreTrendChartCard points={scoreTrendData} />

            <InfoCard className="relative overflow-hidden border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.15),_transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))]">
              <SectionTitle
                eyebrow="Coaching"
                title="Training insight summary"
                description="A deterministic summary of what your recent analytics are saying."
              />
              <p className="mt-6 text-sm leading-7 text-white/85">
                {coachingInsightSummary}
              </p>

              <div className="mt-6 flex flex-wrap gap-2">
                {recurringInsight.recurringConcept ? (
                  <Badge variant="accent">{recurringInsight.recurringConcept}</Badge>
                ) : null}
                {recurringInsight.bodyRegion ? (
                  <Badge variant="slate">{recurringInsight.bodyRegion}</Badge>
                ) : null}
                {recurringInsight.temporalBehavior ? (
                  <Badge variant="slate">{recurringInsight.temporalBehavior}</Badge>
                ) : null}
              </div>

              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Current scope
                  </p>
                  <p className="mt-3 text-sm font-semibold text-white">
                    {activeScopeLabel}
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Latest review
                  </p>
                  <p className="mt-3 text-sm font-semibold text-white">
                    {formatDateTime(
                      [...analyzedSessions].sort(
                        (left, right) =>
                          new Date(right.start_time).getTime() -
                          new Date(left.start_time).getTime()
                      )[0].start_time
                    )}
                  </p>
                </div>
              </div>
            </InfoCard>
          </div>

          <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
            <MetricImprovementChartCard points={metricImprovementData} />

            <InfoCard>
              <SectionTitle
                eyebrow="Intelligence"
                title="Recurring weakness intelligence"
                description="These patterns show up most often across the filtered sessions."
              />

              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Recurring focus area
                  </p>
                  <p className="mt-3 text-sm leading-7 text-white/85">
                    {recurringInsight.recurringConceptSentence ??
                      "Complete more sessions to identify a recurring focus area."}
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Repeated body region
                  </p>
                  <p className="mt-3 text-sm leading-7 text-white/85">
                    {recurringInsight.bodyRegionSentence ??
                      "Body-region patterns will appear after more analyzed sessions."}
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Interaction pattern
                  </p>
                  <p className="mt-3 text-sm leading-7 text-white/85">
                    {recurringInsight.interactionSentence ??
                      "Interaction-aware patterns will appear after more analysis."}
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Movement timing
                  </p>
                  <p className="mt-3 text-sm leading-7 text-white/85">
                    {recurringInsight.temporalSentence ??
                      "Timing behavior will appear after more analyzed sessions."}
                  </p>
                </div>
              </div>
            </InfoCard>
          </div>

          <InfoCard>
            <SectionTitle
              eyebrow="Drills"
              title="Drill comparison"
              description="Compare how each drill is performing inside the selected sport filter."
            />

            {drillComparisonData.length ? (
              <div className="mt-6 grid gap-5 xl:grid-cols-3">
                {drillComparisonData.map((drill) => (
                  <div
                    key={drill.drillName}
                    className="rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-5"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                          {drill.sportName}
                        </p>
                        <h3 className="mt-3 font-display text-2xl font-bold text-white">
                          {drill.drillName}
                        </h3>
                      </div>
                      <Badge variant={getTrendTone(drill.trendDirection)}>
                        {drill.trendLabel}
                      </Badge>
                    </div>

                    <div className="mt-6 grid gap-3 sm:grid-cols-3">
                      <div className="rounded-2xl border border-white/10 bg-background-dark/40 p-3">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                          Sessions
                        </p>
                        <p className="mt-2 text-xl font-bold text-white">
                          {drill.sessions}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-background-dark/40 p-3">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                          Avg score
                        </p>
                        <p className="mt-2 text-xl font-bold text-white">
                          {drill.averageScore.toFixed(0)}%
                        </p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-background-dark/40 p-3">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                          Best
                        </p>
                        <p className="mt-2 text-xl font-bold text-white">
                          {drill.bestScore.toFixed(0)}%
                        </p>
                      </div>
                    </div>

                    <div className="mt-5 rounded-2xl border border-white/10 bg-background-dark/40 p-4">
                      <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                        Main issue
                      </p>
                      <p className="mt-3 text-sm leading-6 text-white/85">
                        {drill.mainIssue ??
                          "More analyzed sessions are needed to identify a consistent issue."}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 text-sm leading-7 text-muted-gray">
                Complete more sessions to unlock drill comparison.
              </div>
            )}
          </InfoCard>

          <InfoCard>
            <SectionTitle
              eyebrow="Sessions"
              title="Recent sessions"
              description="Open a session to revisit the detailed coaching results."
            />

            <div className="mt-6 overflow-hidden rounded-[1.5rem] border border-white/10 bg-white/[0.03]">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-white/10 text-sm">
                  <thead className="bg-white/[0.03]">
                    <tr className="text-left text-xs uppercase tracking-[0.22em] text-muted-gray">
                      <th className="px-4 py-4 font-medium">Date</th>
                      <th className="px-4 py-4 font-medium">Sport</th>
                      <th className="px-4 py-4 font-medium">Drill</th>
                      <th className="px-4 py-4 font-medium">Score</th>
                      <th className="px-4 py-4 font-medium">Severity</th>
                      <th className="px-4 py-4 font-medium">Main Focus</th>
                      <th className="px-4 py-4 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/10">
                    {[...analyzedSessions]
                      .sort(
                        (left, right) =>
                          new Date(right.start_time).getTime() -
                          new Date(left.start_time).getTime()
                      )
                      .map((session) => (
                        <tr key={session.session_id} className="align-top">
                          <td className="px-4 py-4 text-white/85">
                            {formatDateTime(session.start_time)}
                          </td>
                          <td className="px-4 py-4 text-white/75">{session.sport_name}</td>
                          <td className="px-4 py-4">
                            <div className="font-semibold text-white">{session.drill_name}</div>
                            <div className="mt-1 text-xs uppercase tracking-[0.18em] text-muted-gray">
                              {formatEnumLabel(session.input_type)}
                            </div>
                          </td>
                          <td className="px-4 py-4 text-white">
                            {session.overall_accuracy.toFixed(0)}%
                          </td>
                          <td className="px-4 py-4">
                            {session.severity ? (
                              <Badge variant={getSeverityVariant(session.severity)}>
                                {session.severity}
                              </Badge>
                            ) : (
                              <span className="text-white/45">Pending</span>
                            )}
                          </td>
                          <td className="px-4 py-4 text-white/85">
                            {session.mainFocus ?? session.mainIssue ?? "Review detailed coaching"}
                          </td>
                          <td className="px-4 py-4">
                            <Button asChild variant="outline">
                              <Link
                                href={
                                  session.input_type === "LIVE"
                                    ? `/sessions/${session.session_id}/live`
                                    : `/sessions/${session.session_id}/upload`
                                }
                              >
                                View Session
                              </Link>
                            </Button>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </InfoCard>
        </>
      )}
    </div>
  );
}

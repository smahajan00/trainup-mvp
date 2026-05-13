"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  ClipboardCheck,
  Gauge,
  History,
  ShieldAlert,
  Target,
  TrendingDown,
  TrendingUp,
  Trophy
} from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { CTAButton } from "../../../components/ui/cta-button";
import { Select } from "../../../components/ui/select";
import { SkeletonLoader } from "../../../components/ui/skeleton-loader";
import { getErrorMessage } from "../../../lib/api";
import { formatDateTime, formatEnumLabel } from "../../../lib/formatters";
import { getDrillsBySport } from "../../../services/drills";
import { getRecentProgress } from "../../../services/progress";
import { getSessionArtifacts } from "../../../services/sessions";
import { getSports } from "../../../services/sports";
import type { CurrentUserResponse } from "../../../types/auth";
import type { DrillListItem } from "../../../types/drills";
import type { ProfileResponse } from "../../../types/profile";
import type {
  ProgressRange,
  RecentProgressResponse,
  RecentMetricProgress,
  RecentProgressSession
} from "../../../types/progress";
import type { SessionArtifactsResponse } from "../../../types/sessions";
import type { SportOption } from "../../../types/sports";
import { EmptyState } from "../../app-shell/components/EmptyState";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { SectionTitle } from "../../app-shell/components/SectionTitle";
import {
  buildAnalyzedSession,
  buildDrillComparisonData,
  buildMetricImprovementData,
  buildRecurringInsightSummary,
  buildScoreTrendData,
  buildTrendSummary,
  formatScoreLabel,
  getDrillOptionsForSport,
  getSeverityVariant,
  type DashboardAnalyzedSession,
  type DashboardDrillComparison,
  type DashboardRecurringInsight
} from "../analytics-utils";
import { AnalyticsKpiCard } from "./AnalyticsKpiCard";
import { MetricImprovementChartCard } from "./MetricImprovementChartCard";
import { ScoreTrendChartCard } from "./ScoreTrendChartCard";

type ProgressAnalyticsViewProps = {
  user: CurrentUserResponse | null;
  profile: ProfileResponse | null;
};

type SportSummary = SportOption & {
  drillCount: number;
};

type NextTrainingFocus = {
  focusArea: string;
  recommendedDrill: string;
  recommendedSportName: string;
  coachingCue: string;
};

const FILTER_SPORT_ORDER = ["Gym", "Basketball", "Football"];
const RANGE_OPTIONS: { value: ProgressRange; label: string }[] = [
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "all_time", label: "All Time" }
];
const RANGE_LABELS: Record<
  ProgressRange,
  {
    dataWindow: string;
    sessionDescription: string;
    averageDescription: string;
    bestDescription: string;
    emptyTitle: string;
    emptyDescription: string;
  }
> = {
  weekly: {
    dataWindow: "Last 7 days",
    sessionDescription: "Sessions this week",
    averageDescription: "Average this week",
    bestDescription: "Best this week",
    emptyTitle: "No analyzed sessions this week yet.",
    emptyDescription: "Complete an analyzed session this week to see weekly progress."
  },
  monthly: {
    dataWindow: "Last 30 days",
    sessionDescription: "Sessions this month",
    averageDescription: "Average this month",
    bestDescription: "Best this month",
    emptyTitle: "No analyzed sessions this month yet.",
    emptyDescription: "Complete an analyzed session this month to see monthly progress."
  },
  all_time: {
    dataWindow: "All completed analysis",
    sessionDescription: "Total analyzed sessions",
    averageDescription: "All-time average",
    bestDescription: "All-time best",
    emptyTitle: "No analyzed sessions yet.",
    emptyDescription: "Log a few analyzed sessions to unlock score trends, drill breakdowns, and recurring coaching intelligence."
  }
};

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

function getLatestSession(sessions: DashboardAnalyzedSession[]) {
  return [...sessions].sort(
    (left, right) =>
      new Date(right.start_time).getTime() - new Date(left.start_time).getTime()
  )[0] ?? null;
}

function buildNextTrainingFocus(
  sessions: DashboardAnalyzedSession[],
  drills: DashboardDrillComparison[],
  recurringInsight: DashboardRecurringInsight
): NextTrainingFocus | null {
  if (!sessions.length) {
    return null;
  }

  const latestSession = getLatestSession(sessions);
  const recommendedDrill =
    [...drills].sort((left, right) => left.averageScore - right.averageScore)[0] ??
    null;
  const sessionForRecommendedDrill =
    recommendedDrill && latestSession
      ? sessions.find(
          (session) =>
            session.drill_name === recommendedDrill.drillName &&
            session.coachingAction
        ) ?? latestSession
      : latestSession;

  return {
    focusArea:
      recurringInsight.mostCommonIssue ??
      sessionForRecommendedDrill?.mainIssue ??
      sessionForRecommendedDrill?.mainFocus ??
      "Controlled movement quality",
    recommendedDrill: recommendedDrill?.drillName ?? latestSession?.drill_name ?? "Next drill",
    recommendedSportName:
      recommendedDrill?.sportName ?? latestSession?.sport_name ?? "Training",
    coachingCue:
      sessionForRecommendedDrill?.coachingAction ??
      recurringInsight.temporalSentence ??
      "Repeat the drill at controlled speed and keep the first cue simple."
  };
}

function getFocusSessionHref(
  nextFocus: NextTrainingFocus | null,
  sportSummaries: SportSummary[],
  fallbackHref: string
) {
  if (!nextFocus) {
    return fallbackHref;
  }

  const sport = sportSummaries.find(
    (item) => item.sport_name === nextFocus.recommendedSportName
  );
  return sport ? `/sports/${sport.id}/drills` : fallbackHref;
}

function valueOrFallback(value: string | null | undefined, fallback: string) {
  return value && value.trim() ? value : fallback;
}

export function ProgressAnalyticsView({ profile }: ProgressAnalyticsViewProps) {
  const [sportSummaries, setSportSummaries] = useState<SportSummary[]>([]);
  const [drillsBySport, setDrillsBySport] = useState<Record<string, DrillListItem[]>>(
    {}
  );
  const [recentSessions, setRecentSessions] = useState<RecentProgressSession[]>([]);
  const [recentMetrics, setRecentMetrics] = useState<RecentMetricProgress[]>([]);
  const [rangeSummary, setRangeSummary] = useState<RecentProgressResponse | null>(null);
  const [artifactsBySessionId, setArtifactsBySessionId] = useState<
    Record<string, SessionArtifactsResponse>
  >({});
  const [selectedRange, setSelectedRange] = useState<ProgressRange>("monthly");
  const [selectedSportId, setSelectedSportId] = useState("all");
  const [selectedDrillId, setSelectedDrillId] = useState("all");
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshingRange, setIsRefreshingRange] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const hasLoadedDashboardRef = useRef(false);

  useEffect(() => {
    let ignore = false;

    async function loadDashboard() {
      setDashboardError(null);
      if (hasLoadedDashboardRef.current) {
        setIsRefreshingRange(true);
      }

      try {
        const [sports, progressResult] = await Promise.all([
          getSports(),
          getRecentProgress(10, 50, selectedRange)
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
        setRangeSummary(progressResult);
        setArtifactsBySessionId(nextArtifacts);
      } catch (error) {
        if (!ignore) {
          setDashboardError(getErrorMessage(error));
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
          setIsRefreshingRange(false);
          hasLoadedDashboardRef.current = true;
        }
      }
    }

    loadDashboard();

    return () => {
      ignore = true;
    };
  }, [selectedRange]);

  useEffect(() => {
    setSelectedDrillId("all");
  }, [selectedSportId]);

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
  const selectedRangeLabels = RANGE_LABELS[selectedRange];
  const rangeSessionCount = rangeSummary?.total_analyzed_sessions ?? recentSessions.length;
  const hasActiveDetailFilter = Boolean(selectedSportName || selectedDrillName);
  const filteredAverageScore = analyzedSessions.length
    ? analyzedSessions.reduce((total, session) => total + session.overall_accuracy, 0) /
      analyzedSessions.length
    : null;
  const filteredBestScore = analyzedSessions.length
    ? Math.max(...analyzedSessions.map((session) => session.overall_accuracy))
    : null;
  const averageScore = hasActiveDetailFilter
    ? filteredAverageScore
    : rangeSummary?.average_score ?? filteredAverageScore;
  const bestScore = hasActiveDetailFilter
    ? filteredBestScore
    : rangeSummary?.best_score ?? filteredBestScore;
  const displaySessionCount = hasActiveDetailFilter
    ? analyzedSessions.length
    : rangeSessionCount;
  const rangeTrendDirection =
    rangeSummary?.trend_delta === null || rangeSummary?.trend_delta === undefined
      ? ("insufficient" as const)
      : Math.abs(rangeSummary.trend_delta) < 1
        ? ("flat" as const)
        : rangeSummary.trend_delta > 0
          ? ("up" as const)
          : ("down" as const);
  const displayTrendValue = hasActiveDetailFilter
    ? trendSummary.value
    : rangeSummary?.trend_label ?? trendSummary.value;
  const displayTrendDirection = hasActiveDetailFilter
    ? trendSummary.direction
    : rangeTrendDirection;
  const mostCommonIssue = recurringInsight.mostCommonIssue;
  const activeScopeLabel =
    selectedSportName && selectedDrillName
      ? `${selectedSportName} / ${selectedDrillName}`
      : selectedSportName
        ? `${selectedSportName} / All drills`
        : "All Sports";
  const hasAnySessions = rangeSessionCount > 0;
  const hasFilteredSessions = analyzedSessions.length > 0;
  const nextTrainingFocus = buildNextTrainingFocus(
    analyzedSessions,
    drillComparisonData,
    recurringInsight
  );
  const nextTrainingHref = getFocusSessionHref(
    nextTrainingFocus,
    sportSummaries,
    startTrainingHref
  );
  const coachReadItems = [
    {
      label: "Trend",
      value: displayTrendValue
    },
    {
      label: "Key weakness",
      value: valueOrFallback(mostCommonIssue, "No repeated weakness yet")
    },
    {
      label: "Pattern",
      value: valueOrFallback(
        recurringInsight.interactionSentence ?? recurringInsight.temporalSentence,
        "More analyzed sessions will reveal a clearer pattern."
      )
    },
    {
      label: "Next focus",
      value: valueOrFallback(
        nextTrainingFocus?.coachingCue,
        "Complete more sessions to unlock a focused recommendation."
      )
    }
  ];

  if (isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonLoader className="h-64" />
        <SkeletonLoader className="h-28" />
        <div className="grid gap-4 xl:grid-cols-5">
          <SkeletonLoader className="h-32" />
          <SkeletonLoader className="h-32" />
          <SkeletonLoader className="h-32" />
          <SkeletonLoader className="h-32" />
          <SkeletonLoader className="h-32" />
        </div>
        <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
          <SkeletonLoader className="h-[340px]" />
          <SkeletonLoader className="h-[340px]" />
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
    <div className="space-y-6">
      <InfoCard className="border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.16),_transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))] p-5 sm:p-7">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_430px] xl:items-end">
          <div className="min-w-0">
            <Badge variant="accent">Performance Dashboard</Badge>
            <h1 className="mt-4 break-words font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">
              Performance Dashboard
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-muted-gray sm:text-base">
              Track your score trends, training patterns, and key focus areas across sessions.
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

          <div className="grid min-w-0 gap-3 sm:grid-cols-3">
            <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                Active scope
              </p>
              <p className="mt-2 line-clamp-2 text-sm font-semibold text-white">
                {activeScopeLabel}
              </p>
            </div>
            <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                Sessions in view
              </p>
              <p className="mt-2 text-2xl font-bold text-white">
                {displaySessionCount}
              </p>
            </div>
            <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                Data window
              </p>
              <p className="mt-2 text-sm font-semibold text-white">
                {selectedRangeLabels.dataWindow}
              </p>
            </div>
          </div>
        </div>
      </InfoCard>

      <InfoCard className="p-4 sm:p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">
              Filters
            </p>
            <h2 className="mt-1 font-display text-2xl font-bold tracking-tight text-white">
              Focus your training view
            </h2>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-gray">
              <Badge variant="slate" className="max-w-full">
                Data coverage
              </Badge>
              <span>{rangeSessionCount} in range</span>
              <span>showing latest {recentSessions.length}</span>
              <span>{recentMetrics.length} metrics</span>
              <span>{availableDrills} drills</span>
              {isRefreshingRange ? <span>Updating...</span> : null}
            </div>
          </div>

          <div className="flex min-w-0 flex-col gap-3 lg:flex-row lg:items-center">
            <div className="flex flex-wrap gap-2 rounded-2xl border border-white/10 bg-white/[0.03] p-1">
              {RANGE_OPTIONS.map((option) => (
                <Button
                  key={option.value}
                  type="button"
                  size="sm"
                  variant={selectedRange === option.value ? "default" : "ghost"}
                  className="rounded-xl"
                  onClick={() => setSelectedRange(option.value)}
                >
                  {option.label}
                </Button>
              ))}
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
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
                  size="sm"
                  variant={selectedSportId === sport.id ? "default" : "outline"}
                  className="rounded-2xl"
                  onClick={() => setSelectedSportId(sport.id)}
                >
                  {sport.sport_name}
                </Button>
              ))}
            </div>

            {selectedSportId !== "all" ? (
              <div className="w-full min-w-0 sm:w-64">
                <Select
                  value={selectedDrillId}
                  disabled={drillOptions.length === 0}
                  className="h-10 rounded-2xl text-sm"
                  onChange={(event) => setSelectedDrillId(event.target.value)}
                >
                  <option value="all" className="bg-slate text-white">
                    All Drills
                  </option>
                  {drillOptions.map((drill) => (
                    <option
                      key={drill.id}
                      value={drill.id}
                      className="bg-slate text-white"
                    >
                      {drill.drill_name}
                    </option>
                  ))}
                </Select>
              </div>
            ) : null}

            {selectedSportId !== "all" || selectedDrillId !== "all" ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => {
                  setSelectedSportId("all");
                  setSelectedDrillId("all");
                }}
              >
                Reset filters
              </Button>
            ) : null}
          </div>
        </div>
      </InfoCard>

      {!hasAnySessions ? (
        <EmptyState
          icon={History}
          title={selectedRangeLabels.emptyTitle}
          description={selectedRangeLabels.emptyDescription}
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
            description="This sport and drill combination does not have an analyzed session yet."
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
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <AnalyticsKpiCard
              label="Sessions"
              value={String(displaySessionCount)}
              description={selectedRangeLabels.sessionDescription}
              icon={ClipboardCheck}
              tone="accent"
            />
            <AnalyticsKpiCard
              label="Avg Score"
              value={formatScoreLabel(averageScore)}
              description={
                hasActiveDetailFilter ? "Filtered view" : selectedRangeLabels.averageDescription
              }
              icon={Gauge}
              tone="success"
            />
            <AnalyticsKpiCard
              label="Best"
              value={formatScoreLabel(bestScore)}
              description={
                hasActiveDetailFilter ? "Top filtered session" : selectedRangeLabels.bestDescription
              }
              icon={Trophy}
              tone="accent"
            />
            <AnalyticsKpiCard
              label="Trend"
              value={displayTrendValue}
              description="Updated"
              icon={displayTrendDirection === "down" ? TrendingDown : TrendingUp}
              tone={getTrendTone(displayTrendDirection)}
            />
            <AnalyticsKpiCard
              label="Key Weakness"
              value={mostCommonIssue ?? "Need more sessions"}
              description="Current pattern"
              icon={ShieldAlert}
              tone="warning"
            />
          </div>

          <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
            <ScoreTrendChartCard points={scoreTrendData} />

            <InfoCard className="min-w-0 border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.12),_transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))]">
              <SectionTitle
                eyebrow="Coaching"
                title="Coach's Read"
                description="The current answer to what is improving and what to train next."
              />

              <div className="mt-6 grid gap-3">
                {coachReadItems.map((item) => (
                  <div
                    key={item.label}
                    className="rounded-2xl border border-white/10 bg-white/[0.04] p-4"
                  >
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                      {item.label}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-white/85">
                      {item.value}
                    </p>
                  </div>
                ))}
              </div>

              <div className="mt-5 flex flex-wrap gap-2">
                {recurringInsight.recurringConcept ? (
                  <Badge variant="accent" className="max-w-full">
                    {recurringInsight.recurringConcept}
                  </Badge>
                ) : null}
                {recurringInsight.bodyRegion ? (
                  <Badge variant="slate" className="max-w-full">
                    {recurringInsight.bodyRegion}
                  </Badge>
                ) : null}
                {recurringInsight.temporalBehavior ? (
                  <Badge variant="slate" className="max-w-full">
                    {recurringInsight.temporalBehavior}
                  </Badge>
                ) : null}
              </div>
            </InfoCard>
          </div>

          <div className="grid items-stretch gap-5 xl:grid-cols-[1fr_1fr]">
            <MetricImprovementChartCard points={metricImprovementData} />

            <InfoCard className="min-w-0">
              <SectionTitle
                eyebrow="Intelligence"
                title="Training Intelligence"
                description="Recurring signals from the current dashboard view."
              />

              <div className="mt-6 grid items-stretch gap-4 sm:grid-cols-2">
                {[
                  {
                    label: "Main focus",
                    value:
                      recurringInsight.recurringConceptSentence ??
                      "Complete more sessions to surface a main focus."
                  },
                  {
                    label: "Body control",
                    value:
                      recurringInsight.bodyRegionSentence ??
                      "Body-control patterns will appear after more analyzed sessions."
                  },
                  {
                    label: "Pattern",
                    value:
                      recurringInsight.interactionSentence ??
                      "Pattern signals will appear after more analysis."
                  },
                  {
                    label: "Timing",
                    value:
                      recurringInsight.temporalSentence ??
                      "Timing behavior will appear after more analyzed sessions."
                  }
                ].map((item) => (
                  <div
                    key={item.label}
                    className="flex min-w-0 flex-col rounded-2xl border border-white/10 bg-white/[0.04] p-4"
                  >
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                      {item.label}
                    </p>
                    <p className="mt-3 text-sm leading-6 text-white/85">
                      {item.value}
                    </p>
                  </div>
                ))}
              </div>
            </InfoCard>
          </div>

          <InfoCard className="border-primary/15 bg-[linear-gradient(135deg,rgba(255,122,0,0.12),rgba(255,255,255,0.035))] p-5 sm:p-6">
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-center">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="accent">Next Step</Badge>
                  {nextTrainingFocus ? (
                    <Badge variant="slate" className="max-w-full">
                      {nextTrainingFocus.recommendedSportName}
                    </Badge>
                  ) : null}
                </div>
                <h2 className="mt-4 font-display text-3xl font-bold tracking-tight text-white">
                  Next Training Focus
                </h2>
                {nextTrainingFocus ? (
                  <div className="mt-5 grid gap-4 md:grid-cols-3">
                    <div className="min-w-0 rounded-2xl border border-white/10 bg-background-dark/35 p-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                        Focus area
                      </p>
                      <p className="mt-2 break-words text-sm font-semibold text-white">
                        {nextTrainingFocus.focusArea}
                      </p>
                    </div>
                    <div className="min-w-0 rounded-2xl border border-white/10 bg-background-dark/35 p-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                        Recommended drill
                      </p>
                      <p className="mt-2 break-words text-sm font-semibold text-white">
                        {nextTrainingFocus.recommendedDrill}
                      </p>
                    </div>
                    <div className="min-w-0 rounded-2xl border border-white/10 bg-background-dark/35 p-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                        Coaching cue
                      </p>
                      <p className="mt-2 text-sm leading-6 text-white/85">
                        {nextTrainingFocus.coachingCue}
                      </p>
                    </div>
                  </div>
                ) : (
                  <p className="mt-4 text-sm leading-6 text-muted-gray">
                    Complete more sessions to unlock a focused recommendation.
                  </p>
                )}
              </div>

              <CTAButton asChild>
                <Link href={nextTrainingHref}>
                  Start Focus Session
                  <Target className="ml-2 h-4 w-4" />
                </Link>
              </CTAButton>
            </div>
          </InfoCard>

          <InfoCard>
            <SectionTitle
              eyebrow="Drills"
              title="Drill Breakdown"
              description="Compare which drills are improving inside the selected scope."
            />

            {drillComparisonData.length ? (
              <div className="mt-6 grid gap-4 xl:grid-cols-3">
                {drillComparisonData.map((drill) => (
                  <div
                    key={`${drill.sportName}-${drill.drillName}`}
                    className="flex min-w-0 flex-col rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-5"
                  >
                    <div className="flex min-w-0 items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                          {drill.sportName}
                        </p>
                        <h3 className="mt-2 break-words font-display text-2xl font-bold leading-tight text-white">
                          {drill.drillName}
                        </h3>
                      </div>
                      <Badge
                        variant={getTrendTone(drill.trendDirection)}
                        className="shrink-0 whitespace-nowrap"
                      >
                        {drill.trendLabel}
                      </Badge>
                    </div>

                    <div className="mt-5 grid grid-cols-3 gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-muted-gray">
                          Avg
                        </p>
                        <p className="mt-1 text-2xl font-bold text-white">
                          {drill.averageScore.toFixed(0)}%
                        </p>
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-muted-gray">
                          Best
                        </p>
                        <p className="mt-1 text-2xl font-bold text-white">
                          {drill.bestScore.toFixed(0)}%
                        </p>
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-muted-gray">
                          Sessions
                        </p>
                        <p className="mt-1 text-2xl font-bold text-white">
                          {drill.sessions}
                        </p>
                      </div>
                    </div>

                    <div className="mt-5 border-t border-white/10 pt-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                        Main issue
                      </p>
                      <p className="mt-2 line-clamp-3 text-sm leading-6 text-white/85">
                        {drill.mainIssue ??
                          "More analyzed sessions are needed to identify a consistent issue."}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 text-sm leading-7 text-muted-gray">
                Log more sessions to unlock your drill breakdown.
              </div>
            )}
          </InfoCard>

          <InfoCard>
            <SectionTitle
              eyebrow="Sessions"
              title="Recent Sessions"
              description={`Recent sessions in selected range. Showing latest ${analyzedSessions.length}.`}
            />

            <div className="mt-6 overflow-hidden rounded-[1.5rem] border border-white/10 bg-white/[0.03]">
              <div className="overflow-x-auto">
                <table className="min-w-[920px] divide-y divide-white/10 text-sm">
                  <thead className="bg-white/[0.03]">
                    <tr className="text-left text-xs uppercase tracking-[0.18em] text-muted-gray">
                      <th className="w-[150px] px-4 py-4 font-medium">Date</th>
                      <th className="w-[120px] px-4 py-4 font-medium">Sport</th>
                      <th className="w-[210px] px-4 py-4 font-medium">Drill</th>
                      <th className="w-[90px] px-4 py-4 font-medium">Score</th>
                      <th className="w-[120px] px-4 py-4 font-medium">Severity</th>
                      <th className="px-4 py-4 font-medium">Focus</th>
                      <th className="w-[140px] px-4 py-4 font-medium">Action</th>
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
                        <tr key={session.session_id} className="align-middle">
                          <td className="px-4 py-4 text-white/80">
                            <span className="block whitespace-nowrap">
                              {formatDateTime(session.start_time)}
                            </span>
                          </td>
                          <td className="px-4 py-4 text-white/75">{session.sport_name}</td>
                          <td className="px-4 py-4">
                            <div className="max-w-[200px] break-words font-semibold leading-5 text-white">
                              {session.drill_name}
                            </div>
                            <div className="mt-1 text-xs uppercase tracking-[0.16em] text-muted-gray">
                              {formatEnumLabel(session.input_type)}
                            </div>
                          </td>
                          <td className="px-4 py-4">
                            <span className="font-display text-2xl font-bold text-white">
                              {session.overall_accuracy.toFixed(0)}%
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            {session.severity ? (
                              <Badge
                                variant={getSeverityVariant(session.severity)}
                                className="whitespace-nowrap tracking-[0.16em]"
                              >
                                {session.severity}
                              </Badge>
                            ) : (
                              <span className="text-white/45">Pending</span>
                            )}
                          </td>
                          <td className="px-4 py-4 text-white/85">
                            <span className="line-clamp-2 max-w-[260px] leading-6">
                              {session.mainFocus ??
                                session.mainIssue ??
                                "Review detailed coaching"}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <Button asChild variant="outline" size="sm">
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

import { formatEnumLabel, formatTokenLabel } from "../../lib/formatters";
import type { DrillListItem } from "../../types/drills";
import type {
  RecentMetricProgress,
  RecentProgressSession
} from "../../types/progress";
import type {
  SeverityLevel,
  SessionArtifactsResponse,
  TemporalState
} from "../../types/sessions";

export type DashboardAnalyzedSession = RecentProgressSession & {
  sessionHref: string;
  severity: SeverityLevel | null;
  mainFocus: string | null;
  mainIssue: string | null;
  primaryConcept: string | null;
  bodyRegion: string | null;
  interactionGroup: string | null;
  interactionExplanation: string | null;
  temporalState: TemporalState | null;
  temporalSummary: string | null;
  coachingAction: string | null;
};

export type DashboardScoreTrendPoint = {
  label: string;
  fullLabel: string;
  score: number;
  movingAverage: number | null;
  isLatest: boolean;
};

export type DashboardMetricImprovementPoint = {
  metricName: string;
  shortLabel: string;
  change: number;
  average: number;
  latest: number;
  unit: string;
  samples: number;
  hasTrend: boolean;
};

export type DashboardDrillComparison = {
  drillName: string;
  sportName: string;
  sessions: number;
  averageScore: number;
  bestScore: number;
  trendDirection: "up" | "down" | "flat" | "insufficient";
  trendLabel: string;
  mainIssue: string | null;
};

export type DashboardRecurringInsight = {
  recurringConcept: string | null;
  recurringConceptSentence: string | null;
  bodyRegion: string | null;
  bodyRegionSentence: string | null;
  interactionPattern: string | null;
  interactionSentence: string | null;
  temporalBehavior: string | null;
  temporalSentence: string | null;
  mostCommonIssue: string | null;
};

export function getSeverityVariant(severity?: SeverityLevel | null) {
  if (severity === "SEVERE") {
    return "danger" as const;
  }

  if (severity === "MODERATE") {
    return "warning" as const;
  }

  if (severity === "MINOR") {
    return "success" as const;
  }

  return "slate" as const;
}

export function formatDashboardLabel(value?: string | null) {
  if (!value) {
    return null;
  }

  if (/[_-]/.test(value) || value === value.toUpperCase()) {
    return formatEnumLabel(value);
  }

  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function normalizeDashboardLabel(value?: string | null) {
  if (!value) {
    return "";
  }

  return value
    .toLowerCase()
    .replace(/[_-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function formatScoreLabel(score?: number | null) {
  if (score === null || score === undefined || Number.isNaN(score)) {
    return "Not enough data";
  }

  return `${score.toFixed(0)}%`;
}

export function formatShortDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric"
  }).format(new Date(value));
}

export function buildSessionHref(session: RecentProgressSession) {
  return session.input_type === "LIVE"
    ? `/sessions/${session.session_id}/live`
    : `/sessions/${session.session_id}/upload`;
}

export function getDrillOptionsForSport(
  selectedSportId: string,
  drillsBySport: Record<string, DrillListItem[]>
) {
  if (selectedSportId === "all") {
    return [];
  }

  return drillsBySport[selectedSportId] ?? [];
}

function getModeLabel(values: Array<string | null | undefined>) {
  const counts = new Map<string, { count: number; label: string }>();

  values.forEach((value) => {
    if (!value) {
      return;
    }

    const key = normalizeDashboardLabel(value);
    if (!key) {
      return;
    }

    const current = counts.get(key);
    counts.set(key, {
      count: (current?.count ?? 0) + 1,
      label: current?.label ?? value
    });
  });

  return [...counts.values()].sort((left, right) => right.count - left.count)[0]?.label ?? null;
}

function getChoquetExplanation(artifacts?: SessionArtifactsResponse | null) {
  const choquet = artifacts?.choquet_aggregation_result;

  if (!choquet) {
    return { group: null, explanation: null };
  }

  if (
    choquet.dominant_interaction_group &&
    choquet.concept_aggregation[choquet.dominant_interaction_group]
  ) {
    return {
      group: choquet.dominant_interaction_group,
      explanation:
        choquet.concept_aggregation[choquet.dominant_interaction_group]?.explanation ?? null
    };
  }

  const interactionGroup = Object.entries(choquet.concept_aggregation).find(
    ([, group]) => group.interaction_detected
  );

  if (interactionGroup) {
    return {
      group: interactionGroup[0],
      explanation: interactionGroup[1].explanation
    };
  }

  return { group: null, explanation: null };
}

export function buildAnalyzedSession(
  session: RecentProgressSession,
  artifacts?: SessionArtifactsResponse | null
): DashboardAnalyzedSession {
  const evaluationResult = artifacts?.evaluation_result ?? null;
  const feedbackResult = artifacts?.feedback_result ?? null;
  const pedagogyResult = artifacts?.pedagogical_decision_result ?? null;
  const ontologyResult = artifacts?.ontology_reasoning_result ?? null;
  const temporalResult = artifacts?.temporal_modeling_result ?? null;
  const sessionSummary = artifacts?.session_summary ?? null;
  const choquetInsight = getChoquetExplanation(artifacts);
  const mainFocus =
    formatDashboardLabel(pedagogyResult?.selected_focus_items[0]?.metric_name ?? null) ??
    formatDashboardLabel(feedbackResult?.prioritized_feedback_items[0]?.metric_name ?? null) ??
    formatDashboardLabel(sessionSummary?.weaknesses.issues[0]?.metric ?? null);
  const mainIssue =
    formatDashboardLabel(
      feedbackResult?.prioritized_feedback_items[0]?.issue_title ?? null
    ) ??
    formatDashboardLabel(sessionSummary?.weaknesses.issues[0]?.issue_label ?? null) ??
    formatDashboardLabel(evaluationResult?.weakest_metrics[0]?.metric_name ?? null);
  const bodyRegion =
    formatDashboardLabel(
      feedbackResult?.prioritized_feedback_items[0]?.affected_body_part ?? null
    ) ??
    formatDashboardLabel(evaluationResult?.detected_issues[0]?.affected_body_part ?? null) ??
    formatDashboardLabel(Object.keys(ontologyResult?.body_region_summary ?? {})[0] ?? null);

  return {
    ...session,
    sessionHref: buildSessionHref(session),
    severity: evaluationResult?.overall_severity ?? null,
    mainFocus,
    mainIssue,
    primaryConcept: formatDashboardLabel(ontologyResult?.primary_concept ?? null),
    bodyRegion,
    interactionGroup: formatDashboardLabel(choquetInsight.group),
    interactionExplanation: choquetInsight.explanation,
    temporalState: temporalResult?.overall_temporal_state ?? null,
    temporalSummary: temporalResult?.temporal_summary ?? null,
    coachingAction:
      pedagogyResult?.progression_advice ??
      feedbackResult?.improvement_suggestions[0] ??
      sessionSummary?.recommendations.actions[0] ??
      null
  };
}

export function buildScoreTrendData(
  sessions: DashboardAnalyzedSession[]
): DashboardScoreTrendPoint[] {
  const orderedSessions = [...sessions].sort(
    (left, right) =>
      new Date(left.start_time).getTime() - new Date(right.start_time).getTime()
  );

  return orderedSessions.map((session, index) => {
    const scoreWindow = orderedSessions
      .slice(Math.max(0, index - 2), index + 1)
      .map((item) => item.overall_accuracy);
    const movingAverage =
      scoreWindow.length >= 2
        ? scoreWindow.reduce((total, value) => total + value, 0) / scoreWindow.length
        : null;

    return {
      label: formatShortDate(session.start_time),
      fullLabel: new Date(session.start_time).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric"
      }),
      score: session.overall_accuracy,
      movingAverage,
      isLatest: index === orderedSessions.length - 1
    };
  });
}

export function buildMetricImprovementData(
  metrics: RecentMetricProgress[]
): DashboardMetricImprovementPoint[] {
  const groupedMetrics = metrics.reduce<Record<string, RecentMetricProgress[]>>(
    (accumulator, metric) => {
      if (!accumulator[metric.metric_name]) {
        accumulator[metric.metric_name] = [];
      }

      accumulator[metric.metric_name].push(metric);
      return accumulator;
    },
    {}
  );

  return Object.entries(groupedMetrics)
    .map(([metricName, metricItems]) => {
      const orderedItems = [...metricItems].sort(
        (left, right) =>
          new Date(left.created_at).getTime() - new Date(right.created_at).getTime()
      );
      const firstValue = orderedItems[0]?.metric_value ?? 0;
      const latestValue = orderedItems[orderedItems.length - 1]?.metric_value ?? 0;
      const averageValue =
        orderedItems.reduce((total, item) => total + item.metric_value, 0) /
        orderedItems.length;
      const hasTrend = orderedItems.length > 1;
      const change =
        hasTrend && firstValue !== 0
          ? ((latestValue - firstValue) / Math.abs(firstValue)) * 100
          : 0;

      return {
        metricName,
        shortLabel: formatTokenLabel(metricName),
        change,
        average: averageValue,
        latest: latestValue,
        unit: orderedItems[orderedItems.length - 1]?.metric_unit ?? "",
        samples: orderedItems.length,
        hasTrend
      };
    })
    .sort((left, right) => {
      if (right.samples !== left.samples) {
        return right.samples - left.samples;
      }

      return Math.abs(right.change) - Math.abs(left.change);
    })
    .slice(0, 6);
}

export function buildDrillComparisonData(
  sessions: DashboardAnalyzedSession[]
): DashboardDrillComparison[] {
  const groupedSessions = sessions.reduce<Record<string, DashboardAnalyzedSession[]>>(
    (accumulator, session) => {
      if (!accumulator[session.drill_name]) {
        accumulator[session.drill_name] = [];
      }

      accumulator[session.drill_name].push(session);
      return accumulator;
    },
    {}
  );

  return Object.entries(groupedSessions)
    .map(([drillName, drillSessions]) => {
      const orderedSessions = [...drillSessions].sort(
        (left, right) =>
          new Date(left.start_time).getTime() - new Date(right.start_time).getTime()
      );
      const scores = orderedSessions.map((session) => session.overall_accuracy);
      const averageScore = scores.reduce((total, value) => total + value, 0) / scores.length;
      const bestScore = Math.max(...scores);
      const earliest = orderedSessions[0]?.overall_accuracy ?? 0;
      const latest = orderedSessions[orderedSessions.length - 1]?.overall_accuracy ?? 0;
      const delta = latest - earliest;
      const trendDirection: DashboardDrillComparison["trendDirection"] =
        orderedSessions.length < 2
          ? "insufficient"
          : delta > 0
            ? "up"
            : delta < 0
              ? "down"
              : "flat";
      const trendLabel =
        trendDirection === "insufficient"
          ? "Need more sessions"
          : trendDirection === "up"
            ? `Up ${delta.toFixed(0)} pts`
            : trendDirection === "down"
              ? `Down ${Math.abs(delta).toFixed(0)} pts`
              : "Holding steady";

      return {
        drillName,
        sportName: orderedSessions[0]?.sport_name ?? "",
        sessions: drillSessions.length,
        averageScore,
        bestScore,
        trendDirection,
        trendLabel,
        mainIssue: formatDashboardLabel(
          getModeLabel(drillSessions.map((session) => session.mainIssue))
        )
      };
    })
    .sort((left, right) => {
      if (right.sessions !== left.sessions) {
        return right.sessions - left.sessions;
      }

      return right.averageScore - left.averageScore;
    });
}

export function buildRecurringInsightSummary(
  sessions: DashboardAnalyzedSession[]
): DashboardRecurringInsight {
  const recurringConcept = formatDashboardLabel(
    getModeLabel(sessions.map((session) => session.primaryConcept))
  );
  const bodyRegion = formatDashboardLabel(
    getModeLabel(sessions.map((session) => session.bodyRegion))
  );
  const interactionPattern = formatDashboardLabel(
    getModeLabel(sessions.map((session) => session.interactionGroup))
  );
  const interactionSentence =
    sessions.find(
      (session) =>
        normalizeDashboardLabel(session.interactionGroup) ===
        normalizeDashboardLabel(interactionPattern)
    )?.interactionExplanation ??
    (interactionPattern
      ? `${interactionPattern} limitations tend to show up together across recent sessions.`
      : null);
  const temporalBehavior = formatDashboardLabel(
    getModeLabel(sessions.map((session) => session.temporalState))
  );
  const mostCommonIssue = formatDashboardLabel(
    getModeLabel(sessions.map((session) => session.mainIssue))
  );

  return {
    recurringConcept,
    recurringConceptSentence: recurringConcept
      ? `Your most recurring focus area is ${recurringConcept.toLowerCase()}.`
      : null,
    bodyRegion,
    bodyRegionSentence: bodyRegion
      ? `${bodyRegion} control keeps showing up as a repeated coaching target.`
      : null,
    interactionPattern,
    interactionSentence,
    temporalBehavior,
    temporalSentence: temporalBehavior
      ? buildTemporalSentence(temporalBehavior)
      : null,
    mostCommonIssue
  };
}

export function buildTrendSummary(sessions: DashboardAnalyzedSession[]) {
  if (sessions.length < 2) {
    return {
      value: "Need more sessions",
      direction: "insufficient" as const,
      delta: null
    };
  }

  const orderedSessions = [...sessions].sort(
    (left, right) =>
      new Date(left.start_time).getTime() - new Date(right.start_time).getTime()
  );
  const latestScore = orderedSessions[orderedSessions.length - 1]?.overall_accuracy ?? 0;
  const previousScore = orderedSessions[orderedSessions.length - 2]?.overall_accuracy ?? 0;
  const delta = latestScore - previousScore;

  if (delta > 0) {
    return {
      value: `Up ${delta.toFixed(0)} pts`,
      direction: "up" as const,
      delta
    };
  }

  if (delta < 0) {
    return {
      value: `Down ${Math.abs(delta).toFixed(0)} pts`,
      direction: "down" as const,
      delta
    };
  }

  return {
    value: "Holding steady",
    direction: "flat" as const,
    delta
  };
}

export function buildDashboardInsightSummary(
  sessions: DashboardAnalyzedSession[],
  recurringInsight: DashboardRecurringInsight
) {
  if (!sessions.length) {
    return "Complete more analyzed sessions to unlock a full coaching summary.";
  }

  const trend = buildTrendSummary(sessions);
  const latestSession = [...sessions].sort(
    (left, right) =>
      new Date(right.start_time).getTime() - new Date(left.start_time).getTime()
  )[0];

  const trendSentence =
    trend.direction === "up"
      ? "Your recent sessions show steady improvement."
      : trend.direction === "down"
        ? "Your recent sessions show a dip in performance that is worth correcting early."
        : trend.direction === "flat"
          ? "Your recent sessions are holding steady."
          : "You need more completed sessions to establish a clear trend.";
  const focusSentence = recurringInsight.mostCommonIssue
    ? `The main focus area is ${recurringInsight.mostCommonIssue.toLowerCase()}.`
    : recurringInsight.recurringConceptSentence;
  const behaviorSentence =
    recurringInsight.interactionSentence ?? recurringInsight.temporalSentence ?? null;
  const actionSentence = latestSession?.coachingAction
    ? latestSession.coachingAction
    : "Continue practicing controlled reps before increasing speed.";

  return [trendSentence, focusSentence, behaviorSentence, actionSentence]
    .filter(Boolean)
    .join(" ");
}

function buildTemporalSentence(temporalBehavior: string) {
  const normalizedTemporal = normalizeDashboardLabel(temporalBehavior);

  if (normalizedTemporal.includes("rushed")) {
    return "You often move too quickly during key phases of the rep.";
  }

  if (normalizedTemporal.includes("jerky")) {
    return "Your movement timing often becomes abrupt between positions.";
  }

  if (normalizedTemporal.includes("incomplete")) {
    return "Several reps finish before the movement fully settles.";
  }

  if (normalizedTemporal.includes("controlled")) {
    return "Your timing is generally controlled, which is a solid base to build on.";
  }

  if (normalizedTemporal.includes("stable")) {
    return "Your timing is generally stable across recent sessions.";
  }

  return "Timing remains one of the recurring themes in recent sessions.";
}

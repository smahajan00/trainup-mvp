import Link from "next/link";
import { ArrowDownRight, ArrowRight, ArrowUpRight, Minus } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "../../../components/ui/button";
import { Badge } from "../../../components/ui/badge";
import { getRecentProgress } from "../../../services/progress";
import type { RecentProgressResponse, RecentProgressSession } from "../../../types/progress";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { SectionTitle } from "../../app-shell/components/SectionTitle";
import { normalizeMetricName } from "./session-results-utils";

type MiniProgressPreviewProps = {
  currentSessionId: string;
  currentDrillName: string;
  currentScorePercent?: number | null;
  currentWeakestMetric?: string | null;
};

type TrendDirection = "up" | "down" | "flat";

function getPreviousSession(
  recentSessions: RecentProgressSession[],
  currentSessionId: string,
  currentDrillName: string
) {
  const sameDrillSession = recentSessions.find(
    (session) =>
      session.session_id !== currentSessionId &&
      session.drill_name === currentDrillName
  );

  if (sameDrillSession) {
    return sameDrillSession;
  }

  return recentSessions.find((session) => session.session_id !== currentSessionId) ?? null;
}

function getTrendDirection(currentScore: number, previousScore: number): TrendDirection {
  if (currentScore > previousScore) {
    return "up";
  }

  if (currentScore < previousScore) {
    return "down";
  }

  return "flat";
}

export function MiniProgressPreview({
  currentSessionId,
  currentDrillName,
  currentScorePercent,
  currentWeakestMetric
}: MiniProgressPreviewProps) {
  const [progress, setProgress] = useState<RecentProgressResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [progressError, setProgressError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    if (currentScorePercent === null || currentScorePercent === undefined) {
      return;
    }

    async function loadProgress() {
      setIsLoading(true);
      setProgressError(null);

      try {
        const result = await getRecentProgress(6, 20);
        if (!ignore) {
          setProgress(result);
        }
      } catch (error) {
        if (!ignore) {
          setProgressError(
            error instanceof Error
              ? error.message
              : "Progress preview is unavailable right now."
          );
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    loadProgress();

    return () => {
      ignore = true;
    };
  }, [currentScorePercent]);

  const previousSession = progress
    ? getPreviousSession(progress.recent_sessions, currentSessionId, currentDrillName)
    : null;
  const trendDirection =
    previousSession && currentScorePercent !== null && currentScorePercent !== undefined
      ? getTrendDirection(currentScorePercent, previousSession.overall_accuracy)
      : null;
  const recurringIssue =
    progress && currentWeakestMetric
      ? progress.recent_metrics.some(
          (metric) =>
            metric.session_id !== currentSessionId &&
            normalizeMetricName(metric.metric_name) ===
              normalizeMetricName(currentWeakestMetric)
        )
        ? currentWeakestMetric
        : null
      : null;

  return (
    <InfoCard>
      <SectionTitle
        eyebrow="Progress"
        title="Mini progress preview"
        description="A quick look at how this session compares with your recent work."
        action={
          <Button asChild variant="outline">
            <Link href="/progress">
              View Full Progress
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        }
      />

      {currentScorePercent === null || currentScorePercent === undefined ? (
        <p className="mt-6 text-sm leading-6 text-muted-gray">
          Complete analysis to unlock progress trends.
        </p>
      ) : isLoading ? (
        <p className="mt-6 text-sm leading-6 text-muted-gray">
          Checking recent progress...
        </p>
      ) : progressError ? (
        <p className="mt-6 text-sm leading-6 text-muted-gray">{progressError}</p>
      ) : !previousSession ? (
        <p className="mt-6 text-sm leading-6 text-muted-gray">
          Complete more sessions to unlock progress trends.
        </p>
      ) : (
        <>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Current score
              </p>
              <p className="mt-3 text-2xl font-bold text-white">
                {currentScorePercent.toFixed(0)}%
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Recent score
              </p>
              <p className="mt-3 text-2xl font-bold text-white">
                {previousSession.overall_accuracy.toFixed(0)}%
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Trend
              </p>
              <div className="mt-3 flex items-center gap-3">
                {trendDirection === "up" ? (
                  <ArrowUpRight className="h-5 w-5 text-emerald-200" />
                ) : trendDirection === "down" ? (
                  <ArrowDownRight className="h-5 w-5 text-rose-200" />
                ) : (
                  <Minus className="h-5 w-5 text-white/70" />
                )}
                <span className="text-sm font-semibold text-white">
                  {trendDirection === "up"
                    ? "Improving"
                    : trendDirection === "down"
                      ? "Needs attention"
                      : "Holding steady"}
                </span>
              </div>
            </div>
          </div>

          {recurringIssue ? (
            <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Recurring issue
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge variant="warning">{recurringIssue}</Badge>
              </div>
            </div>
          ) : null}
        </>
      )}
    </InfoCard>
  );
}

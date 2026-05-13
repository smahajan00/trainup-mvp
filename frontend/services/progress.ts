import { apiRequest } from "../lib/api";
import type { ProgressRange, RecentProgressResponse } from "../types/progress";

export function getRecentProgress(
  sessionLimit = 5,
  metricLimit = 20,
  range?: ProgressRange
) {
  const params = new URLSearchParams({
    session_limit: String(sessionLimit),
    metric_limit: String(metricLimit)
  });

  if (range) {
    params.set("range", range);
  }

  return apiRequest<RecentProgressResponse>(`/progress/recent?${params.toString()}`);
}

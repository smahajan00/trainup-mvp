import { apiRequest } from "../lib/api";
import type { RecentProgressResponse } from "../types/progress";

export function getRecentProgress(sessionLimit = 5, metricLimit = 20) {
  return apiRequest<RecentProgressResponse>(
    `/progress/recent?session_limit=${sessionLimit}&metric_limit=${metricLimit}`
  );
}

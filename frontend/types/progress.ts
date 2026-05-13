export type SessionInputType = "UPLOAD" | "LIVE";
export type SessionStatus = "ACTIVE" | "COMPLETED" | "ABORTED";
export type SeverityLevel = "MINOR" | "MODERATE" | "SEVERE";
export type ProgressRange = "weekly" | "monthly" | "all_time";

export type SummaryStrengthMetric = {
  name: string;
  score: number;
};

export type SessionStrengths = {
  metrics: SummaryStrengthMetric[];
};

export type SessionWeaknessIssue = {
  metric: string;
  severity: SeverityLevel;
  issue_label: string;
};

export type SessionWeaknesses = {
  issues: SessionWeaknessIssue[];
};

export type SessionRecommendations = {
  actions: string[];
};

export type SessionSummary = {
  id: string;
  session_id: string;
  summary_text: string;
  overall_accuracy: number;
  strengths: SessionStrengths;
  weaknesses: SessionWeaknesses;
  recommendations: SessionRecommendations;
  created_at: string;
};

export type RecentProgressSession = {
  session_id: string;
  drill_name: string;
  sport_name: string;
  input_type: SessionInputType;
  status: SessionStatus;
  start_time: string;
  overall_accuracy: number;
  summary_text: string;
};

export type RecentMetricProgress = {
  progress_id: string;
  summary_id: string;
  session_id: string;
  drill_name: string;
  sport_name: string;
  metric_name: string;
  metric_unit: string;
  metric_value: number;
  date_recorded: string;
  created_at: string;
};

export type RecentProgressResponse = {
  selected_range: ProgressRange;
  total_analyzed_sessions: number;
  average_score: number | null;
  best_score: number | null;
  trend_delta: number | null;
  trend_label: string | null;
  available_ranges: ProgressRange[];
  recent_sessions: RecentProgressSession[];
  recent_metrics: RecentMetricProgress[];
};

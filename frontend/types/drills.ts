export type DrillTargetMetrics = {
  metrics: string[];
};

export type DrillReferenceRange = {
  min?: number;
  max?: number;
};

export type DrillReferencePayload = {
  movement_type?: string;
  phases?: string[];
  tracked_joints?: string[];
  ideal_ranges?: Record<string, DrillReferenceRange>;
  stability_expectations?: Record<string, number | string>;
  notes?: string;
};

export type DrillRuleCheck = {
  metric: string;
  condition: string;
  expected_min?: number;
  expected_max?: number;
  severity_weight: number;
  issue_label: string;
  coaching_cue: string;
};

export type DrillCoachingRules = {
  primary_focus?: string[];
  thresholds?: Record<string, number>;
  rule_checks?: DrillRuleCheck[];
  positive_cues?: string[];
  recommendation_templates?: string[];
};

export type DrillListItem = {
  id: string;
  sport_id: string;
  drill_name: string;
  description: string | null;
  target_metrics: DrillTargetMetrics;
};

export type DrillDetail = {
  id: string;
  sport_id: string;
  sport_name: string;
  drill_name: string;
  description: string | null;
  target_metrics: DrillTargetMetrics;
  reference_payload: DrillReferencePayload;
  coaching_rules: DrillCoachingRules;
};

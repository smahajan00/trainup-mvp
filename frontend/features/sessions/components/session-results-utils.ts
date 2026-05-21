import { formatEnumLabel, formatTokenLabel } from "../../../lib/formatters";
import type { SkillLevel } from "../../../types/profile";
import type {
  IT2FuzzyInterpretationResult,
  PoseSequence,
  RankedMetric,
  SeverityLevel
} from "../../../types/sessions";

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

export function formatSeverityLabel(severity?: SeverityLevel | null) {
  if (severity === "SEVERE") {
    return "High Priority";
  }

  if (severity === "MODERATE") {
    return "Moderate Priority";
  }

  if (severity === "MINOR") {
    return "Minor Adjustment";
  }

  return "Priority";
}

export function formatScorePercent(score?: number | null) {
  if (score === null || score === undefined || Number.isNaN(score)) {
    return "Pending";
  }

  return `${Math.round(score * 100)}%`;
}

export function formatMetricLabel(metric?: string | null) {
  if (!metric) {
    return "Movement quality";
  }

  return formatTokenLabel(metric);
}

export function formatPhaseLabel(phase?: string | null) {
  if (!phase) {
    return "movement";
  }

  return formatTokenLabel(phase);
}

export function formatMetricSummary(metric?: RankedMetric | null) {
  if (!metric) {
    return null;
  }

  return `${formatMetricLabel(metric.metric_name)} during ${formatPhaseLabel(metric.phase_id)}`;
}

export function buildPoseQualitySummary(poseSequence?: PoseSequence | null) {
  if (!poseSequence) {
    return "Pose quality summary will appear after movement data is processed.";
  }

  const validRatio =
    poseSequence.frame_count > 0
      ? poseSequence.valid_frame_count / poseSequence.frame_count
      : 0;
  const qualityLead =
    validRatio >= 0.85
      ? "Pose quality looks strong."
      : validRatio >= 0.65
        ? "Pose quality is usable."
        : "Pose tracking quality was limited, so feedback may be less reliable.";
  const primaryFlag = poseSequence.diagnostic_flags[0];

  return `${qualityLead} ${poseSequence.valid_frame_count} of ${poseSequence.frame_count} frames were usable.${
    primaryFlag ? ` ${formatEnumLabel(primaryFlag)} was flagged during capture.` : ""
  }`;
}

export function getSkillFocusLimit(skillLevel: SkillLevel) {
  if (skillLevel === "ADVANCED") {
    return 3;
  }

  if (skillLevel === "INTERMEDIATE") {
    return 2;
  }

  return 1;
}

export function formatCorrectionIntensity(intensity?: string | null) {
  if (!intensity) {
    return "Balanced";
  }

  const map: Record<string, string> = {
    observe: "Observation-first",
    soft: "Light correction",
    corrective: "Direct correction",
    direct: "High focus correction"
  };

  return map[intensity] ?? formatEnumLabel(intensity);
}

export function formatTeachingStrategy(strategy?: string | null) {
  if (!strategy) {
    return "Skill-focused";
  }

  const map: Record<string, string> = {
    single_focus_mastery: "Single focus",
    dual_focus_refinement: "Dual refinement",
    multi_focus_precision: "Precision work"
  };

  return map[strategy] ?? formatEnumLabel(strategy);
}

export function formatToneProfile(tone?: string | null) {
  if (!tone) {
    return "Clear coaching";
  }

  const map: Record<string, string> = {
    supportive_simple: "Simple and supportive",
    corrective_specific: "Corrective and specific",
    technical_performance: "Technical performance"
  };

  return map[tone] ?? formatEnumLabel(tone);
}

export function formatTemporalStateLabel(state?: string | null) {
  if (!state) {
    return "Not available";
  }

  const map: Record<string, string> = {
    STABLE: "Stable",
    CONTROLLED: "Controlled",
    RUSHED: "Rushed",
    JERKY: "Jerky",
    INCOMPLETE: "Incomplete",
    UNCERTAIN: "Uncertain"
  };

  return map[state] ?? formatEnumLabel(state);
}

export function buildConfidenceLabel(
  it2Result?: IT2FuzzyInterpretationResult | null
) {
  if (!it2Result) {
    return "Not available";
  }

  if (it2Result.uncertainty_summary.high_count > 0) {
    return "Lower confidence";
  }

  if (it2Result.uncertainty_summary.medium_count > 0) {
    return "Moderate confidence";
  }

  return "High confidence";
}

export function normalizeMetricName(value?: string | null) {
  if (!value) {
    return "";
  }

  return value.toLowerCase().replace(/[_\s-]+/g, " ").trim();
}

const COACHING_STOP_WORDS = new Set([
  "a",
  "an",
  "and",
  "are",
  "as",
  "at",
  "before",
  "by",
  "during",
  "for",
  "from",
  "in",
  "into",
  "is",
  "it",
  "keep",
  "maintain",
  "next",
  "of",
  "on",
  "or",
  "set",
  "session",
  "the",
  "this",
  "through",
  "to",
  "try",
  "with",
  "your"
]);

export function normalizeCoachingText(value?: string | null) {
  if (!value) {
    return "";
  }

  return value
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\b(rep|reps|repetition|repetitions)\b/g, "rep")
    .replace(/\b(correct|correction|fix|improve|improving)\b/g, "improve")
    .replace(/\b(aligned|alignment|tracking|track)\b/g, "alignment")
    .replace(/\b(stable|stability|control|controlled)\b/g, "control")
    .replace(/\s+/g, " ")
    .trim();
}

export function professionalizeCoachingCopy(value?: string | null) {
  if (!value) {
    return "";
  }

  return value
    .replace(/\bnext\s+rep\b/gi, "next set")
    .replace(/\bnext\s+repetition\b/gi, "next set")
    .replace(/\bwhat\s+to\s+fix\b/gi, "corrective focus")
    .replace(/\bwhat\s+happened\b/gi, "movement observation")
    .replace(/\bwhy\s+it\s+matters\b/gi, "performance impact")
    .replace(/\bmain\s+coaching\s+cue\b/gi, "primary performance focus")
    .replace(/\s+/g, " ")
    .trim();
}

function coachingTokens(value?: string | null) {
  return normalizeCoachingText(value)
    .split(" ")
    .filter((token) => token.length > 2 && !COACHING_STOP_WORDS.has(token));
}

export function areCoachingTextsSimilar(
  first?: string | null,
  second?: string | null
) {
  const firstNormalized = normalizeCoachingText(first);
  const secondNormalized = normalizeCoachingText(second);

  if (!firstNormalized || !secondNormalized) {
    return false;
  }

  if (firstNormalized === secondNormalized) {
    return true;
  }

  if (
    firstNormalized.length > 18 &&
    secondNormalized.length > 18 &&
    (firstNormalized.includes(secondNormalized) ||
      secondNormalized.includes(firstNormalized))
  ) {
    return true;
  }

  const firstTokens = new Set(coachingTokens(firstNormalized));
  const secondTokens = new Set(coachingTokens(secondNormalized));

  if (firstTokens.size < 3 || secondTokens.size < 3) {
    return false;
  }

  const overlap = [...firstTokens].filter((token) => secondTokens.has(token)).length;
  const overlapRatio = overlap / Math.min(firstTokens.size, secondTokens.size);

  return overlap >= 3 && overlapRatio >= 0.68;
}

export function dedupeCoachingTexts(
  items: (string | null | undefined)[],
  existing: (string | null | undefined)[] = []
) {
  const accepted: string[] = [];

  items.forEach((item) => {
    const normalized = item?.replace(/\s+/g, " ").trim();

    if (!normalized) {
      return;
    }

    const duplicatesExisting = existing.some((existingItem) =>
      areCoachingTextsSimilar(normalized, existingItem)
    );
    const duplicatesAccepted = accepted.some((acceptedItem) =>
      areCoachingTextsSimilar(normalized, acceptedItem)
    );

    if (!duplicatesExisting && !duplicatesAccepted) {
      accepted.push(normalized);
    }
  });

  return accepted;
}

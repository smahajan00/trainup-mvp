import { AlertTriangle, Sparkles } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { SectionTitle } from "../../app-shell/components/SectionTitle";
import type { SkillLevel } from "../../../types/profile";
import type {
  AnalysisState,
  DeterministicFeedbackItem,
  DeterministicEvaluationIssue,
  FeedbackTTSSegments,
  IT2FuzzyMetricInterpretation,
  LLMEnhancedFeedbackItem,
  SessionAnalysisWarning,
  SessionArtifactsResponse,
  TrainingSession
} from "../../../types/sessions";
import { AdvancedInsightsPanel } from "./AdvancedInsightsPanel";
import { CoachingFeedbackCard } from "./CoachingFeedbackCard";
import { ImprovementPlanCard } from "./ImprovementPlanCard";
import { MiniProgressPreview } from "./MiniProgressPreview";
import { ResultsOverviewCard } from "./ResultsOverviewCard";
import {
  buildConfidenceLabel,
  buildPoseQualitySummary,
  formatCorrectionIntensity,
  formatMetricLabel,
  formatMetricSummary,
  formatPhaseLabel,
  formatScorePercent,
  formatTeachingStrategy,
  formatTemporalStateLabel,
  formatToneProfile,
  getSeverityVariant,
  getSkillFocusLimit
} from "./session-results-utils";

type SessionResultsPanelProps = {
  session: TrainingSession;
  artifacts: SessionArtifactsResponse | null;
  analysisState: AnalysisState;
  analysisError?: string | null;
  analysisWarnings?: SessionAnalysisWarning[];
  showAnalysisWarningBanner?: boolean;
};

function buildFallbackWhyText(
  issue: DeterministicEvaluationIssue | undefined,
  pedagogyReason?: string | null,
  choquetExplanation?: string | null,
  temporalSummary?: string | null,
  ontologySummary?: string | null,
  uncertaintyNote?: string | null
) {
  return (
    pedagogyReason ??
    choquetExplanation ??
    temporalSummary ??
    ontologySummary ??
    uncertaintyNote ??
    (issue
      ? `${formatMetricLabel(issue.metric_name)} became a priority because it affected ${issue.affected_body_part.toLowerCase()} control during ${formatPhaseLabel(issue.phase_id)}.`
      : "This area stood out as the clearest opportunity for better control.")
  );
}

function findMatchingLLMItem(
  feedbackItem: DeterministicFeedbackItem,
  llmItems: LLMEnhancedFeedbackItem[]
) {
  return (
    llmItems.find(
      (item) =>
        item.metric_name === feedbackItem.metric_name &&
        item.phase_id === feedbackItem.phase_id
    ) ??
    llmItems.find((item) => item.priority_rank === feedbackItem.priority_rank) ??
    null
  );
}

function findMatchingUncertainty(
  feedbackItem: DeterministicFeedbackItem,
  it2Metrics: IT2FuzzyMetricInterpretation[]
) {
  return (
    it2Metrics.find(
      (item) =>
        item.metric_name === feedbackItem.metric_name &&
        item.phase_id === feedbackItem.phase_id
    ) ?? null
  );
}

function buildFocusItems(
  skillLevel: SkillLevel,
  selectedFocusItems: string[],
  improvementSuggestions: string[]
) {
  const focusLimit = getSkillFocusLimit(skillLevel);
  const focusItems = selectedFocusItems.slice(0, focusLimit);

  if (focusItems.length) {
    return focusItems;
  }

  return improvementSuggestions.slice(0, focusLimit);
}

function buildFeedbackItemKey(feedbackItem: DeterministicFeedbackItem) {
  return `${feedbackItem.phase_id}:${feedbackItem.metric_name}:${feedbackItem.priority_rank}`;
}

function buildTTSSegments(
  feedbackItem: DeterministicFeedbackItem,
  whatToFix: string,
  nextAction: string,
  isEnhanced: boolean
): FeedbackTTSSegments {
  const finalCue = whatToFix || feedbackItem.what_to_fix || feedbackItem.coaching_cue;
  const finalNextCue =
    nextAction || feedbackItem.next_rep_cue || feedbackItem.improvement_suggestion;

  return {
    segment_1: isEnhanced
      ? finalCue
      : feedbackItem.simple_coaching_phrase ||
        feedbackItem.issue_title ||
        finalCue,
    segment_2: feedbackItem.what_to_fix || finalCue,
    segment_3: isEnhanced ? finalNextCue : feedbackItem.next_rep_cue || finalNextCue
  };
}

function cleanAdvancedDetail(value: string | null | undefined) {
  if (!value) {
    return null;
  }

  return value
    .replace(/\b[A-Z][A-Z0-9_:-]{3,}\b/g, (match) => formatMetricLabel(match.toLowerCase()))
    .replace(/\bchoquet\b/gi, "linked-issue")
    .replace(/\bontology\b/gi, "movement concept")
    .replace(/\bit2 fuzzy\b/gi, "confidence")
    .replace(/\bfuzzy\b/gi, "movement read")
    .replace(/\btemporal model(?:ing)?\b/gi, "timing")
    .replace(/\bdiagnostic flags?\b/gi, "analysis note")
    .replace(/\s+/g, " ")
    .trim();
}

export function SessionResultsPanel({
  session,
  artifacts,
  analysisState,
  analysisError,
  analysisWarnings = [],
  showAnalysisWarningBanner = true
}: SessionResultsPanelProps) {
  const evaluationResult = artifacts?.evaluation_result ?? null;
  const feedbackResult = artifacts?.feedback_result ?? null;
  const llmFeedbackResult = artifacts?.llm_feedback_result ?? null;
  const poseSequence = artifacts?.pose_sequence ?? null;
  const fuzzyResult = artifacts?.fuzzy_interpretation_result ?? null;
  const it2Result = artifacts?.it2_fuzzy_interpretation_result ?? null;
  const pedagogyResult = artifacts?.pedagogical_decision_result ?? null;
  const ontologyResult = artifacts?.ontology_reasoning_result ?? null;
  const choquetResult = artifacts?.choquet_aggregation_result ?? null;
  const temporalResult = artifacts?.temporal_modeling_result ?? null;
  const sessionSummary = artifacts?.session_summary ?? null;

  if (analysisState === "FAILED") {
    return (
      <InfoCard>
        <SectionTitle
          eyebrow="Results"
          title="Session Results"
          description="Analysis could not be completed because evaluation/feedback failed."
        />
        <div className="mt-6 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-4 text-sm leading-7 text-rose-100">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            <span>{analysisError ?? "Analysis failed. Try again."}</span>
          </div>
        </div>
      </InfoCard>
    );
  }

  const hasRenderableResults = Boolean(
    evaluationResult?.status === "COMPLETED" ||
      feedbackResult?.status === "COMPLETED" ||
      feedbackResult?.status === "NO_ACTIONABLE_ISSUES" ||
      llmFeedbackResult?.status === "COMPLETED" ||
      sessionSummary
  );

  if (!hasRenderableResults) {
    return (
      <InfoCard>
        <SectionTitle
          eyebrow="Results"
          title="Session Results"
          description={
            analysisState === "RUNNING"
              ? "Your session results will appear here as soon as analysis finishes."
              : "Analyze your session to unlock coaching cues."
          }
        />
        <div className="mt-6 flex min-h-[150px] flex-col items-center justify-center rounded-[1.5rem] border border-white/10 bg-[radial-gradient(circle_at_center,_rgba(255,122,0,0.08),_transparent_42%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.018))] px-6 py-7 text-center">
          <div className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-white/45">
            {analysisState === "RUNNING" ? "Processing" : "Locked"}
          </div>
          <p className="mt-4 max-w-xl text-sm leading-7 text-white/75">
            {analysisState === "RUNNING"
                ? "TrainUp is processing movement quality, coaching priorities, and advanced reasoning."
                : "Complete performance analysis to unlock coaching feedback and movement results."}
          </p>
        </div>
      </InfoCard>
    );
  }

  const strongestMetric = evaluationResult?.strongest_metrics[0] ?? null;
  const weakestMetric = evaluationResult?.weakest_metrics[0] ?? null;
  const leadIssue = evaluationResult?.detected_issues[0] ?? null;
  const strongestArea =
    formatMetricSummary(strongestMetric) ??
    sessionSummary?.strengths.metrics[0]?.name ??
    "No standout strength was captured yet.";
  const mainLimitation =
    formatMetricSummary(weakestMetric) ??
    sessionSummary?.weaknesses.issues[0]?.issue_label ??
    "No clear limitation was captured yet.";
  const poseQualitySummary = buildPoseQualitySummary(poseSequence);
  const currentScorePercent =
    evaluationResult?.overall_score !== undefined && evaluationResult?.overall_score !== null
      ? evaluationResult.overall_score * 100
      : sessionSummary?.overall_accuracy ?? null;
  const focusItemLabels = buildFocusItems(
    session.skill_level,
    (feedbackResult?.prioritized_feedback_items ?? []).map(
      (item) => item.simple_coaching_phrase || item.what_to_fix || item.coaching_cue
    ),
    feedbackResult?.improvement_suggestions ?? []
  );
  const llmItems = llmFeedbackResult?.enhanced_feedback_items ?? [];
  const feedbackItems = feedbackResult?.prioritized_feedback_items.slice(0, 3) ?? [];
  const coachingCards = feedbackItems.map((feedbackItem) => {
    const llmItem = findMatchingLLMItem(feedbackItem, llmItems);
    const uncertaintyItem = findMatchingUncertainty(
      feedbackItem,
      it2Result?.it2_metric_results ?? []
    );
    const uncertaintyNote =
      uncertaintyItem?.uncertainty_category === "HIGH_UNCERTAINTY"
        ? "This pattern appeared with lower confidence, so another clean rep can help confirm it."
        : null;

    const whatToFix =
      llmItem && !llmItem.fallback_used
        ? llmItem.llm_coaching_cue
        : feedbackItem.what_to_fix || feedbackItem.coaching_cue;
    const nextAction =
      llmItem && !llmItem.fallback_used
        ? llmItem.llm_improvement_suggestion
        : feedbackItem.next_rep_cue || feedbackItem.improvement_suggestion;

    return {
      key: `${feedbackItem.phase_id}-${feedbackItem.metric_name}-${feedbackItem.priority_rank}`,
      title: feedbackItem.issue_title || formatMetricLabel(feedbackItem.metric_name),
      severity: feedbackItem.severity_level,
      feedbackItemKey: buildFeedbackItemKey(feedbackItem),
      whatHappened:
        feedbackItem.what_happened ||
        feedbackItem.issue_title ||
        "This rep showed one movement pattern to clean up first.",
      whyItHappened:
        feedbackItem.why_it_matters ||
        buildFallbackWhyText(
          leadIssue ?? undefined,
          null,
          null,
          null,
          null,
          uncertaintyNote
        ),
      whatToFix,
      nextAction,
      simpleCue: feedbackItem.simple_coaching_phrase || null,
      isEnhanced: Boolean(llmItem && !llmItem.fallback_used),
      ttsSegments: buildTTSSegments(
        feedbackItem,
        whatToFix,
        nextAction,
        Boolean(llmItem && !llmItem.fallback_used)
      ),
      backupNote:
        llmItem && llmItem.llm_coaching_cue !== llmItem.deterministic_coaching_cue
          ? llmItem.deterministic_coaching_cue
          : null
    };
  });

  const advancedItems = [
    fuzzyResult
      ? {
          label: "Movement read",
          value: formatMetricLabel(fuzzyResult.fuzzy_summary.dominant_fuzzy_label),
          detail: fuzzyResult.fuzzy_summary.top_concern_areas.length
            ? `Main movement concerns: ${fuzzyResult.fuzzy_summary.top_concern_areas
                .map((item) => formatMetricLabel(item))
                .join(", ")}.`
            : null
        }
      : null,
    it2Result
      ? {
          label: "Confidence",
          value: buildConfidenceLabel(it2Result),
          detail: cleanAdvancedDetail(it2Result.uncertainty_summary.summary_text)
        }
      : null,
    pedagogyResult
      ? {
          label: "Coaching style",
          value: pedagogyResult.learning_objective,
          detail: `${formatTeachingStrategy(
            pedagogyResult.teaching_strategy
          )} with ${formatToneProfile(pedagogyResult.tone_profile)} delivery.`
        }
      : null,
    ontologyResult
      ? {
          label: "Movement concept",
          value: ontologyResult.primary_concept
            ? formatMetricLabel(ontologyResult.primary_concept)
            : "No dominant concept",
          detail: cleanAdvancedDetail(ontologyResult.reasoning_summary)
        }
      : null,
    choquetResult
      ? {
          label: "Linked issues",
          value: choquetResult.dominant_interaction_group
            ? formatMetricLabel(choquetResult.dominant_interaction_group)
            : "No linked issue",
          detail: cleanAdvancedDetail(
            (choquetResult.dominant_interaction_group
              ? choquetResult.concept_aggregation[choquetResult.dominant_interaction_group]
                  ?.explanation
              : null) ??
            "Linked movement issues did not isolate one dominant limitation."
          )
        }
      : null,
    temporalResult
      ? {
          label: "Timing pattern",
          value: formatTemporalStateLabel(temporalResult.overall_temporal_state),
          detail: cleanAdvancedDetail(temporalResult.temporal_summary)
        }
      : null
  ].filter((item): item is NonNullable<typeof item> => Boolean(item));

  return (
    <div className="space-y-8">
      {showAnalysisWarningBanner && analysisState === "COMPLETED_WITH_WARNINGS" ? (
        <div className="rounded-[1.5rem] border border-amber-400/30 bg-amber-500/10 px-5 py-4 text-sm leading-7 text-amber-100">
          <p>
            Some advanced insights could not be generated, but your core coaching feedback is ready.
          </p>
          {analysisWarnings.length ? (
            <ul className="mt-3 space-y-2">
              {analysisWarnings.map((warning) => (
                <li key={`${warning.step}-${warning.message}`}>
                  {warning.message}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <ResultsOverviewCard
        overallScore={formatScorePercent(evaluationResult?.overall_score ?? null)}
        severity={evaluationResult?.overall_severity ?? null}
        strongestArea={strongestArea}
        mainLimitation={mainLimitation}
        poseQualitySummary={poseQualitySummary}
        movementConcept={
          ontologyResult?.primary_concept
            ? formatMetricLabel(ontologyResult.primary_concept)
            : null
        }
      />

      <div className="space-y-5">
        <InfoCard>
          <SectionTitle
            eyebrow="Coaching"
            title="Coaching Feedback"
            description="Clear guidance on what happened, why it happened, what to fix, and what to do next."
          />

          {llmFeedbackResult?.status === "COMPLETED" &&
          !llmFeedbackResult.fallback_used ? null : (
            <div className="mt-4 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm leading-6 text-amber-100">
              Showing core rule-based coaching. Wording enhancement is unavailable right now.
            </div>
          )}

          {coachingCards.length ? (
            <div
              className={`mt-5 grid gap-5 ${
                coachingCards.length > 1 ? "2xl:grid-cols-2" : ""
              }`}
            >
              {coachingCards.map((card) => (
                <CoachingFeedbackCard
                  key={card.key}
                  sessionId={session.id}
                  feedbackItemKey={card.feedbackItemKey}
                  title={card.title}
                  severity={card.severity}
                  whatHappened={card.whatHappened}
                  whyItHappened={card.whyItHappened}
                  whatToFix={card.whatToFix}
                  nextAction={card.nextAction}
                  simpleCue={card.simpleCue}
                  isEnhanced={card.isEnhanced}
                  backupNote={card.backupNote}
                  ttsSegments={card.ttsSegments}
                />
              ))}
            </div>
          ) : feedbackResult?.status === "NO_ACTIONABLE_ISSUES" ? (
            <div className="mt-6 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-4 text-sm leading-7 text-emerald-100">
              This session did not surface a major corrective issue. Keep repeating the same movement quality cues.
            </div>
          ) : (
            <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 text-sm leading-7 text-white/80">
              Coaching feedback is still unavailable. Results overview is shown from the current evaluation data.
            </div>
          )}
        </InfoCard>
      </div>

      <ImprovementPlanCard
        focusItems={focusItemLabels}
        learningObjective={
          pedagogyResult?.learning_objective ??
          feedbackResult?.overall_feedback_summary ??
          null
        }
        progressionAdvice={pedagogyResult?.progression_advice ?? null}
        correctionIntensity={formatCorrectionIntensity(
          pedagogyResult?.correction_intensity ?? null
        )}
        improvementSuggestions={feedbackResult?.improvement_suggestions ?? []}
        skillLevelLabel={session.skill_level}
      />

      <MiniProgressPreview
        currentSessionId={session.id}
        currentDrillName={session.drill_name}
        currentScorePercent={currentScorePercent}
        currentWeakestMetric={
          weakestMetric?.metric_name ??
          sessionSummary?.weaknesses.issues[0]?.metric ??
          null
        }
      />

      <AdvancedInsightsPanel
        items={advancedItems}
        hasAnyAdvancedData={Boolean(
          fuzzyResult ||
            it2Result ||
            pedagogyResult ||
            ontologyResult ||
            choquetResult ||
            temporalResult
        )}
      />

      {pedagogyResult?.selected_focus_items.length ? (
        <div className="rounded-[1.5rem] border border-primary/15 bg-primary/10 px-5 py-4 text-sm leading-7 text-white/85">
          <div className="flex flex-wrap items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="font-semibold text-white">
              Coaching focus
            </span>
            <Badge variant={getSeverityVariant(leadIssue?.severity_level ?? null)}>
              {formatTeachingStrategy(pedagogyResult.teaching_strategy)}
            </Badge>
          </div>
          <p className="mt-3">
            {pedagogyResult.learning_objective}
          </p>
        </div>
      ) : null}
    </div>
  );
}

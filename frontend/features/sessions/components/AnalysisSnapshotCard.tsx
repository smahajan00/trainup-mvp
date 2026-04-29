import { Badge } from "../../../components/ui/badge";
import { formatEnumLabel } from "../../../lib/formatters";
import type { SessionArtifactsResponse, SeverityLevel } from "../../../types/sessions";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { SectionTitle } from "../../app-shell/components/SectionTitle";

function getSeverityVariant(severity: SeverityLevel) {
  if (severity === "SEVERE") {
    return "danger" as const;
  }

  if (severity === "MODERATE") {
    return "warning" as const;
  }

  return "slate" as const;
}

export function AnalysisSnapshotCard({
  artifacts
}: {
  artifacts: SessionArtifactsResponse | null;
}) {
  const evaluationResult = artifacts?.evaluation_result ?? null;
  const feedbackResult = artifacts?.feedback_result ?? null;
  const llmFeedbackResult = artifacts?.llm_feedback_result ?? null;
  const sessionSummary = artifacts?.session_summary ?? null;

  if (!evaluationResult && !feedbackResult && !llmFeedbackResult && !sessionSummary) {
    return null;
  }

  const summaryText =
    llmFeedbackResult?.enhanced_summary.llm_summary ??
    feedbackResult?.overall_feedback_summary ??
    sessionSummary?.summary_text ??
    null;

  return (
    <InfoCard>
      <SectionTitle
        eyebrow="Latest"
        title="Latest analysis snapshot"
        description="A quick summary while the detailed results UI is still being built."
      />

      <div className="mt-6 flex flex-wrap gap-2">
        {evaluationResult ? (
          <Badge variant={getSeverityVariant(evaluationResult.overall_severity)}>
            {formatEnumLabel(evaluationResult.overall_severity)}
          </Badge>
        ) : null}
        {feedbackResult ? (
          <Badge variant="slate">{formatEnumLabel(feedbackResult.status)}</Badge>
        ) : null}
        {llmFeedbackResult ? (
          <Badge variant={llmFeedbackResult.fallback_used ? "warning" : "success"}>
            {llmFeedbackResult.fallback_used ? "Fallback summary" : "Enhanced summary"}
          </Badge>
        ) : null}
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
            Overall score
          </p>
          <p className="mt-3 text-2xl font-bold text-white">
            {evaluationResult
              ? `${Math.round(evaluationResult.overall_score * 100)}%`
              : "Pending"}
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
            Issues found
          </p>
          <p className="mt-3 text-2xl font-bold text-white">
            {evaluationResult?.detected_issues.length ?? 0}
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
            Feedback
          </p>
          <p className="mt-3 text-sm font-semibold text-white">
            {llmFeedbackResult
              ? "Ready"
              : feedbackResult
                ? "Ready"
                : "Pending"}
          </p>
        </div>
      </div>

      {summaryText ? (
        <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
            Summary
          </p>
          <p className="mt-3 text-sm leading-7 text-white/85">{summaryText}</p>
        </div>
      ) : null}
    </InfoCard>
  );
}

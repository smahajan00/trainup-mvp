"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  BrainCircuit,
  FileCheck2,
  Gauge,
  ScanSearch,
  Target,
  UploadCloud
} from "lucide-react";

import { Badge } from "../../../../components/ui/badge";
import { Button } from "../../../../components/ui/button";
import { CTAButton } from "../../../../components/ui/cta-button";
import { SkeletonLoader } from "../../../../components/ui/skeleton-loader";
import { AppShell } from "../../../../features/app-shell/components/AppShell";
import { EmptyState } from "../../../../features/app-shell/components/EmptyState";
import { InfoCard } from "../../../../features/app-shell/components/InfoCard";
import { SectionTitle } from "../../../../features/app-shell/components/SectionTitle";
import { SessionStatusBadge } from "../../../../features/sessions/components/SessionStatusBadge";
import { formatDateTime, formatEnumLabel, formatFileSize } from "../../../../lib/formatters";
import { validateVideoFile } from "../../../../lib/session-validation";
import {
  getSession,
  getSessionArtifacts,
  submitSessionUpload
} from "../../../../services/sessions";
import type {
  SessionArtifactsResponse,
  SessionFeedback,
  SeverityLevel,
  TrainingSession,
  UploadProcessingResponse
} from "../../../../types/sessions";

function ProcessingStep({
  title,
  description,
  complete,
  icon: Icon
}: {
  title: string;
  description: string;
  complete: boolean;
  icon: typeof UploadCloud;
}) {
  return (
    <div
      className={`rounded-2xl border p-4 transition-all duration-300 ${
        complete
          ? "border-emerald-400/25 bg-emerald-500/10"
          : "border-white/10 bg-white/[0.04]"
      }`}
    >
      <div className="flex items-center justify-between gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] text-white">
          <Icon className="h-5 w-5" />
        </div>
        <Badge variant={complete ? "success" : "slate"}>
          {complete ? "Complete" : "Pending"}
        </Badge>
      </div>
      <h3 className="mt-5 text-base font-semibold text-white">{title}</h3>
      <p className="mt-3 text-sm leading-7 text-muted-gray">{description}</p>
    </div>
  );
}

function getSeverityVariant(severity: SeverityLevel) {
  if (severity === "SEVERE") {
    return "danger" as const;
  }

  if (severity === "MODERATE") {
    return "warning" as const;
  }

  return "slate" as const;
}

function UploadSessionContent({ sessionId }: { sessionId: string }) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [session, setSession] = useState<TrainingSession | null>(null);
  const [artifactSnapshot, setArtifactSnapshot] =
    useState<SessionArtifactsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [localErrors, setLocalErrors] = useState<string[]>([]);
  const [localWarnings, setLocalWarnings] = useState<string[]>([]);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadProcessingResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDragActive, setIsDragActive] = useState(false);

  useEffect(() => {
    let ignore = false;

    async function loadSession() {
      setLoadError(null);

      try {
        const [sessionDetail, artifactsDetail] = await Promise.all([
          getSession(sessionId),
          getSessionArtifacts(sessionId)
        ]);
        if (!ignore) {
          setSession(sessionDetail);
          setArtifactSnapshot(artifactsDetail);
        }
      } catch (error) {
        if (!ignore) {
          setLoadError(
            error instanceof Error
              ? error.message
              : "Unable to load the upload session."
          );
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    loadSession();

    return () => {
      ignore = true;
    };
  }, [sessionId]);

  const displayWarnings = [
    ...localWarnings,
    ...(uploadResult?.validation.warnings ?? [])
  ];
  const displayErrors = [...localErrors, ...(uploadResult?.validation.errors ?? [])];
  const perceptionResult =
    uploadResult?.perception_result ?? artifactSnapshot?.perception_result ?? null;
  const cognitionResult =
    uploadResult?.cognition_result ?? artifactSnapshot?.cognition_result ?? null;
  const evaluationResult =
    uploadResult?.evaluation_result ?? artifactSnapshot?.evaluation_result ?? null;
  const sessionSummary =
    uploadResult?.session_summary ?? artifactSnapshot?.session_summary ?? null;
  const feedbackItems: SessionFeedback[] =
    uploadResult?.feedback ?? artifactSnapshot?.feedback ?? [];
  const artifactsPersisted =
    uploadResult?.artifacts_persisted.length ??
    artifactSnapshot?.artifacts.length ??
    0;
  const uploadAccepted =
    uploadResult?.upload_received ??
    Boolean(perceptionResult || cognitionResult || evaluationResult);
  const validationComplete =
    uploadResult?.validation.is_valid ??
    Boolean(perceptionResult || cognitionResult || evaluationResult);
  const keypointPreview = perceptionResult?.keypoint_series.slice(0, 3) ?? [];
  const cognitionMetricEntries = cognitionResult
    ? Object.entries(cognitionResult.derived_metrics)
    : [];
  const evaluationMetricEntries = evaluationResult
    ? Object.entries(evaluationResult.metric_scores)
    : [];
  const motionFeatureEntries = perceptionResult
    ? Object.entries(perceptionResult.derived_motion_features)
    : [];

  function handleSelectedFile(file: File | null) {
    setSelectedFile(file);
    setUploadResult(null);
    setSubmitError(null);

    if (!file) {
      setLocalErrors([]);
      setLocalWarnings([]);
      return;
    }

    const validation = validateVideoFile(file);
    setLocalErrors(validation.errors);
    setLocalWarnings(validation.warnings);
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    handleSelectedFile(event.target.files?.[0] ?? null);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragActive(false);
    handleSelectedFile(event.dataTransfer.files?.[0] ?? null);
  }

  async function handleUpload() {
    if (!selectedFile) {
      setSubmitError("Select a video file before submitting.");
      return;
    }

    const validation = validateVideoFile(selectedFile);
    setLocalErrors(validation.errors);
    setLocalWarnings(validation.warnings);
    setSubmitError(null);
    setUploadResult(null);

    if (!validation.isValid) {
      return;
    }

    try {
      setIsSubmitting(true);
      const result = await submitSessionUpload(sessionId, selectedFile);
      setUploadResult(result);
      const artifactsDetail = await getSessionArtifacts(sessionId);
      setArtifactSnapshot(artifactsDetail);
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "Unable to submit this video."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader className="h-64" />
        <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
          <SkeletonLoader className="h-[440px]" />
          <SkeletonLoader className="h-[440px]" />
        </div>
        <div className="grid gap-5 xl:grid-cols-4">
          <SkeletonLoader className="h-40" />
          <SkeletonLoader className="h-40" />
          <SkeletonLoader className="h-40" />
          <SkeletonLoader className="h-40" />
        </div>
      </div>
    );
  }

  if (loadError || !session) {
    return (
      <EmptyState
        icon={UploadCloud}
        title="Upload session unavailable"
        description={loadError ?? "We couldn't load this upload session."}
        action={
          <CTAButton asChild>
            <Link href="/sports">Back to Sports</Link>
          </CTAButton>
        }
      />
    );
  }

  if (session.input_type !== "UPLOAD") {
    return (
      <EmptyState
        icon={UploadCloud}
        title="This session is not in upload mode"
        description="Open the matching live session page or create a dedicated upload session from the drill detail screen."
        action={
          <CTAButton asChild>
            <Link href={`/drills/${session.drill_id}`}>Back to Drill</Link>
          </CTAButton>
        }
      />
    );
  }

  return (
    <div className="space-y-8">
      <InfoCard className="relative overflow-hidden border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.16),_transparent_35%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))]">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap gap-2">
              <Badge variant="accent">{session.sport_name}</Badge>
              <Badge variant="slate">{formatEnumLabel(session.input_type)}</Badge>
              <SessionStatusBadge status={session.status} />
            </div>
            <h2 className="mt-5 font-display text-4xl font-bold text-white sm:text-5xl">
              {session.drill_name}
            </h2>
            <p className="mt-4 text-sm leading-7 text-muted-gray sm:text-base">
              Validate a recorded drill clip and run it through TrainUp&apos;s
              first deterministic upload pipeline. This phase generates a
              scaffold perception payload, payload-quality diagnostics, and a
              drill-aware rule evaluation without pretending full pose
              intelligence exists yet.
            </p>
          </div>

          <div className="grid gap-3 xl:min-w-[280px]">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Session Started
              </p>
              <p className="mt-3 text-sm font-semibold text-white">
                {formatDateTime(session.start_time)}
              </p>
            </div>
            <Button
              asChild
              variant="outline"
              className="justify-between rounded-2xl px-5 py-6 text-white/90"
            >
              <Link href={`/drills/${session.drill_id}`}>
                <span className="flex items-center gap-2">
                  <ArrowLeft className="h-4 w-4" />
                  Back to Drill
                </span>
              </Link>
            </Button>
          </div>
        </div>
      </InfoCard>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <InfoCard className="relative overflow-hidden">
          <SectionTitle
            eyebrow="Upload Capture"
            title="Submit a drill video into the scaffolded pipeline"
            description="Accepted formats: MP4, MOV, WEBM, and MKV. Raw media is validated but not permanently stored in this phase."
          />

          <div
            onDragOver={(event) => {
              event.preventDefault();
              setIsDragActive(true);
            }}
            onDragLeave={() => setIsDragActive(false)}
            onDrop={handleDrop}
            className={`mt-6 rounded-[1.75rem] border border-dashed px-6 py-10 text-center transition-all duration-300 ${
              isDragActive
                ? "border-primary/45 bg-primary/10"
                : "border-white/12 bg-white/[0.03]"
            }`}
          >
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl border border-primary/20 bg-primary/10 text-primary">
              <UploadCloud className="h-7 w-7" />
            </div>
            <h3 className="mt-5 font-display text-2xl font-bold text-white">
              Drag a video here or browse locally
            </h3>
            <p className="mt-3 text-sm leading-7 text-muted-gray">
              Keep the full movement visible, maintain a stable camera angle,
              and prefer landscape framing for drill review.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <CTAButton type="button" onClick={() => inputRef.current?.click()}>
                Choose Video
              </CTAButton>
              <Button
                type="button"
                variant="outline"
                className="rounded-xl"
                onClick={() => handleSelectedFile(null)}
              >
                Clear Selection
              </Button>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept="video/mp4,video/quicktime,video/webm,video/x-matroska"
              className="hidden"
              onChange={handleInputChange}
            />
            {selectedFile ? (
              <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 text-left">
                <p className="text-sm font-semibold text-white">{selectedFile.name}</p>
                <p className="mt-2 text-sm text-muted-gray">
                  {selectedFile.type || "Unknown type"} · {formatFileSize(selectedFile.size)}
                </p>
              </div>
            ) : null}
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <Button
              type="button"
              onClick={handleUpload}
              className="rounded-2xl px-6"
              disabled={!selectedFile || isSubmitting}
            >
              {isSubmitting ? "Processing Upload" : "Submit Video"}
            </Button>
            <Badge variant="slate">100 MB max</Badge>
            <Badge variant="slate">Scaffold processing only</Badge>
          </div>
        </InfoCard>

        <div className="space-y-5">
          <InfoCard>
            <SectionTitle
              eyebrow="Validation"
              title="Session-side upload checks"
              description="This is where TrainUp confirms the media is suitable for the next Perception-layer stage."
            />

            {submitError ? (
              <div className="mt-6 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-4 text-sm leading-7 text-rose-100">
                {submitError}
              </div>
            ) : null}

            {displayErrors.length ? (
              <div className="mt-6 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-rose-200">
                  Errors
                </p>
                <ul className="mt-3 space-y-2 text-sm leading-7 text-rose-100">
                  {displayErrors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {displayWarnings.length ? (
              <div className="mt-4 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-amber-200">
                  Warnings
                </p>
                <ul className="mt-3 space-y-2 text-sm leading-7 text-amber-100">
                  {displayWarnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {uploadResult ? (
              <div className="mt-6 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-4">
                <div className="flex items-center gap-3">
                  <FileCheck2 className="h-5 w-5 text-emerald-200" />
                  <p className="text-sm font-semibold text-white">
                    {uploadResult.upload_received
                      ? "Processing scaffold complete"
                      : "Video received but not cleared for the next stage"}
                  </p>
                </div>
              <p className="mt-3 text-sm leading-7 text-emerald-50">
                  {uploadResult.next_step}
              </p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm text-white/85">
                    <span className="block text-xs uppercase tracking-[0.2em] text-white/50">
                      Content Type
                    </span>
                    <span className="mt-2 block">
                      {uploadResult.validation.content_type ?? "Unknown"}
                    </span>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm text-white/85">
                    <span className="block text-xs uppercase tracking-[0.2em] text-white/50">
                      File Size
                    </span>
                    <span className="mt-2 block">
                      {formatFileSize(uploadResult.validation.file_size_bytes)}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="mt-6 text-sm leading-7 text-muted-gray">
                Once a valid video is submitted, this panel will show the
                generated perception payload, cognition scaffold metrics, and
                deterministic drill-aware evaluation results. TrainUp is still
                explicit about what is scaffold-derived versus final analysis.
              </p>
            )}
          </InfoCard>

          <InfoCard>
            <SectionTitle
              eyebrow="Capture Guidance"
              title="Record with later analysis in mind"
              description="These are practical prep notes for the upcoming perception stage."
            />
            <ul className="mt-6 space-y-3 text-sm leading-7 text-white/85">
              <li>Keep the athlete and the full drill motion inside the frame.</li>
              <li>Use a stable camera angle and avoid rapid zooming or panning.</li>
              <li>Prefer clear side or front angles that expose the key joints.</li>
              <li>Good lighting and uncluttered backgrounds improve the next stage.</li>
            </ul>
          </InfoCard>
        </div>
      </div>

      <div className="space-y-5">
        <SectionTitle
          eyebrow="Pipeline Progress"
          title="TrainUp upload processing stages"
          description="These stages reflect real backend processing steps. The current phase produces scaffolded movement data, deterministic diagnostics, and seeded rule evaluation, not final AI coaching."
        />
        <div className="grid gap-5 xl:grid-cols-5">
          <ProcessingStep
            title="Upload accepted"
            description="The media reached the authenticated session pipeline."
            complete={uploadAccepted}
            icon={UploadCloud}
          />
          <ProcessingStep
            title="Validation complete"
            description="Metadata and supported-format checks passed."
            complete={validationComplete}
            icon={FileCheck2}
          />
          <ProcessingStep
            title="Perception payload generated"
            description="A structured movement payload scaffold was built and persisted."
            complete={Boolean(perceptionResult)}
            icon={ScanSearch}
          />
          <ProcessingStep
            title="Cognition scaffold complete"
            description="Deterministic readiness and diagnostic metrics are available."
            complete={Boolean(cognitionResult)}
            icon={BrainCircuit}
          />
          <ProcessingStep
            title="Drill evaluation ready"
            description="Seeded coaching rules were applied to drill-specific metric scores."
            complete={Boolean(evaluationResult)}
            icon={Target}
          />
        </div>
      </div>

      {perceptionResult ? (
        <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
          <InfoCard>
            <SectionTitle
              eyebrow="Perception Result"
              title="Initial movement payload generated"
              description="This payload is scaffold-generated from the uploaded file and session context. It is intentionally labeled as scaffold mode."
            />

            <div className="mt-6 flex flex-wrap gap-2">
              <Badge variant="accent">{perceptionResult.source_type}</Badge>
              <Badge variant="slate">
                {perceptionResult.processing_summary.processing_mode}
              </Badge>
              <Badge variant="slate">{artifactsPersisted} artifacts persisted</Badge>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                  Frame Count
                </p>
                <p className="mt-3 text-2xl font-bold text-white">
                  {perceptionResult.processing_summary.frame_count}
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                  Duration
                </p>
                <p className="mt-3 text-2xl font-bold text-white">
                  {perceptionResult.processing_summary.duration_seconds.toFixed(2)}s
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                  FPS Estimate
                </p>
                <p className="mt-3 text-2xl font-bold text-white">
                  {perceptionResult.processing_summary.fps_estimate.toFixed(1)}
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                  File Size
                </p>
                <p className="mt-3 text-2xl font-bold text-white">
                  {formatFileSize(perceptionResult.file_metadata.file_size_bytes)}
                </p>
              </div>
            </div>

            <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                File Metadata
              </p>
              <p className="mt-3 text-sm font-semibold text-white">
                {perceptionResult.file_metadata.file_name}
              </p>
              <p className="mt-2 text-sm text-muted-gray">
                {perceptionResult.file_metadata.content_type}
              </p>
            </div>

            <div className="mt-6">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Sampled keypoint frames
              </p>
              <div className="mt-4 space-y-3">
                {keypointPreview.map((frame) => (
                  <div
                    key={`${frame.frame_index}-${frame.timestamp}`}
                    className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-white">
                        Frame {frame.frame_index}
                      </p>
                      <Badge variant="slate">
                        confidence {frame.confidence.toFixed(2)}
                      </Badge>
                    </div>
                    <p className="mt-2 text-sm text-muted-gray">
                      Timestamp {frame.timestamp.toFixed(3)}s ·{" "}
                      {Object.keys(frame.keypoints).length} keypoints
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </InfoCard>

          <div className="space-y-5">
            <InfoCard>
              <SectionTitle
                eyebrow="Motion Features"
                title="Foundational motion descriptors"
                description="These are scaffold-level motion descriptors derived from the generated payload."
              />
              <div className="mt-6 grid gap-3">
                {motionFeatureEntries.map(([key, value]) => (
                  <div
                    key={key}
                    className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4"
                  >
                    <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                      {formatEnumLabel(key)}
                    </p>
                    <p className="mt-3 text-lg font-semibold text-white">
                      {typeof value === "number" ? value.toFixed(3) : String(value)}
                    </p>
                  </div>
                ))}
              </div>
            </InfoCard>

            {cognitionResult ? (
              <InfoCard>
                <SectionTitle
                  eyebrow="Cognition Result"
                  title="Foundational diagnostic metrics available"
                  description="These metrics are deterministic and honest. They describe payload quality and readiness, not final drill correctness."
                />

                <div className="mt-6 flex flex-wrap gap-2">
                  <Badge variant="accent">{cognitionResult.analysis_mode}</Badge>
                  <Badge
                    variant={
                      cognitionResult.processing_readiness.payload_usable
                        ? "success"
                        : "warning"
                    }
                  >
                    {cognitionResult.processing_readiness.payload_usable
                      ? "Payload usable"
                      : "Payload limited"}
                  </Badge>
                  <Badge
                    variant={
                      cognitionResult.processing_readiness.minimum_frames_met
                        ? "success"
                        : "warning"
                    }
                  >
                    {cognitionResult.processing_readiness.minimum_frames_met
                      ? "Minimum frames met"
                      : "Short clip"}
                  </Badge>
                </div>

                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  {cognitionMetricEntries.map(([key, value]) => (
                    <div
                      key={key}
                      className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4"
                    >
                      <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                        {formatEnumLabel(key)}
                      </p>
                      <p className="mt-3 text-2xl font-bold text-white">
                        {(value * 100).toFixed(0)}%
                      </p>
                    </div>
                  ))}
                </div>

                <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Diagnostic Flags
                  </p>
                  <ul className="mt-3 space-y-2 text-sm leading-7 text-white/85">
                    {cognitionResult.diagnostic_flags.map((flag) => (
                      <li key={flag}>{flag}</li>
                    ))}
                  </ul>
                </div>
              </InfoCard>
            ) : null}

            {evaluationResult ? (
              <InfoCard>
                <SectionTitle
                  eyebrow="Deterministic Evaluation"
                  title="Drill-aware rule evaluation complete"
                  description="These outputs are generated from the current scaffold payload and the seeded drill rule set. They are deterministic, explainable, and intentionally labeled as non-LLM evaluation."
                />

                <div className="mt-6 flex flex-wrap gap-2">
                  <Badge variant="accent">{evaluationResult.evaluation_mode}</Badge>
                  <Badge variant="slate">{evaluationResult.evaluator_name}</Badge>
                  <Badge
                    variant={
                      evaluationResult.feedback_count > 0 ? "warning" : "success"
                    }
                  >
                    {evaluationResult.feedback_count} issue
                    {evaluationResult.feedback_count === 1 ? "" : "s"}
                  </Badge>
                </div>

                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  {evaluationMetricEntries.map(([key, value]) => (
                    <div
                      key={key}
                      className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                          {formatEnumLabel(key)}
                        </p>
                        <p className="text-sm font-semibold text-white">
                          {(value * 100).toFixed(0)}%
                        </p>
                      </div>
                      <div className="mt-4 h-2 rounded-full bg-white/10">
                        <div
                          className="h-2 rounded-full bg-primary transition-all duration-500"
                          style={{ width: `${Math.max(value * 100, 8)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Evaluation Notes
                  </p>
                  <ul className="mt-3 space-y-2 text-sm leading-7 text-white/85">
                    {evaluationResult.summary_flags.map((flag) => (
                      <li key={flag}>{flag}</li>
                    ))}
                  </ul>
                </div>

                <div className="mt-6">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="h-5 w-5 text-primary" />
                    <p className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-gray">
                      Detected Technique Issues
                    </p>
                  </div>

                  {evaluationResult.issues.length ? (
                    <div className="mt-4 space-y-3">
                      {evaluationResult.issues.map((issue) => (
                        <div
                          key={`${issue.metric}-${issue.issue_label}`}
                          className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4"
                        >
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <p className="text-sm font-semibold text-white">
                                {issue.issue_label}
                              </p>
                              <p className="mt-2 text-sm leading-7 text-muted-gray">
                                {formatEnumLabel(issue.metric)} scored{" "}
                                {(issue.actual_score * 100).toFixed(0)}%
                                {issue.expected_min !== null &&
                                issue.expected_min !== undefined
                                  ? ` against a minimum of ${(issue.expected_min * 100).toFixed(0)}%.`
                                  : "."}
                              </p>
                            </div>
                            <Badge variant={getSeverityVariant(issue.severity_level)}>
                              {formatEnumLabel(issue.severity_level)}
                            </Badge>
                          </div>
                          <p className="mt-4 text-sm leading-7 text-white/85">
                            {issue.coaching_cue}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-4 text-sm leading-7 text-muted-gray">
                      No seeded coaching rule thresholds were triggered in this
                      evaluation pass.
                    </p>
                  )}
                </div>

                {feedbackItems.length ? (
                  <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
                    <div className="flex items-center gap-3">
                      <Gauge className="h-5 w-5 text-primary" />
                      <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                        Coaching Cues
                      </p>
                    </div>
                    <div className="mt-4 space-y-3">
                      {feedbackItems.map((item) => (
                        <div
                          key={item.id}
                          className="rounded-2xl border border-white/10 bg-background-dark/60 px-4 py-4"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <p className="text-sm font-semibold text-white">
                              {item.technique_issue}
                            </p>
                            <Badge variant={getSeverityVariant(item.severity_level)}>
                              {formatEnumLabel(item.severity_level)}
                            </Badge>
                          </div>
                          <p className="mt-3 text-sm leading-7 text-white/85">
                            {item.coaching_cue}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </InfoCard>
            ) : null}

            {sessionSummary ? (
              <InfoCard>
                <SectionTitle
                  eyebrow="Session Summary"
                  title="Deterministic session recap"
                  description="This summary is derived from the stored drill evaluation and feedback records. It reflects the current rule-based pipeline and avoids invented AI interpretation."
                />

                <div className="mt-6 grid gap-4 sm:grid-cols-[0.8fr_1.2fr]">
                  <div className="rounded-3xl border border-emerald-400/25 bg-emerald-500/10 p-5">
                    <p className="text-xs uppercase tracking-[0.22em] text-emerald-200">
                      Overall Accuracy
                    </p>
                    <p className="mt-4 font-display text-5xl font-bold text-white">
                      {sessionSummary.overall_accuracy.toFixed(1)}%
                    </p>
                    <p className="mt-3 text-sm leading-7 text-emerald-50/90">
                      Calculated as the average of the current drill-aware
                      metric scores.
                    </p>
                  </div>

                  <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
                    <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                      Summary Text
                    </p>
                    <p className="mt-4 text-sm leading-7 text-white/90">
                      {sessionSummary.summary_text}
                    </p>
                  </div>
                </div>

                <div className="mt-6 grid gap-5 lg:grid-cols-3">
                  <div className="rounded-3xl border border-emerald-400/25 bg-emerald-500/10 p-5">
                    <p className="text-xs uppercase tracking-[0.22em] text-emerald-200">
                      Strengths
                    </p>
                    {sessionSummary.strengths.metrics.length ? (
                      <div className="mt-4 space-y-3">
                        {sessionSummary.strengths.metrics.map((metric) => (
                          <div
                            key={metric.name}
                            className="rounded-2xl border border-white/10 bg-background-dark/50 px-4 py-4"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <p className="text-sm font-semibold text-white">
                                {formatEnumLabel(metric.name)}
                              </p>
                              <Badge variant="success">
                                {(metric.score * 100).toFixed(0)}%
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-4 text-sm leading-7 text-emerald-50/90">
                        No metrics crossed the current high-confidence strength
                        band in this pass.
                      </p>
                    )}
                  </div>

                  <div className="rounded-3xl border border-amber-400/25 bg-amber-500/10 p-5">
                    <p className="text-xs uppercase tracking-[0.22em] text-amber-200">
                      Weaknesses
                    </p>
                    {sessionSummary.weaknesses.issues.length ? (
                      <div className="mt-4 space-y-3">
                        {sessionSummary.weaknesses.issues.map((issue) => (
                          <div
                            key={`${issue.metric}-${issue.issue_label}`}
                            className="rounded-2xl border border-white/10 bg-background-dark/50 px-4 py-4"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <p className="text-sm font-semibold text-white">
                                {issue.issue_label}
                              </p>
                              <Badge variant={getSeverityVariant(issue.severity)}>
                                {formatEnumLabel(issue.severity)}
                              </Badge>
                            </div>
                            <p className="mt-3 text-sm text-white/80">
                              {formatEnumLabel(issue.metric)}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-4 text-sm leading-7 text-amber-50/90">
                        No seeded issue thresholds were triggered in this
                        session.
                      </p>
                    )}
                  </div>

                  <div className="rounded-3xl border border-primary/20 bg-primary/10 p-5">
                    <p className="text-xs uppercase tracking-[0.22em] text-primary">
                      Recommendations
                    </p>
                    {sessionSummary.recommendations.actions.length ? (
                      <div className="mt-4 space-y-3">
                        {sessionSummary.recommendations.actions.map((action) => (
                          <div
                            key={action}
                            className="rounded-2xl border border-white/10 bg-background-dark/50 px-4 py-4"
                          >
                            <p className="text-sm leading-7 text-white/90">{action}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-4 text-sm leading-7 text-white/85">
                        No extra corrective actions were needed for this
                        evaluation pass.
                      </p>
                    )}
                  </div>
                </div>
              </InfoCard>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function UploadSessionPage() {
  const params = useParams<{ sessionId: string }>();

  return (
    <AppShell
      eyebrow="Upload Session"
      title="Recorded video intake"
      description="Validate a drill video, generate a scaffold movement payload, and review deterministic drill-aware evaluation output."
      capsule="Upload pipeline"
      actions={
        <CTAButton asChild>
          <Link href="/sports">Browse Sports</Link>
        </CTAButton>
      }
    >
      {() => <UploadSessionContent sessionId={params.sessionId} />}
    </AppShell>
  );
}

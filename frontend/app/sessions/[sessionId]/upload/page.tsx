"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ChangeEvent, DragEvent, useEffect, useState } from "react";
import { ArrowLeft, FileCheck2, UploadCloud } from "lucide-react";

import { Badge } from "../../../../components/ui/badge";
import { Button } from "../../../../components/ui/button";
import { CTAButton } from "../../../../components/ui/cta-button";
import { SkeletonLoader } from "../../../../components/ui/skeleton-loader";
import { AppShell } from "../../../../features/app-shell/components/AppShell";
import { EmptyState } from "../../../../features/app-shell/components/EmptyState";
import { InfoCard } from "../../../../features/app-shell/components/InfoCard";
import { SectionTitle } from "../../../../features/app-shell/components/SectionTitle";
import { AnalysisProgressCard } from "../../../../features/sessions/components/AnalysisProgressCard";
import { PoseOverlayPreview } from "../../../../features/sessions/components/PoseOverlayPreview";
import { SessionResultsPanel } from "../../../../features/sessions/components/SessionResultsPanel";
import { SessionInputModeToggle } from "../../../../features/sessions/components/SessionInputModeToggle";
import { SessionStatusBadge } from "../../../../features/sessions/components/SessionStatusBadge";
import { useSessionAnalysis } from "../../../../features/sessions/hooks/useSessionAnalysis";
import { getErrorMessage } from "../../../../lib/api";
import { formatDateTime, formatEnumLabel, formatFileSize } from "../../../../lib/formatters";
import { validateVideoFile } from "../../../../lib/session-validation";
import {
  getSession,
  getSessionArtifacts,
  submitSessionUpload
} from "../../../../services/sessions";
import type {
  SessionArtifactsResponse,
  TrainingSession,
  UploadProcessingResponse
} from "../../../../types/sessions";

function formatCaptureIssue(issue: string) {
  switch (issue) {
    case "POSE_EXTRACTION_FAILURE":
      return "Pose extraction failed. Try MP4 format, better lighting, or check that the full body is visible.";
    case "VIDEO_UNREADABLE":
      return "The uploaded video could not be read. Try exporting the clip again in MP4 or MOV format.";
    case "ZERO_FRAMES":
      return "No readable frames were found in the uploaded video.";
    case "ZERO_VALID_FRAMES":
      return "The clip did not contain enough full-body frames for pose detection.";
    case "PERCEPTION_RUNTIME_UNAVAILABLE":
      return "The pose extraction service is temporarily unavailable.";
    case "MEDIAPIPE_RUNTIME_UNAVAILABLE":
      return "Pose detection could not be initialized for this upload.";
    case "OPENCV_RUNTIME_UNAVAILABLE":
      return "Video decoding is unavailable on the server right now.";
    default:
      return issue
        .replace(/^MISSING_SYSTEM_LIBRARY:/, "Missing system library: ")
        .replace(/^POSE_EXTRACTION_EXCEPTION:/, "Pose extraction exception: ")
        .replaceAll("_", " ");
  }
}

function UploadSessionContent({ sessionId }: { sessionId: string }) {
  const [session, setSession] = useState<TrainingSession | null>(null);
  const [artifactSnapshot, setArtifactSnapshot] =
    useState<SessionArtifactsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string | null>(null);
  const [localErrors, setLocalErrors] = useState<string[]>([]);
  const [localWarnings, setLocalWarnings] = useState<string[]>([]);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadProcessingResponse | null>(
    null
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDragActive, setIsDragActive] = useState(false);
  const {
    analysisError,
    analysisState,
    analysisSteps,
    analysisWarnings,
    currentStep,
    resetAnalysis,
    runAnalysis
  } = useSessionAnalysis(sessionId, (artifacts) => {
    setArtifactSnapshot(artifacts);
  });

  useEffect(() => {
    let ignore = false;

    async function loadSessionData() {
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
          setLoadError(getErrorMessage(error));
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    loadSessionData();

    return () => {
      ignore = true;
    };
  }, [sessionId]);

  useEffect(() => {
    if (!selectedFile) {
      setVideoPreviewUrl(null);
      return;
    }

    const previewUrl = URL.createObjectURL(selectedFile);
    setVideoPreviewUrl(previewUrl);

    return () => {
      URL.revokeObjectURL(previewUrl);
    };
  }, [selectedFile]);

  const poseSequenceSummary =
    uploadResult?.pose_sequence ?? artifactSnapshot?.pose_sequence ?? null;
  const hasPoseData = Boolean(poseSequenceSummary);
  const captureValidation = uploadResult?.capture_validation ?? null;
  const displayWarnings = [
    ...localWarnings,
    ...(uploadResult?.validation.warnings ?? [])
  ];
  const displayErrors = [...localErrors, ...(uploadResult?.validation.errors ?? [])];
  const captureIssues = [
    ...(captureValidation && !captureValidation.is_valid
      ? [captureValidation.message]
      : []),
    ...(poseSequenceSummary?.diagnostic_flags.map(formatCaptureIssue) ?? [])
  ];

  const canUpload = session?.input_type === "UPLOAD";
  const canAnalyze = hasPoseData;

  function handleSelectedFile(file: File | null) {
    setSelectedFile(file);
    setUploadResult(null);
    setSubmitError(null);
    resetAnalysis();

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
      setSubmitError("Upload a video to begin analysis.");
      return;
    }

    const validation = validateVideoFile(selectedFile);
    setLocalErrors(validation.errors);
    setLocalWarnings(validation.warnings);
    setSubmitError(null);
    resetAnalysis();

    if (!validation.isValid) {
      return;
    }

    try {
      setIsSubmitting(true);
      const result = await submitSessionUpload(sessionId, selectedFile);
      setUploadResult(result);
      setArtifactSnapshot(await getSessionArtifacts(sessionId));
    } catch (error) {
      setSubmitError(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleAnalyzeSession() {
    await runAnalysis();
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader className="h-64" />
        <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
          <SkeletonLoader className="h-[420px]" />
          <SkeletonLoader className="h-[420px]" />
        </div>
        <div className="grid gap-5 xl:grid-cols-2">
          <SkeletonLoader className="h-[320px]" />
          <SkeletonLoader className="h-[320px]" />
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

  return (
    <div className="space-y-8">
      <InfoCard className="relative overflow-hidden border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.16),_transparent_35%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))]">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap gap-2">
              <Badge variant="accent">{session.sport_name}</Badge>
              <Badge variant="slate">{formatEnumLabel(session.input_type)}</Badge>
              {session.camera_view ? (
                <Badge variant="slate">{formatEnumLabel(session.camera_view)}</Badge>
              ) : null}
              {session.dominant_side ? (
                <Badge variant="slate">{formatEnumLabel(session.dominant_side)}</Badge>
              ) : null}
              <SessionStatusBadge status={session.status} />
            </div>
            <h2 className="mt-5 font-display text-4xl font-bold text-white sm:text-5xl">
              {session.drill_name}
            </h2>
            <p className="mt-4 text-sm text-muted-gray sm:text-base">
              Load a clip, confirm the framing, then break down the rep in one guided flow.
            </p>
          </div>

          <div className="grid gap-3 xl:min-w-[280px]">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Started
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

      <InfoCard>
        <SessionInputModeToggle
          mode="UPLOAD"
          sessionDrillId={session.drill_id}
          secondaryActionLabel="Start a new live session"
          secondaryActionHref={`/sessions/new?drillId=${session.drill_id}&mode=LIVE`}
          helperText="This session is locked to upload video. Start a new live session if you want camera-based capture for the next rep."
        />
      </InfoCard>

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <InfoCard className="relative overflow-hidden">
          <SectionTitle
            eyebrow="Input"
            title="Upload your performance clip"
            description="Choose one rep, keep the whole movement in frame, and send it through the review flow."
          />

          {canUpload ? (
            <>
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
                  Drop your clip here
                </h3>
                <p className="mt-3 text-sm text-muted-gray">
                  MP4, MOV, WEBM, or MKV. One clip per session.
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-3">
                  <label className="inline-flex cursor-pointer items-center justify-center rounded-2xl bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground shadow-[0_14px_34px_rgba(255,122,0,0.22)] transition-all duration-300 hover:-translate-y-0.5 hover:scale-[1.02] hover:bg-primary/90 hover:shadow-[0_18px_42px_rgba(255,122,0,0.28)]">
                    Choose Video
                    <input
                      type="file"
                      accept="video/mp4,video/quicktime,video/webm,video/x-matroska"
                      className="hidden"
                      onChange={handleInputChange}
                    />
                  </label>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => handleSelectedFile(null)}
                  >
                    Clear selection
                  </Button>
                </div>
                {selectedFile ? (
                  <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 text-left">
                    <p className="text-sm font-semibold text-white">
                      {selectedFile.name}
                    </p>
                    <p className="mt-2 text-sm text-muted-gray">
                      {selectedFile.type || "Unknown type"} ·{" "}
                      {formatFileSize(selectedFile.size)}
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
                  {isSubmitting ? "Uploading clip" : "Upload Clip"}
                </Button>
                <Badge variant="slate">100 MB max</Badge>
              </div>
            </>
          ) : (
            <div className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-4 text-sm leading-7 text-amber-100">
              This session was created for live camera. Upload is not available on
              this session. Start a new upload session from setup if you want to
              analyze a recorded clip.
            </div>
          )}
        </InfoCard>

        <InfoCard>
          <SectionTitle
            eyebrow="Preview"
            title="Preview before analysis"
            description="Your video preview and overlay-ready canvas stay aligned here."
          />

          <div className="mt-6">
            <PoseOverlayPreview
              showVideo={Boolean(videoPreviewUrl)}
              videoSrc={videoPreviewUrl}
              controls
              emptyTitle="Pose overlay preview"
              emptyDescription="Choose a clip to preview it here. Skeleton guide will appear after pose detection."
              overlayMessage="Pose overlay preview · Skeleton guide will appear after pose detection"
            />
          </div>

          <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Preview status
            </p>
            <p className="mt-3 text-sm text-white/85">
              {videoPreviewUrl
                ? "Preview ready. Upload when the rep looks framed correctly."
                : "Upload a video to begin analysis."}
            </p>
          </div>
        </InfoCard>
      </div>

      <div className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <InfoCard>
          <SectionTitle
            eyebrow="Validation"
            title="Clip readiness"
            description="Frames processed, valid movement data, and capture issues from this upload."
          />

          {submitError ? (
            <div className="mt-6 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-4 text-sm leading-7 text-rose-100">
              {submitError}
            </div>
          ) : null}

          {displayErrors.length ? (
            <div className="mt-6 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-4">
              <p className="text-xs uppercase tracking-[0.22em] text-rose-200">
                File issues
              </p>
              <ul className="mt-3 space-y-2 text-sm text-rose-100">
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
              <ul className="mt-3 space-y-2 text-sm text-amber-100">
                {displayWarnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {poseSequenceSummary ? (
            <>
              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Frames processed
                  </p>
                  <p className="mt-3 text-2xl font-bold text-white">
                    {poseSequenceSummary.frame_count}
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Valid frames
                  </p>
                  <p className="mt-3 text-2xl font-bold text-white">
                    {poseSequenceSummary.valid_frame_count}
                  </p>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
                <div className="flex items-center gap-3">
                  <FileCheck2 className="h-5 w-5 text-primary" />
                  <p className="text-sm font-semibold text-white">
                    {captureValidation?.message ??
                      uploadResult?.next_step ??
                      "Upload complete."}
                  </p>
                </div>
                <div className="mt-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    Capture issues
                  </p>
                  {captureIssues.length ? (
                    <ul className="mt-3 space-y-2 text-sm text-white/85">
                      {captureIssues.map((issue) => (
                        <li key={issue}>{issue}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-3 text-sm text-muted-gray">
                      No capture issues detected.
                    </p>
                  )}
                </div>
              </div>
            </>
          ) : (
            <p className="mt-6 text-sm text-muted-gray">
              Upload a video to begin analysis.
            </p>
          )}
        </InfoCard>

        <AnalysisProgressCard
          analysisError={analysisError}
          analysisState={analysisState}
          analysisSteps={analysisSteps}
          analysisWarnings={analysisWarnings}
          currentStep={currentStep}
        />
      </div>

      <InfoCard>
        <SectionTitle
          eyebrow="Action"
          title="Analyze performance"
          description="Run the full evaluation and coaching pipeline with one action."
        />

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <CTAButton
            type="button"
            onClick={handleAnalyzeSession}
            disabled={!canAnalyze || analysisState === "RUNNING"}
          >
            {analysisState === "RUNNING" ? "Analyzing performance" : "Analyze Performance"}
          </CTAButton>
          <Badge variant="slate">
            {canAnalyze
              ? "Ready to analyze"
              : "Upload a video to begin analysis"}
          </Badge>
        </div>
      </InfoCard>

      <SessionResultsPanel
        session={session}
        artifacts={artifactSnapshot}
        analysisState={analysisState}
        analysisError={analysisError}
        analysisWarnings={analysisWarnings}
      />
    </div>
  );
}

export default function UploadSessionPage() {
  const params = useParams<{ sessionId: string }>();

  return (
    <AppShell
      eyebrow="Upload"
      title="Training input"
      description="Upload your clip, confirm the preview, and analyze the full performance."
      capsule="Input"
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

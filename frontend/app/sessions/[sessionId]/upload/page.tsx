"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  CircleAlert,
  CircleDashed,
  FileCheck2,
  LoaderCircle,
  UploadCloud
} from "lucide-react";

import { Badge } from "../../../../components/ui/badge";
import { Button } from "../../../../components/ui/button";
import { CTAButton } from "../../../../components/ui/cta-button";
import { Label } from "../../../../components/ui/label";
import { Select } from "../../../../components/ui/select";
import { SkeletonLoader } from "../../../../components/ui/skeleton-loader";
import { AppShell } from "../../../../features/app-shell/components/AppShell";
import { EmptyState } from "../../../../features/app-shell/components/EmptyState";
import { InfoCard } from "../../../../features/app-shell/components/InfoCard";
import { SectionTitle } from "../../../../features/app-shell/components/SectionTitle";
import { PoseOverlayPreview } from "../../../../features/sessions/components/PoseOverlayPreview";
import { SessionResultsPanel } from "../../../../features/sessions/components/SessionResultsPanel";
import { useSessionAnalysis } from "../../../../features/sessions/hooks/useSessionAnalysis";
import {
  ACTIVE_SIDE_OPTIONS,
  buildReplacementSessionPayload,
  getCameraViewOptions,
  resolveCameraView,
  resolveDominantSide,
  validateSessionSetup
} from "../../../../features/sessions/session-setup-utils";
import { getErrorMessage } from "../../../../lib/api";
import { formatEnumLabel, formatFileSize } from "../../../../lib/formatters";
import { validateVideoFile } from "../../../../lib/session-validation";
import { getDrillById } from "../../../../services/drills";
import {
  createSession,
  getSession,
  getSessionArtifacts,
  submitSessionUpload
} from "../../../../services/sessions";
import type { DrillDetail } from "../../../../types/drills";
import type { ProfileResponse } from "../../../../types/profile";
import type {
  AnalysisProgressStep,
  AnalysisStepStatus,
  CameraView,
  DominantSide,
  PoseSequenceSummary,
  SessionArtifactsResponse,
  TrainingSession,
  UploadProcessingResponse
} from "../../../../types/sessions";

type UploadStage =
  | "IDLE"
  | "PREPARING"
  | "UPLOADING"
  | "PROCESSING"
  | "BUILDING_OVERLAY"
  | "READY"
  | "ERROR";

const UPLOAD_STAGE_COPY: Record<
  UploadStage,
  { label: string; message: string; buttonLabel: string }
> = {
  IDLE: {
    label: "Awaiting clip",
    message: "Choose a clip to start processing.",
    buttonLabel: "Upload Clip"
  },
  PREPARING: {
    label: "Preparing upload...",
    message: "Checking file and setup before sending the clip.",
    buttonLabel: "Preparing..."
  },
  UPLOADING: {
    label: "Uploading video...",
    message: "Sending the selected clip to TrainUp.",
    buttonLabel: "Uploading..."
  },
  PROCESSING: {
    label: "Processing pose data...",
    message: "Extracting pose frames and building the movement timeline.",
    buttonLabel: "Processing..."
  },
  BUILDING_OVERLAY: {
    label: "Building preview overlay...",
    message: "Loading the processed pose frames into the preview.",
    buttonLabel: "Building overlay..."
  },
  READY: {
    label: "Ready for analysis",
    message: "Pose data is ready. You can analyze performance now.",
    buttonLabel: "Upload Clip"
  },
  ERROR: {
    label: "Needs attention",
    message: "Upload or processing failed. Review the message and try again.",
    buttonLabel: "Retry Upload"
  }
};

function getFileKey(file: File) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function poseCacheWasReused(poseSequence?: PoseSequenceSummary | null) {
  return Boolean(poseSequence?.processing_metadata?.cache_hit);
}

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

function getAnalysisStepTone(status: AnalysisStepStatus) {
  switch (status) {
    case "COMPLETED":
      return "success";
    case "FAILED":
      return "danger";
    case "WARNING":
      return "warning";
    case "RUNNING":
      return "active";
    default:
      return "idle";
  }
}

function AnalysisStepIcon({ status }: { status: AnalysisStepStatus }) {
  if (status === "COMPLETED") {
    return <CheckCircle2 className="h-4 w-4 text-emerald-300" />;
  }

  if (status === "FAILED") {
    return <CircleAlert className="h-4 w-4 text-rose-300" />;
  }

  if (status === "WARNING") {
    return <CircleAlert className="h-4 w-4 text-amber-300" />;
  }

  if (status === "RUNNING") {
    return <LoaderCircle className="h-4 w-4 animate-spin text-primary" />;
  }

  return <CircleDashed className="h-4 w-4 text-white/35" />;
}

function AnalysisPipelineSteps({
  steps
}: {
  steps: AnalysisProgressStep[];
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5">
      {steps.map((step) => {
        const tone = getAnalysisStepTone(step.status);

        return (
          <div
            key={step.id}
            className={`flex min-w-0 items-center gap-2 rounded-[1.1rem] border px-3 py-2.5 transition-all duration-300 ${
              tone === "success"
                ? "border-emerald-400/20 bg-emerald-500/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]"
                : tone === "danger"
                  ? "border-rose-400/25 bg-rose-500/10"
                  : tone === "warning"
                    ? "border-amber-400/25 bg-amber-500/10"
                    : tone === "active"
                      ? "border-primary/35 bg-primary/10 shadow-[0_12px_34px_rgba(255,122,0,0.12)]"
                      : "border-white/10 bg-white/[0.035]"
            }`}
          >
            <AnalysisStepIcon status={step.status} />
            <div className="min-w-0">
              <p className="truncate text-xs font-semibold text-white/90">
                {step.label}
              </p>
              <p className="mt-0.5 text-[10px] uppercase tracking-[0.16em] text-muted-gray">
                {step.required ? "Required" : "Advanced"}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function UploadSessionContent({
  sessionId,
  profile
}: {
  sessionId: string;
  profile: ProfileResponse | null;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setupFlowEnabled = searchParams.get("setup") === "1";
  const wasReplaced = searchParams.get("replaced") === "1";
  const resultsRef = useRef<HTMLDivElement | null>(null);
  const [session, setSession] = useState<TrainingSession | null>(null);
  const [drill, setDrill] = useState<DrillDetail | null>(null);
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
  const [uploadStage, setUploadStage] = useState<UploadStage>("IDLE");
  const [uploadNotice, setUploadNotice] = useState<string | null>(null);
  const [processedFileKey, setProcessedFileKey] = useState<string | null>(null);
  const [isApplyingSetup, setIsApplyingSetup] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);
  const [selectedCameraView, setSelectedCameraView] = useState<CameraView | "">("");
  const [selectedDominantSide, setSelectedDominantSide] =
    useState<DominantSide>("AUTO");
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
  const previousAnalysisStateRef = useRef(analysisState);

  useEffect(() => {
    let ignore = false;

    async function loadSessionData() {
      setLoadError(null);

      try {
        const sessionDetail = await getSession(sessionId);
        const [artifactsDetail, drillDetail] = await Promise.all([
          getSessionArtifacts(sessionId),
          getDrillById(sessionDetail.drill_id)
        ]);

        if (!ignore) {
          setSession(sessionDetail);
          setDrill(drillDetail);
          setArtifactSnapshot(artifactsDetail);
          setSelectedCameraView(
            resolveCameraView(drillDetail, sessionDetail.camera_view)
          );
          setSelectedDominantSide(resolveDominantSide(sessionDetail.dominant_side));
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

  useEffect(() => {
    const previousAnalysisState = previousAnalysisStateRef.current;
    previousAnalysisStateRef.current = analysisState;

    if (
      previousAnalysisState === "RUNNING" &&
      (analysisState === "COMPLETED" ||
        analysisState === "COMPLETED_WITH_WARNINGS" ||
        analysisState === "FAILED")
    ) {
      window.requestAnimationFrame(() => {
        resultsRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });
      });
    }
  }, [analysisState]);

  const currentPoseSequence =
    selectedFile && !uploadResult ? null : artifactSnapshot?.pose_sequence ?? null;
  const poseSequenceSummary = uploadResult?.pose_sequence ?? currentPoseSequence;
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
  const setupLocked =
    isSubmitting ||
    Boolean(uploadResult) ||
    Boolean(artifactSnapshot?.pose_sequence) ||
    session?.status !== "ACTIVE";
  const setupEditable = Boolean(setupFlowEnabled && session && !setupLocked);
  const setupHasChanges = Boolean(
    session &&
      (selectedCameraView !== resolveCameraView(drill, session.camera_view) ||
        selectedDominantSide !== resolveDominantSide(session.dominant_side))
  );
  const canAnalyze = hasPoseData;
  const cameraViewOptions = getCameraViewOptions(drill);
  const setupControlsDisabled = !setupEditable || setupLocked || isApplyingSetup;
  const setupStateLabel = setupLocked
    ? "Locked"
    : setupEditable
      ? setupHasChanges
        ? "Changes pending"
        : "Ready"
      : "Read-only";
  const setupHelperText = setupLocked
    ? "Setup is locked after capture starts."
    : setupEditable
      ? "Changing setup before capture will restart this session with the new settings."
      : "Existing session setup is read-only.";
  const activeAnalysisStep =
    analysisSteps.find((step) => step.id === currentStep) ??
    analysisSteps.find((step) => step.status === "RUNNING") ??
    null;
  const uploadStageCopy = UPLOAD_STAGE_COPY[uploadStage];
  const poseCacheHit = poseCacheWasReused(poseSequenceSummary);
  const uploadReadinessLabel = poseSequenceSummary
    ? "Processed"
    : isSubmitting
      ? uploadStageCopy.label
      : selectedFile
      ? displayErrors.length
        ? "Needs attention"
        : "Ready for upload"
      : "Awaiting clip";
  const previewStatus =
    currentPoseSequence?.status === "COMPLETED" &&
    currentPoseSequence.valid_frame_count > 0
      ? "Pose overlay active"
      : videoPreviewUrl
        ? "Preview ready"
        : "Awaiting clip";

  async function handleApplySetupChanges() {
    if (!session) {
      return;
    }

    const validationError = validateSessionSetup({
      drill,
      cameraView: selectedCameraView,
      dominantSide: selectedDominantSide
    });

    if (validationError) {
      setSetupError(validationError);
      return;
    }

    if (!selectedCameraView) {
      return;
    }

    if (!setupHasChanges) {
      return;
    }

    setSetupError(null);
    setIsApplyingSetup(true);

    try {
      const replacementSession = await createSession(
        buildReplacementSessionPayload({
          session,
          drill,
          profile,
          cameraView: selectedCameraView,
          dominantSide: selectedDominantSide
        })
      );

      router.replace(`/sessions/${replacementSession.id}/upload?setup=1&replaced=1`);
    } catch (error) {
      setSetupError(getErrorMessage(error));
      setIsApplyingSetup(false);
    }
  }

  function handleSelectedFile(file: File | null) {
    if (isSubmitting) {
      return;
    }

    setSelectedFile(file);
    setUploadResult(null);
    setSubmitError(null);
    setUploadNotice(null);
    resetAnalysis();

    if (!file) {
      setLocalErrors([]);
      setLocalWarnings([]);
      setUploadStage("IDLE");
      setProcessedFileKey(null);
      return;
    }

    const validation = validateVideoFile(file);
    setLocalErrors(validation.errors);
    setLocalWarnings(validation.warnings);
    setUploadStage("IDLE");
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    handleSelectedFile(event.target.files?.[0] ?? null);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragActive(false);
    if (isSubmitting) {
      return;
    }
    handleSelectedFile(event.dataTransfer.files?.[0] ?? null);
  }

  async function handleUpload() {
    if (setupHasChanges) {
      setSetupError("Apply setup changes before uploading this clip.");
      return;
    }

    const setupValidationError = validateSessionSetup({
      drill,
      cameraView: selectedCameraView,
      dominantSide: selectedDominantSide
    });
    if (setupValidationError) {
      setSetupError(setupValidationError);
      return;
    }

    if (!selectedFile) {
      setSubmitError("Upload a video to begin analysis.");
      return;
    }

    const nextFileKey = getFileKey(selectedFile);
    if (uploadResult && processedFileKey === nextFileKey && poseSequenceSummary) {
      setUploadStage("READY");
      setUploadNotice("This clip is already processed. You can analyze it now.");
      return;
    }

    const validation = validateVideoFile(selectedFile);
    setLocalErrors(validation.errors);
    setLocalWarnings(validation.warnings);
    setSubmitError(null);
    setUploadNotice(null);
    resetAnalysis();

    if (!validation.isValid) {
      setUploadStage("ERROR");
      return;
    }

    let processingTimer: number | null = null;

    try {
      setIsSubmitting(true);
      setUploadStage("PREPARING");
      await new Promise<void>((resolve) => {
        window.setTimeout(resolve, 120);
      });
      setUploadStage("UPLOADING");
      processingTimer = window.setTimeout(() => {
        setUploadStage("PROCESSING");
      }, 850);
      const result = await submitSessionUpload(sessionId, selectedFile);
      if (processingTimer !== null) {
        window.clearTimeout(processingTimer);
        processingTimer = null;
      }
      setUploadStage("BUILDING_OVERLAY");
      setUploadResult(result);
      setArtifactSnapshot(await getSessionArtifacts(sessionId));
      setProcessedFileKey(nextFileKey);
      setUploadNotice(
        poseCacheWasReused(result.pose_sequence)
          ? "Pose data was reused from the cached processing result."
          : "Pose data processed. Preview overlay is ready."
      );
      setUploadStage("READY");
    } catch (error) {
      if (processingTimer !== null) {
        window.clearTimeout(processingTimer);
      }
      setUploadStage("ERROR");
      setSubmitError(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleAnalyzeSession() {
    await runAnalysis();
  }

  function handleStartNewSession() {
    if (session?.drill_id) {
      router.push(`/drills/${session.drill_id}`);
      return;
    }

    router.push("/sports");
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
    <div className="space-y-5">
      <InfoCard className="border-primary/15 p-4 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap gap-2">
              <Badge variant="accent">{session.sport_name}</Badge>
              <Badge variant="slate">{formatEnumLabel(session.skill_level)}</Badge>
            </div>
            <h2 className="mt-3 line-clamp-2 font-display text-3xl font-bold tracking-tight text-white sm:text-[2.45rem]">
              {session.drill_name}
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-gray sm:text-base">
              Upload one clean set and analyze movement quality.
            </p>
          </div>

          <Button
            asChild
            variant="outline"
            className="w-full justify-center rounded-2xl px-5 py-4 text-white/90 sm:w-auto"
          >
            <Link href={`/drills/${session.drill_id}`}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Drill
            </Link>
          </Button>
        </div>
      </InfoCard>

      <InfoCard className="p-3.5 sm:p-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
          <div className="min-w-0 xl:w-[24%]">
            <p className="text-[10px] uppercase tracking-[0.18em] text-muted-gray">
              Session setup
            </p>
            <p className="mt-1.5 line-clamp-1 text-sm font-semibold text-white">
              {session.drill_name}
            </p>
            <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-gray">
              {setupHelperText}
            </p>
          </div>

          <div className="grid flex-1 gap-2.5 sm:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,0.75fr)_auto]">
            <div className="min-w-0">
              <Label htmlFor="upload-camera-view" className="text-xs">
                Camera view
              </Label>
              <Select
                id="upload-camera-view"
                value={selectedCameraView}
                disabled={setupControlsDisabled}
                className="mt-1.5 h-9 rounded-xl px-3 text-xs"
                onChange={(event) => {
                  setSetupError(null);
                  setSelectedCameraView(event.target.value as CameraView);
                }}
              >
                {cameraViewOptions.map((view) => (
                  <option key={view} value={view} className="bg-slate text-white">
                    {formatEnumLabel(view)}
                  </option>
                ))}
              </Select>
            </div>

            <div className="min-w-0">
              <Label htmlFor="upload-active-side" className="text-xs">
                Active side
              </Label>
              <Select
                id="upload-active-side"
                value={selectedDominantSide}
                disabled={setupControlsDisabled}
                className="mt-1.5 h-9 rounded-xl px-3 text-xs"
                onChange={(event) => {
                  setSetupError(null);
                  setSelectedDominantSide(event.target.value as DominantSide);
                }}
              >
                {ACTIVE_SIDE_OPTIONS.map((option) => (
                  <option
                    key={option.value}
                    value={option.value}
                    className="bg-slate text-white"
                  >
                    {option.label}
                  </option>
                ))}
              </Select>
            </div>

            <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-2.5">
              <p className="text-[10px] uppercase tracking-[0.18em] text-muted-gray">
                Mode
              </p>
              <p className="mt-1.5 truncate text-sm font-semibold text-white">
                Upload Video
              </p>
            </div>

            <div className="flex flex-col justify-end gap-2">
              <Badge
                variant={
                  setupLocked
                    ? "warning"
                    : setupHasChanges
                      ? "accent"
                      : "slate"
                }
                className="justify-center"
              >
                {setupStateLabel}
              </Badge>
              {setupEditable && !setupLocked ? (
                <Button
                  type="button"
                  size="sm"
                  variant={setupHasChanges ? "default" : "outline"}
                  onClick={() => {
                    void handleApplySetupChanges();
                  }}
                  disabled={!setupHasChanges || isApplyingSetup}
                >
                  {isApplyingSetup ? "Applying" : "Apply setup changes"}
                </Button>
              ) : null}
            </div>
          </div>
        </div>

        {setupError || wasReplaced ? (
          <div
            className={`mt-3 rounded-2xl border px-4 py-2.5 text-sm leading-6 ${
              setupError
                ? "border-rose-400/30 bg-rose-500/10 text-rose-100"
                : "border-primary/25 bg-primary/10 text-primary"
            }`}
          >
            {setupError ??
              "Setup changes were applied. The previous unused session was discarded from this flow."}
          </div>
        ) : null}
      </InfoCard>

      <div className="space-y-5">
        <InfoCard className="relative overflow-hidden border-primary/10 bg-[radial-gradient(circle_at_top_left,_rgba(255,122,0,0.08),_transparent_38%),linear-gradient(180deg,rgba(255,255,255,0.058),rgba(255,255,255,0.022))]">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <SectionTitle
              eyebrow="Step 1"
              title="Upload clip"
              description="One clean set. Stable camera."
            />
            <Badge variant={displayErrors.length ? "danger" : "slate"}>
              {uploadReadinessLabel}
            </Badge>
          </div>
          <p className="mt-2 text-[10px] leading-4 text-white/40">
            Best results with clear full-body visibility.
          </p>

          {canUpload ? (
            <>
              <div
                onDragOver={(event) => {
                  event.preventDefault();
                  if (isSubmitting) {
                    return;
                  }
                  setIsDragActive(true);
                }}
                onDragLeave={() => setIsDragActive(false)}
                onDrop={handleDrop}
                className={`group mt-4 min-h-[260px] rounded-[1.75rem] border border-dashed px-5 py-7 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] transition-all duration-300 hover:border-primary/30 hover:bg-white/[0.045] hover:shadow-[0_18px_58px_rgba(0,0,0,0.22)] ${
                  isDragActive
                    ? "border-primary/50 bg-primary/10 shadow-[0_20px_70px_rgba(255,122,0,0.14)]"
                    : isSubmitting
                      ? "border-white/10 bg-white/[0.025] opacity-75"
                    : "border-white/12 bg-white/[0.03]"
                }`}
              >
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-3xl border border-primary/20 bg-primary/10 text-primary transition-transform duration-300 group-hover:scale-105">
                  <UploadCloud className="h-6 w-6" />
                </div>
                <h3 className="mt-4 font-display text-2xl font-bold text-white">
                  Drop video here
                </h3>
                <p className="mt-2 text-sm text-muted-gray">
                  MP4, MOV, WEBM, or MKV. 100 MB max.
                </p>
                <div className="mt-5 flex flex-wrap justify-center gap-3">
                  <label
                    className={`inline-flex items-center justify-center rounded-2xl bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground shadow-[0_14px_34px_rgba(255,122,0,0.22)] transition-all duration-300 hover:-translate-y-0.5 hover:scale-[1.02] hover:bg-primary/90 hover:shadow-[0_18px_42px_rgba(255,122,0,0.28)] ${
                      isSubmitting
                        ? "pointer-events-none cursor-not-allowed opacity-65"
                        : "cursor-pointer"
                    }`}
                  >
                    Choose Video
                    <input
                      type="file"
                      accept="video/mp4,video/quicktime,video/webm,video/x-matroska"
                      className="hidden"
                      disabled={isSubmitting}
                      onChange={handleInputChange}
                    />
                  </label>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => handleSelectedFile(null)}
                    disabled={!selectedFile || isSubmitting}
                  >
                    Clear
                  </Button>
                </div>
              </div>

              {selectedFile ? (
                <div className="mt-4 flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-white">
                      {selectedFile.name}
                    </p>
                    <p className="mt-1 text-sm text-muted-gray">
                      {selectedFile.type || "Unknown type"} ·{" "}
                      {formatFileSize(selectedFile.size)}
                    </p>
                  </div>
                  <Button
                    type="button"
                    onClick={handleUpload}
                    className="rounded-2xl px-6"
                    disabled={!selectedFile || isSubmitting}
                  >
                    {isSubmitting ? uploadStageCopy.buttonLabel : "Upload Clip"}
                  </Button>
                </div>
              ) : null}

              {uploadStage !== "IDLE" || uploadNotice ? (
                <div
                  className={`mt-4 rounded-2xl border px-4 py-4 ${
                    uploadStage === "ERROR"
                      ? "border-rose-400/30 bg-rose-500/10"
                      : uploadStage === "READY"
                        ? "border-emerald-400/25 bg-emerald-500/10"
                        : "border-primary/25 bg-primary/10"
                  }`}
                >
                  <div className="flex min-w-0 items-start gap-3">
                    {isSubmitting ? (
                      <LoaderCircle className="mt-0.5 h-5 w-5 shrink-0 animate-spin text-primary" />
                    ) : uploadStage === "READY" ? (
                      <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-300" />
                    ) : uploadStage === "ERROR" ? (
                      <CircleAlert className="mt-0.5 h-5 w-5 shrink-0 text-rose-300" />
                    ) : (
                      <CircleDashed className="mt-0.5 h-5 w-5 shrink-0 text-white/45" />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-white">
                        {uploadStageCopy.label}
                      </p>
                      <p className="mt-1 text-sm leading-6 text-white/65">
                        {uploadNotice ?? uploadStageCopy.message}
                      </p>
                      {poseCacheHit ? (
                        <p className="mt-2 text-xs font-semibold text-emerald-200">
                          Cached pose extraction reused.
                        </p>
                      ) : isSubmitting && uploadStage === "PROCESSING" ? (
                        <p className="mt-2 text-xs text-white/45">
                          Longer clips can take a moment while pose frames are extracted.
                        </p>
                      ) : null}
                    </div>
                  </div>
                </div>
              ) : null}
            </>
          ) : (
            <div className="mt-5 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-4 text-sm leading-7 text-amber-100">
              This session was created for live camera. Return to the drill launcher to create an upload session.
            </div>
          )}

          <div className="mt-5 rounded-2xl border border-white/10 bg-background-dark/45 px-4 py-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <FileCheck2 className="h-5 w-5 shrink-0 text-primary" />
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-white">
                    {captureValidation?.message ??
                      uploadResult?.next_step ??
                      uploadReadinessLabel}
                  </p>
                  <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-gray">
                    {drill?.reference_payload.notes ??
                      "Use the recommended camera angle for reliable analysis."}
                  </p>
                </div>
              </div>
              {poseSequenceSummary ? (
                <div className="flex gap-2">
                  <Badge variant="slate">
                    {poseSequenceSummary.frame_count} frames
                  </Badge>
                  <Badge variant="success">
                    {poseSequenceSummary.valid_frame_count} valid
                  </Badge>
                </div>
              ) : null}
            </div>

            {submitError ? (
              <div className="mt-4 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm leading-6 text-rose-100">
                {submitError}
              </div>
            ) : null}

            {displayErrors.length || displayWarnings.length || captureIssues.length ? (
              <div className="mt-4 grid gap-3 lg:grid-cols-3">
                {displayErrors.length ? (
                  <div className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.2em] text-rose-200">
                      File issues
                    </p>
                    <ul className="mt-2 space-y-1 text-sm text-rose-100">
                      {displayErrors.map((error) => (
                        <li key={error}>{error}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {displayWarnings.length ? (
                  <div className="rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.2em] text-amber-200">
                      Warnings
                    </p>
                    <ul className="mt-2 space-y-1 text-sm text-amber-100">
                      {displayWarnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {captureIssues.length ? (
                  <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                      Protocol
                    </p>
                    <ul className="mt-2 space-y-1 text-sm text-white/85">
                      {captureIssues.map((issue) => (
                        <li key={issue}>{issue}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        </InfoCard>

        <InfoCard className="border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.045),rgba(255,255,255,0.018))]">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <SectionTitle
              eyebrow="Step 2"
              title="Preview"
              description="Review framing and pose overlay before analysis."
            />
            <Badge variant={currentPoseSequence ? "success" : "slate"}>
              {previewStatus}
            </Badge>
          </div>

          <div className="mt-5">
            <PoseOverlayPreview
              mode="upload"
              videoSrc={videoPreviewUrl}
              poseSequence={currentPoseSequence}
              isActive={Boolean(videoPreviewUrl)}
              controls
              emptyTitle="Preview clip"
              emptyDescription="Choose one clean set. The pose overlay appears after processing."
              className="border-white/12 bg-black/50 shadow-[0_24px_72px_rgba(0,0,0,0.32)]"
            />
          </div>
        </InfoCard>
      </div>

      <InfoCard className="p-4 sm:p-5">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <SectionTitle
            eyebrow="Step 3"
            title="Performance Analysis"
            description="Run evaluation and coaching feedback."
          />
          <div className="flex flex-wrap items-center gap-3">
            <CTAButton
              type="button"
              onClick={handleAnalyzeSession}
              disabled={!canAnalyze || analysisState === "RUNNING"}
            >
              {analysisState === "RUNNING"
                ? "Analyzing performance"
                : "Analyze Performance"}
            </CTAButton>
            <Badge
              variant={
                analysisState === "FAILED"
                  ? "danger"
                  : analysisState === "COMPLETED_WITH_WARNINGS"
                    ? "warning"
                    : analysisState === "COMPLETED"
                      ? "success"
                      : analysisState === "RUNNING"
                        ? "accent"
                        : "slate"
              }
            >
              {canAnalyze ? analysisState : "Upload required"}
            </Badge>
            {activeAnalysisStep ? (
              <Badge variant="slate">{activeAnalysisStep.label}</Badge>
            ) : null}
          </div>
        </div>

        <div className="mt-3">
          <AnalysisPipelineSteps steps={analysisSteps} />
        </div>

        {analysisWarnings.length || analysisState === "COMPLETED_WITH_WARNINGS" ? (
          <div className="mt-4 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm leading-6 text-amber-100">
            Some advanced insights could not be generated, but your core coaching feedback is ready.
            {analysisWarnings.length ? (
              <ul className="mt-2 space-y-1">
                {analysisWarnings.map((warning) => (
                  <li key={`${warning.step}-${warning.message}`}>
                    {warning.message}
                    {warning.diagnosticFlags.length
                      ? ` (${warning.diagnosticFlags.join(", ")})`
                      : ""}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}

        {analysisError ? (
          <div className="mt-4 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm leading-6 text-rose-100">
            {analysisError}
          </div>
        ) : null}
      </InfoCard>

      <div ref={resultsRef}>
        <SessionResultsPanel
          session={session}
          artifacts={artifactSnapshot}
          analysisState={analysisState}
          analysisError={analysisError}
          analysisWarnings={analysisWarnings}
          showAnalysisWarningBanner={false}
          onStartNewSession={handleStartNewSession}
        />
      </div>
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
      {({ profile }) => (
        <UploadSessionContent sessionId={params.sessionId} profile={profile} />
      )}
    </AppShell>
  );
}

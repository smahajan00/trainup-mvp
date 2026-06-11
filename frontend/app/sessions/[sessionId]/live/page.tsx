"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Camera, Pause, Play, Square } from "lucide-react";

import { Badge } from "../../../../components/ui/badge";
import { Button } from "../../../../components/ui/button";
import { CTAButton } from "../../../../components/ui/cta-button";
import { SkeletonLoader } from "../../../../components/ui/skeleton-loader";
import { AppShell } from "../../../../features/app-shell/components/AppShell";
import { EmptyState } from "../../../../features/app-shell/components/EmptyState";
import { InfoCard } from "../../../../features/app-shell/components/InfoCard";
import { SectionTitle } from "../../../../features/app-shell/components/SectionTitle";
import { PoseOverlayPreview } from "../../../../features/sessions/components/PoseOverlayPreview";
import { SessionSetupCard } from "../../../../features/sessions/components/SessionSetupCard";
import { SessionInputModeToggle } from "../../../../features/sessions/components/SessionInputModeToggle";
import { SessionStatusBadge } from "../../../../features/sessions/components/SessionStatusBadge";
import {
  buildReplacementSessionPayload,
  resolveCameraView,
  resolveDominantSide,
  usesFallbackSkillLevel,
  validateSessionSetup
} from "../../../../features/sessions/session-setup-utils";
import { getErrorMessage } from "../../../../lib/api";
import { formatDateTime, formatEnumLabel } from "../../../../lib/formatters";
import { getDrillById } from "../../../../services/drills";
import {
  createSession,
  endLiveSession,
  getSession,
  getSessionArtifacts,
  submitLiveFrameBatch
} from "../../../../services/sessions";
import type { DrillDetail } from "../../../../types/drills";
import type { ProfileResponse } from "../../../../types/profile";
import type {
  CameraView,
  DominantSide,
  FrameBatchResponse,
  SessionArtifactsResponse,
  TrainingSession
} from "../../../../types/sessions";

type CameraState = "idle" | "requesting" | "granted" | "denied" | "error";
type CaptureState = "IDLE" | "CAPTURING" | "PAUSED" | "STOPPED";

function isPlayInterruption(error: unknown) {
  if (!(error instanceof DOMException || error instanceof Error)) {
    return false;
  }

  return (
    error.name === "AbortError" ||
    /play\(\) request was interrupted|interrupted by a new load request/i.test(
      error.message
    )
  );
}

async function playVideoSafely(video: HTMLVideoElement | null) {
  if (!video) {
    return true;
  }

  if (!video.paused && video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
    return true;
  }

  try {
    await video.play();
    return true;
  } catch (error) {
    if (isPlayInterruption(error)) {
      return false;
    }

    throw error;
  }
}

function LiveSessionContent({
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
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const captureIntervalRef = useRef<number | null>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [session, setSession] = useState<TrainingSession | null>(null);
  const [drill, setDrill] = useState<DrillDetail | null>(null);
  const [artifactSnapshot, setArtifactSnapshot] =
    useState<SessionArtifactsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [cameraState, setCameraState] = useState<CameraState>("idle");
  const [captureState, setCaptureState] = useState<CaptureState>("IDLE");
  const [actionError, setActionError] = useState<string | null>(null);
  const [frameBatchResult, setFrameBatchResult] = useState<FrameBatchResponse | null>(
    null
  );
  const [capturedTicks, setCapturedTicks] = useState(0);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [isApplyingSetup, setIsApplyingSetup] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);
  const [selectedCameraView, setSelectedCameraView] = useState<CameraView | "">("");
  const [selectedDominantSide, setSelectedDominantSide] =
    useState<DominantSide>("AUTO");

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
    return () => {
      if (captureIntervalRef.current !== null) {
        window.clearInterval(captureIntervalRef.current);
      }

      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };
  }, []);

  function startCaptureClock() {
    if (captureIntervalRef.current !== null) {
      window.clearInterval(captureIntervalRef.current);
    }

    captureIntervalRef.current = window.setInterval(() => {
      setCapturedTicks((currentValue) => currentValue + 1);
    }, 500);
  }

  function stopCaptureClock() {
    if (captureIntervalRef.current !== null) {
      window.clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }
  }

  async function requestCameraPreview() {
    setActionError(null);
    setCameraState("requesting");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: false
      });

      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = stream;
      setCameraStream(stream);
      setCameraState("granted");

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      return true;
    } catch (error) {
      setCameraState("denied");
      setActionError(
        error instanceof Error ? error.message : "Camera access was denied."
      );
      return false;
    }
  }

  async function handleStartCamera() {
    setActionError(null);

    if (setupHasChanges) {
      setSetupError("Apply setup changes before starting the camera.");
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

    if (session?.input_type !== "LIVE") {
      setActionError(
        "This session was created for upload video. Live camera capture is unavailable on this session."
      );
      return;
    }

    const hasCamera = cameraState === "granted" || (await requestCameraPreview());
    if (!hasCamera) {
      return;
    }

    try {
      setIsStarting(true);
      const playStarted = await playVideoSafely(videoRef.current);
      if (!playStarted) {
        window.setTimeout(() => {
          void playVideoSafely(videoRef.current);
        }, 150);
      }
      setCapturedTicks(0);
      setFrameBatchResult(null);
      setCaptureState("CAPTURING");
      startCaptureClock();
    } catch (error) {
      setActionError(getErrorMessage(error));
      setCameraState("error");
    } finally {
      setIsStarting(false);
    }
  }

  async function handlePause() {
    stopCaptureClock();
    await videoRef.current?.pause();
    setCaptureState("PAUSED");
  }

  async function handleResume() {
    const playStarted = await playVideoSafely(videoRef.current);
    if (!playStarted) {
      window.setTimeout(() => {
        void playVideoSafely(videoRef.current);
      }, 150);
    }
    setCaptureState("CAPTURING");
    startCaptureClock();
  }

  async function handleStop() {
    setActionError(null);

    if (session?.input_type !== "LIVE") {
      setActionError(
        "This session was created for upload video. Live camera capture is unavailable on this session."
      );
      return;
    }

    try {
      setIsStopping(true);
      stopCaptureClock();
      await videoRef.current?.pause();
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setCameraStream(null);
      setCameraState("idle");
      setCaptureState("STOPPED");

      const frameCount = Math.max(capturedTicks, 1);
      const timestamps = Array.from({ length: frameCount }, (_, index) =>
        Number((index * 0.5).toFixed(2))
      );

      const batchResult = await submitLiveFrameBatch(sessionId, {
        frame_count: frameCount,
        timestamps,
        client_ready: true
      });
      setFrameBatchResult(batchResult);

      const updatedSession = await endLiveSession(sessionId, {
        final_status: "COMPLETED"
      });
      setSession(updatedSession);
      setArtifactSnapshot(await getSessionArtifacts(sessionId));
    } catch (error) {
      setActionError(getErrorMessage(error));
    } finally {
      setIsStopping(false);
    }
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
        icon={Camera}
        title="Live session unavailable"
        description={loadError ?? "We couldn't load this live session."}
        action={
          <CTAButton asChild>
            <Link href="/sports">Back to Sports</Link>
          </CTAButton>
        }
      />
    );
  }

  const canUseLiveActions = session.input_type === "LIVE" && session.status === "ACTIVE";
  const setupLocked =
    captureState !== "IDLE" ||
    cameraState === "requesting" ||
    cameraState === "granted" ||
    isStarting ||
    isStopping ||
    session.status !== "ACTIVE" ||
    Boolean(artifactSnapshot?.pose_sequence);
  const setupEditable = Boolean(setupFlowEnabled && !setupLocked);
  const setupHasChanges =
    selectedCameraView !== resolveCameraView(drill, session.camera_view) ||
    selectedDominantSide !== resolveDominantSide(session.dominant_side);

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

      router.replace(`/sessions/${replacementSession.id}/live?setup=1&replaced=1`);
    } catch (error) {
      setSetupError(getErrorMessage(error));
      setIsApplyingSetup(false);
    }
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
              Check camera setup, framing, and pose visibility before recording your set.
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
          mode="LIVE"
          sessionDrillId={session.drill_id}
          helperText="This session stays locked to live camera while you check setup and framing."
        />
      </InfoCard>

      <SessionSetupCard
        drill={drill}
        drillName={session.drill_name}
        sportName={session.sport_name}
        skillLevel={session.skill_level}
        inputType="LIVE"
        cameraView={selectedCameraView}
        dominantSide={selectedDominantSide}
        isEditable={setupEditable}
        isLocked={setupLocked}
        hasChanges={setupHasChanges}
        isApplying={isApplyingSetup}
        setupError={setupError}
        setupNotice={
          wasReplaced
            ? "Setup changes were applied. The previous unused session was discarded from this flow."
            : null
        }
        usesFallbackSkillLevel={usesFallbackSkillLevel(profile, drill)}
        onCameraViewChange={(value) => {
          setSetupError(null);
          setSelectedCameraView(value);
        }}
        onDominantSideChange={(value) => {
          setSetupError(null);
          setSelectedDominantSide(value);
        }}
        onApplyChanges={() => {
          void handleApplySetupChanges();
        }}
      />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(320px,0.75fr)]">
        <InfoCard className="relative overflow-hidden">
          <SectionTitle
            eyebrow="Input"
            title="Live pose preview"
            description="Use the camera controls to check pose tracking, framing, and readiness."
          />

          <div className="mt-6">
            <PoseOverlayPreview
              mode="live"
              stream={cameraStream}
              videoRef={videoRef}
              isActive={cameraState === "granted" && Boolean(cameraStream)}
              isPaused={captureState === "PAUSED"}
              mirrored
              autoPlay
              muted
              emptyTitle="Live pose overlay"
              emptyDescription="Start the camera to check framing and pose visibility. The pose overlay runs locally in your browser."
            />
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <CTAButton
              type="button"
              onClick={handleStartCamera}
              disabled={!canUseLiveActions || isStarting || captureState === "CAPTURING"}
            >
              <Camera className="mr-2 h-4 w-4" />
              {isStarting ? "Starting camera" : "Start Camera"}
            </CTAButton>
            <Button
              type="button"
              variant="outline"
              onClick={handlePause}
              disabled={captureState !== "CAPTURING"}
            >
              <Pause className="mr-2 h-4 w-4" />
              Pause
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleResume}
              disabled={captureState !== "PAUSED"}
            >
              <Play className="mr-2 h-4 w-4" />
              Resume
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleStop}
              disabled={
                !canUseLiveActions ||
                isStopping ||
                (captureState !== "CAPTURING" && captureState !== "PAUSED")
              }
            >
              <Square className="mr-2 h-4 w-4" />
              {isStopping ? "Stopping" : "Stop"}
            </Button>
          </div>
        </InfoCard>

        <InfoCard>
          <SectionTitle
            eyebrow="Preview"
            title="Capture status"
            description="Keep camera readiness, preview state, and timing clear during the setup check."
          />

          {actionError ? (
            <div className="mt-6 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-4 text-sm leading-7 text-rose-100">
              {actionError}
            </div>
          ) : null}

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Camera
              </p>
              <p className="mt-3 text-sm font-semibold text-white">
                {cameraState === "granted"
                  ? "Ready"
                  : cameraState === "requesting"
                    ? "Opening"
                    : cameraState === "denied"
                      ? "Blocked"
                      : "Off"}
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Capture
              </p>
              <p className="mt-3 text-sm font-semibold text-white">
                {captureState === "CAPTURING"
                  ? "Running"
                  : captureState === "PAUSED"
                    ? "Paused"
                    : captureState === "STOPPED"
                      ? "Stopped"
                      : "Not started"}
              </p>
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Live notes
            </p>
            <ul className="mt-3 space-y-2 text-sm text-white/85">
              <li>
                {session.input_type === "LIVE"
                  ? "Start the camera to check framing and pose visibility."
                  : "This session was created for upload video, so live capture is unavailable on this page."}
              </li>
              <li>
                {captureState === "STOPPED"
                  ? "Camera check complete. Record your set, then continue to Upload Video."
                  : "Use the pose overlay to confirm readiness before recording your set."}
              </li>
              <li>
                {frameBatchResult
                  ? `Preview timing samples submitted: ${frameBatchResult.frame_count}`
                  : captureState === "STOPPED"
                    ? "Preview timing check complete."
                    : "No preview timing samples submitted yet."}
              </li>
              <li>
                Camera preview runs locally in your browser.
              </li>
            </ul>
          </div>

          <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Capture duration
            </p>
            <p className="mt-3 text-2xl font-bold text-white">
              {(capturedTicks * 0.5).toFixed(1)}s
            </p>
          </div>
        </InfoCard>
      </div>

      <InfoCard className="p-5 sm:p-6">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Next Step
            </p>
            <h2 className="mt-2 font-display text-2xl font-bold text-white">
              Ready to analyse?
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-white/75">
              Record your set, then use the upload flow to generate saved performance
              results and coaching feedback.
            </p>
            <p className="mt-2 text-xs leading-5 text-muted-gray">
              Live camera is used here for pose preview and setup checking.
            </p>
          </div>
          <CTAButton asChild className="w-full shrink-0 sm:w-auto">
            <Link href={`/drills/${session.drill_id}`}>Go to Upload Video</Link>
          </CTAButton>
        </div>
      </InfoCard>
    </div>
  );
}

export default function LiveSessionPage() {
  const params = useParams<{ sessionId: string }>();

  return (
    <AppShell
      eyebrow="Live Session"
      title="Training input"
      description="Use the browser-side camera preview to check setup, framing, and readiness."
      capsule="Input"
      actions={
        <CTAButton asChild>
          <Link href="/sports">Browse Sports</Link>
        </CTAButton>
      }
    >
      {({ profile }) => (
        <LiveSessionContent sessionId={params.sessionId} profile={profile} />
      )}
    </AppShell>
  );
}

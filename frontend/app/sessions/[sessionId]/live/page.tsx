"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
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
import { AnalysisProgressCard } from "../../../../features/sessions/components/AnalysisProgressCard";
import { AnalysisSnapshotCard } from "../../../../features/sessions/components/AnalysisSnapshotCard";
import { PoseOverlayPreview } from "../../../../features/sessions/components/PoseOverlayPreview";
import { SessionInputModeToggle } from "../../../../features/sessions/components/SessionInputModeToggle";
import { SessionStatusBadge } from "../../../../features/sessions/components/SessionStatusBadge";
import { useSessionAnalysis } from "../../../../features/sessions/hooks/useSessionAnalysis";
import { formatDateTime, formatEnumLabel } from "../../../../lib/formatters";
import {
  endLiveSession,
  getSession,
  getSessionArtifacts,
  startLiveSession,
  submitLiveFrameBatch
} from "../../../../services/sessions";
import type {
  FrameBatchResponse,
  LiveStartResponse,
  SessionArtifactsResponse,
  TrainingSession
} from "../../../../types/sessions";

type CameraState = "idle" | "requesting" | "granted" | "denied" | "error";
type CaptureState = "IDLE" | "CAPTURING" | "PAUSED" | "STOPPED";

function LiveSessionContent({ sessionId }: { sessionId: string }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const captureIntervalRef = useRef<number | null>(null);
  const [session, setSession] = useState<TrainingSession | null>(null);
  const [artifactSnapshot, setArtifactSnapshot] =
    useState<SessionArtifactsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [cameraState, setCameraState] = useState<CameraState>("idle");
  const [captureState, setCaptureState] = useState<CaptureState>("IDLE");
  const [actionError, setActionError] = useState<string | null>(null);
  const [startResult, setStartResult] = useState<LiveStartResponse | null>(null);
  const [frameBatchResult, setFrameBatchResult] = useState<FrameBatchResponse | null>(
    null
  );
  const [capturedTicks, setCapturedTicks] = useState(0);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const {
    analysisError,
    analysisState,
    analysisSteps,
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
          setLoadError(
            error instanceof Error
              ? error.message
              : "Unable to load the live session."
          );
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
    resetAnalysis();

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
      const result = await startLiveSession(sessionId, {
        camera_permission_granted: true,
        lighting_ready: true,
        framing_ready: true,
        space_ready: true,
        client_ready: true
      });

      setStartResult(result);
      if (!result.started) {
        setActionError(result.message);
        return;
      }

      await videoRef.current?.play();
      setCapturedTicks(0);
      setFrameBatchResult(null);
      setCaptureState("CAPTURING");
      startCaptureClock();
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Unable to start camera capture."
      );
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
    await videoRef.current?.play();
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
      setCaptureState("STOPPED");
      await videoRef.current?.pause();
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setCameraState("idle");
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Unable to stop the camera."
      );
    } finally {
      setIsStopping(false);
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
  const canAnalyze =
    Boolean(artifactSnapshot?.pose_sequence) ||
    captureState === "STOPPED" ||
    (session.input_type === "LIVE" && session.status === "COMPLETED");

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
              Start the camera, control capture, then analyze the session in one flow.
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
          secondaryActionLabel="Start a new upload session"
          helperText="This session was created for live camera. Start a new session if you want to upload a recorded clip."
        />
      </InfoCard>

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <InfoCard className="relative overflow-hidden">
          <SectionTitle
            eyebrow="Input"
            title="Live camera"
            description="Use the same session context while controlling the camera here."
          />

          <div className="mt-6">
            <PoseOverlayPreview
              showVideo={cameraState === "granted" && Boolean(streamRef.current)}
              videoRef={videoRef}
              autoPlay
              muted
              emptyTitle="Camera preview"
              emptyDescription="Start camera to capture movement."
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
            title="Capture state"
            description="Keep the user-facing status simple and clear."
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
                  ? "Start camera to capture movement."
                  : "This session was created for upload video, so live capture is unavailable on this page."}
              </li>
              <li>
                {captureState === "STOPPED"
                  ? "Capture finalized. Analyze Session is now available."
                  : "Stop the camera before running analysis."}
              </li>
              <li>
                {frameBatchResult
                  ? `Accepted frames: ${frameBatchResult.frame_count}`
                  : "No live frame batch submitted yet."}
              </li>
              <li>{startResult?.message ?? "Camera start state has not been confirmed yet."}</li>
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

      <div className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <InfoCard>
          <SectionTitle
            eyebrow="Action"
            title="Analyze session"
            description="Run the full backend pipeline after capture is stopped."
          />

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <CTAButton
              type="button"
              onClick={handleAnalyzeSession}
              disabled={!canAnalyze || analysisState === "RUNNING"}
            >
              {analysisState === "RUNNING" ? "Analyzing session" : "Analyze Session"}
            </CTAButton>
            <Badge variant="slate">
              {captureState === "IDLE"
                ? "Start camera to capture movement"
                : captureState === "STOPPED" || artifactSnapshot?.pose_sequence
                  ? "Ready to analyze"
                  : "Stop the camera before analysis"}
            </Badge>
          </div>
        </InfoCard>

        <AnalysisProgressCard
          analysisError={analysisError}
          analysisState={analysisState}
          analysisSteps={analysisSteps}
        />
      </div>

      <AnalysisSnapshotCard artifacts={artifactSnapshot} />
    </div>
  );
}

export default function LiveSessionPage() {
  const params = useParams<{ sessionId: string }>();

  return (
    <AppShell
      eyebrow="Live Session"
      title="Training input"
      description="Use the camera and analyze the session when capture is done."
      capsule="Input"
      actions={
        <CTAButton asChild>
          <Link href="/sports">Browse Sports</Link>
        </CTAButton>
      }
    >
      {() => <LiveSessionContent sessionId={params.sessionId} />}
    </AppShell>
  );
}

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Camera,
  CameraOff,
  CheckCircle2,
  SignalHigh,
  Square
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
import { formatDateTime, formatEnumLabel } from "../../../../lib/formatters";
import {
  endLiveSession,
  getSession,
  startLiveSession,
  submitLiveFrameBatch
} from "../../../../services/sessions";
import type {
  FrameBatchResponse,
  LiveStartResponse,
  TrainingSession
} from "../../../../types/sessions";

type CameraState = "idle" | "requesting" | "granted" | "denied" | "error";

function LiveSessionContent({ sessionId }: { sessionId: string }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [session, setSession] = useState<TrainingSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [cameraState, setCameraState] = useState<CameraState>("idle");
  const [lightingReady, setLightingReady] = useState(false);
  const [framingReady, setFramingReady] = useState(false);
  const [spaceReady, setSpaceReady] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [startResult, setStartResult] = useState<LiveStartResponse | null>(null);
  const [frameBatchResult, setFrameBatchResult] = useState<FrameBatchResponse | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isSendingBatch, setIsSendingBatch] = useState(false);
  const [isEnding, setIsEnding] = useState(false);

  const clientReady =
    cameraState === "granted" && lightingReady && framingReady && spaceReady;

  useEffect(() => {
    let ignore = false;

    async function loadSession() {
      setLoadError(null);

      try {
        const sessionDetail = await getSession(sessionId);
        if (!ignore) {
          setSession(sessionDetail);
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

    loadSession();

    return () => {
      ignore = true;
    };
  }, [sessionId]);

  useEffect(() => {
    if (videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [cameraState]);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };
  }, []);

  const readinessWarnings = useMemo(
    () => startResult?.readiness.warnings ?? [],
    [startResult]
  );

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
    } catch (error) {
      setCameraState("denied");
      setActionError(
        error instanceof Error
          ? error.message
          : "Camera access was denied."
      );
    }
  }

  async function handleStart() {
    setActionError(null);
    setFrameBatchResult(null);

    try {
      setIsStarting(true);
      const result = await startLiveSession(sessionId, {
        camera_permission_granted: cameraState === "granted",
        lighting_ready: lightingReady,
        framing_ready: framingReady,
        space_ready: spaceReady,
        client_ready: clientReady
      });
      setStartResult(result);
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Unable to start live mode."
      );
    } finally {
      setIsStarting(false);
    }
  }

  async function handleSendFrameBatch() {
    setActionError(null);

    try {
      setIsSendingBatch(true);
      const timestamps = Array.from({ length: 30 }, (_, index) =>
        Number((index / 30).toFixed(3))
      );
      const result = await submitLiveFrameBatch(sessionId, {
        frame_count: timestamps.length,
        timestamps,
        client_ready: true
      });
      setFrameBatchResult(result);
    } catch (error) {
      setActionError(
        error instanceof Error
          ? error.message
          : "Unable to send the session check."
      );
    } finally {
      setIsSendingBatch(false);
    }
  }

  async function handleEnd(finalStatus: "COMPLETED" | "ABORTED") {
    setActionError(null);

    try {
      setIsEnding(true);
      const updatedSession = await endLiveSession(sessionId, { final_status: finalStatus });
      setSession(updatedSession);
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setCameraState("idle");
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Unable to end the live session."
      );
    } finally {
      setIsEnding(false);
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader className="h-64" />
        <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
          <SkeletonLoader className="h-[520px]" />
          <SkeletonLoader className="h-[520px]" />
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

  if (session.input_type !== "LIVE") {
    return (
      <EmptyState
        icon={CameraOff}
        title="This session is not in live mode"
        description="Open the upload page for this session, or start a new live setup for the same drill."
        action={
          <CTAButton asChild>
            <Link href={`/sessions/${session.id}/upload`}>Open Upload Page</Link>
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
              Check framing. Start when ready.
            </p>
          </div>

          <div className="grid gap-3 xl:min-w-[340px]">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Session Started
              </p>
              <p className="mt-3 text-sm font-semibold text-white">
                {formatDateTime(session.start_time)}
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <CTAButton
                type="button"
                onClick={handleStart}
                disabled={!clientReady || isStarting || session.status !== "ACTIVE"}
                className="flex-1 justify-center rounded-2xl"
              >
                {isStarting ? "Starting" : "Start"}
              </CTAButton>
              <Button
                type="button"
                variant="outline"
                className="rounded-2xl px-4"
                onClick={() => handleEnd("COMPLETED")}
                disabled={isEnding || session.status !== "ACTIVE"}
              >
                <Square className="mr-2 h-4 w-4" />
                End
              </Button>
            </div>
            <Button
              asChild
              variant="outline"
              className="justify-between rounded-2xl px-5 py-6 text-white/90"
            >
              <Link href={`/sessions/new?drillId=${session.drill_id}&mode=UPLOAD`}>
                <span>Switch to upload video</span>
                <Badge variant="slate">New session</Badge>
              </Link>
            </Button>
            <p className="text-sm text-muted-gray">
              Input mode is fixed per session. This starts an upload setup for the same drill.
            </p>
          </div>
        </div>
      </InfoCard>

      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <InfoCard className="relative overflow-hidden">
          <SectionTitle
            eyebrow="Live"
            title="Camera Preview"
            description="Keep the athlete in frame."
          />

          <div className="mt-6 overflow-hidden rounded-[1.75rem] border border-white/10 bg-slate/40">
            {cameraState === "granted" && streamRef.current ? (
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                className="aspect-video w-full bg-black object-cover"
              />
            ) : (
              <div className="flex aspect-video w-full flex-col items-center justify-center bg-[radial-gradient(circle_at_center,_rgba(255,122,0,0.12),_transparent_45%),linear-gradient(180deg,rgba(17,17,17,0.86),rgba(31,31,31,0.92))] px-8 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-3xl border border-primary/20 bg-primary/10 text-primary">
                  <Camera className="h-7 w-7" />
                </div>
                <h3 className="mt-5 font-display text-3xl font-bold text-white">
                  Camera preview
                </h3>
                <p className="mt-4 max-w-xl text-sm text-muted-gray">
                  Enable camera to preview framing.
                </p>
              </div>
            )}
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <Button
              type="button"
              variant="outline"
              className="rounded-2xl"
              onClick={requestCameraPreview}
              disabled={cameraState === "requesting" || session.status !== "ACTIVE"}
            >
              <Camera className="mr-2 h-4 w-4" />
              {cameraState === "requesting"
                ? "Opening"
                : cameraState === "granted"
                  ? "Refresh"
                  : "Enable Camera"}
            </Button>
            <Button
              type="button"
              variant="outline"
              className="rounded-2xl"
              onClick={handleSendFrameBatch}
              disabled={
                !startResult?.started ||
                isSendingBatch ||
                session.status !== "ACTIVE"
              }
            >
              <SignalHigh className="mr-2 h-4 w-4" />
              {isSendingBatch ? "Sending" : "Send Check"}
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="rounded-2xl border border-white/10 bg-white/[0.03]"
              onClick={() => handleEnd("ABORTED")}
              disabled={isEnding || session.status !== "ACTIVE"}
            >
              Abort
            </Button>
          </div>
        </InfoCard>

        <div className="space-y-5">
          <InfoCard>
            <SectionTitle
              eyebrow="Readiness"
              title="Session Checks"
              description="Confirm each item."
            />

            <div className="mt-6 space-y-4">
              <label className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
                <input
                  type="checkbox"
                  checked={lightingReady}
                  onChange={(event) => setLightingReady(event.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-white/20 bg-transparent text-primary"
                />
                <div>
                  <p className="text-sm font-semibold text-white">Lighting ready</p>
                </div>
              </label>

              <label className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
                <input
                  type="checkbox"
                  checked={framingReady}
                  onChange={(event) => setFramingReady(event.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-white/20 bg-transparent text-primary"
                />
                <div>
                  <p className="text-sm font-semibold text-white">Framing ready</p>
                  {session.camera_view ? (
                    <p className="mt-1 text-sm text-muted-gray">
                      Match the {formatEnumLabel(session.camera_view).toLowerCase()} view.
                    </p>
                  ) : null}
                </div>
              </label>

              <label className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
                <input
                  type="checkbox"
                  checked={spaceReady}
                  onChange={(event) => setSpaceReady(event.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-white/20 bg-transparent text-primary"
                />
                <div>
                  <p className="text-sm font-semibold text-white">Space ready</p>
                </div>
              </label>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
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
              <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                  Client Ready
                </p>
                <p className="mt-3 text-sm font-semibold text-white">
                  {clientReady ? "Ready" : "Not ready"}
                </p>
              </div>
            </div>

            {readinessWarnings.length ? (
              <div className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-amber-200">
                  Warnings
                </p>
                <ul className="mt-3 space-y-2 text-sm leading-7 text-amber-100">
                  {readinessWarnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </InfoCard>

          <InfoCard>
            <SectionTitle
              eyebrow="Status"
              title="Session State"
              description="Live review is not active yet."
            />

            {actionError ? (
              <div className="mt-6 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-4 text-sm leading-7 text-rose-100">
                {actionError}
              </div>
            ) : null}

            {startResult ? (
              <div className="mt-6 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-4">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-200" />
                  <p className="text-sm font-semibold text-white">Session started</p>
                </div>
              </div>
            ) : (
              <p className="mt-6 text-sm text-muted-gray">
                Check camera. Start session.
              </p>
            )}

            {frameBatchResult ? (
              <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                  Check
                </p>
                <p className="mt-3 text-sm font-semibold text-white">
                  Check received
                </p>
                <p className="mt-2 text-sm text-muted-gray">
                  Accepted frames: {frameBatchResult.frame_count}
                </p>
              </div>
            ) : null}

            <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Next
              </p>
              <ul className="mt-3 space-y-2 text-sm text-white/85">
                <li>• Live review</li>
                <li>• Instant scoring</li>
                <li>• Voice cues</li>
              </ul>
            </div>
          </InfoCard>
        </div>
      </div>
    </div>
  );
}

export default function LiveSessionPage() {
  const params = useParams<{ sessionId: string }>();

  return (
    <AppShell
      eyebrow="Live Session"
      title="Start live training"
      description="Open camera and begin."
      capsule="Live"
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

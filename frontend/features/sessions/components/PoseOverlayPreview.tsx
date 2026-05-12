"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { MutableRefObject } from "react";
import type { NormalizedLandmark, PoseLandmarker } from "@mediapipe/tasks-vision";
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  Loader2,
  Maximize2,
  Pause,
  PlayCircle
} from "lucide-react";

import { cn } from "../../../lib/utils";
import type { PoseSequence } from "../../../types/sessions";
import {
  clearPoseCanvas,
  drawPoseDebugMarker,
  drawPoseSkeleton,
  findClosestPoseFrame,
  getContainedVideoRenderBox,
  getPoseFrameToleranceMs,
  getValidPoseFrames,
  normalizeLandmarkArray,
  resizeCanvasToVideo
} from "../utils/pose-overlay";

type PoseOverlayMode = "upload" | "live";

type PoseOverlayPreviewProps = {
  mode: PoseOverlayMode;
  videoSrc?: string | null;
  stream?: MediaStream | null;
  poseSequence?: PoseSequence | null;
  videoRef?: MutableRefObject<HTMLVideoElement | null>;
  isActive?: boolean;
  isPaused?: boolean;
  mirrored?: boolean;
  autoPlay?: boolean;
  controls?: boolean;
  muted?: boolean;
  emptyTitle: string;
  emptyDescription: string;
  statusText?: string;
  debugOverlay?: boolean;
  className?: string;
};

type OverlayTone = "idle" | "running" | "success" | "warning" | "error";

const MEDIAPIPE_WASM_PATH = "/mediapipe/tasks-vision/wasm";
const POSE_MODEL_PATH = "/mediapipe/models/pose_landmarker_lite.task";
const POSE_WASM_CHECK_PATH = `${MEDIAPIPE_WASM_PATH}/vision_wasm_internal.wasm`;
const LIVE_DETECTION_INTERVAL_MS = 90;

function formatVideoTime(value: number) {
  if (!Number.isFinite(value) || value <= 0) {
    return "0:00";
  }

  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60)
    .toString()
    .padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function getStatusTone(status: string): OverlayTone {
  if (/failed|unavailable|denied|error/i.test(status)) {
    return "error";
  }

  if (/no pose|full body not detected|move into|missing|no pose frame|process a video/i.test(status)) {
    return "warning";
  }

  if (/ready|active|detected|running/i.test(status)) {
    return "success";
  }

  if (/loading|initializing|detecting/i.test(status)) {
    return "running";
  }

  return "idle";
}

function StatusIcon({ tone }: { tone: OverlayTone }) {
  if (tone === "running") {
    return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
  }

  if (tone === "success") {
    return <CheckCircle2 className="h-4 w-4 text-emerald-300" />;
  }

  if (tone === "warning" || tone === "error") {
    return <AlertTriangle className="h-4 w-4 text-amber-300" />;
  }

  return <PlayCircle className="h-4 w-4 text-primary" />;
}

function getUploadStatus({
  hasVideo,
  poseSequence
}: {
  hasVideo: boolean;
  poseSequence?: PoseSequence | null;
}) {
  if (!hasVideo) {
    return "Upload and process a video to view the pose overlay.";
  }

  if (!poseSequence) {
    return "Upload and process a video to view the pose overlay.";
  }

  if (poseSequence.status === "FAILED") {
    return "Pose extraction failed, so the pose overlay is unavailable.";
  }

  if (poseSequence.status === "INSUFFICIENT_DATA") {
    return "Pose extraction did not find enough valid frames for an overlay.";
  }

  if (poseSequence.frame_count <= 0 || poseSequence.valid_frame_count <= 0) {
    return "Pose extraction did not produce drawable frames.";
  }

  return "Pose overlay active";
}

async function createLivePoseLandmarker() {
  const { FilesetResolver, PoseLandmarker } = await import(
    "@mediapipe/tasks-vision"
  );
  const vision = await FilesetResolver.forVisionTasks(MEDIAPIPE_WASM_PATH);

  return PoseLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: POSE_MODEL_PATH,
      delegate: "CPU"
    },
    runningMode: "VIDEO",
    numPoses: 1,
    minPoseDetectionConfidence: 0.5,
    minPosePresenceConfidence: 0.5,
    minTrackingConfidence: 0.5
  });
}

async function assertMediaPipeAssetsAvailable() {
  const [modelResponse, wasmResponse] = await Promise.all([
    fetch(POSE_MODEL_PATH, { cache: "force-cache", method: "HEAD" }),
    fetch(POSE_WASM_CHECK_PATH, { cache: "force-cache", method: "HEAD" })
  ]);

  if (!modelResponse.ok) {
    throw new Error(`pose model request failed (${modelResponse.status})`);
  }

  if (!wasmResponse.ok) {
    throw new Error(`pose wasm request failed (${wasmResponse.status})`);
  }
}

function waitForVideoReady(video: HTMLVideoElement) {
  if (video.readyState >= 2) {
    return Promise.resolve();
  }

  return new Promise<void>((resolve, reject) => {
    const timeoutId = window.setTimeout(() => {
      cleanup();
      reject(new Error("camera video did not become ready"));
    }, 6000);

    function cleanup() {
      window.clearTimeout(timeoutId);
      video.removeEventListener("loadedmetadata", handleReady);
      video.removeEventListener("canplay", handleReady);
      video.removeEventListener("playing", handleReady);
      video.removeEventListener("error", handleError);
    }

    function handleReady() {
      if (video.readyState >= 2) {
        cleanup();
        resolve();
      }
    }

    function handleError() {
      cleanup();
      reject(new Error("camera video failed to load"));
    }

    video.addEventListener("loadedmetadata", handleReady);
    video.addEventListener("canplay", handleReady);
    video.addEventListener("playing", handleReady);
    video.addEventListener("error", handleError);
  });
}

export function PoseOverlayPreview({
  mode,
  videoSrc,
  stream,
  poseSequence,
  videoRef,
  isActive = true,
  isPaused = false,
  mirrored = false,
  autoPlay = false,
  controls = false,
  muted = false,
  emptyTitle,
  emptyDescription,
  statusText,
  debugOverlay = true,
  className
}: PoseOverlayPreviewProps) {
  const internalVideoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const detectorRef = useRef<PoseLandmarker | null>(null);
  const liveAnimationRef = useRef<number | null>(null);
  const uploadAnimationRef = useRef<number | null>(null);
  const lastLiveDetectionRef = useRef(0);
  const hasLoggedLiveDimensionsRef = useRef(false);
  const [overlayStatus, setOverlayStatus] = useState(
    statusText ??
      (mode === "live"
        ? "Camera active - pose overlay running"
        : "Upload and process a video to view the pose overlay.")
  );
  const [isVideoPlaying, setIsVideoPlaying] = useState(false);
  const [videoCurrentTime, setVideoCurrentTime] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);

  const hasVideo = mode === "live" ? Boolean(stream && isActive) : Boolean(videoSrc);
  const forceMutedPreview = mode === "upload";
  const effectiveMuted = forceMutedPreview || muted;
  const validUploadFrames = useMemo(
    () => getValidPoseFrames(poseSequence),
    [poseSequence]
  );
  const uploadFrameToleranceMs = useMemo(
    () => getPoseFrameToleranceMs(validUploadFrames),
    [validUploadFrames]
  );
  const statusTone = getStatusTone(overlayStatus);

  function cancelLiveAnimationFrame() {
    if (liveAnimationRef.current !== null) {
      window.cancelAnimationFrame(liveAnimationRef.current);
      liveAnimationRef.current = null;
    }
  }

  useEffect(() => {
    setOverlayStatus(
      statusText ??
        (mode === "live"
          ? isPaused
            ? "Camera paused - pose overlay paused"
            : hasVideo
              ? "Camera active - pose overlay running"
              : "Start the camera to run the pose overlay."
          : getUploadStatus({ hasVideo, poseSequence }))
    );
  }, [hasVideo, isPaused, mode, poseSequence, statusText]);

  useEffect(() => {
    if (mode !== "upload") {
      return;
    }

    const video = internalVideoRef.current;
    if (!video) {
      return;
    }

    const videoElement = video;

    function keepPreviewMuted() {
      if (!forceMutedPreview) {
        return;
      }
      if (!videoElement.muted) {
        videoElement.muted = true;
      }
      if (videoElement.volume !== 0) {
        videoElement.volume = 0;
      }
    }

    function handleLoadedMetadata() {
      setVideoDuration(
        Number.isFinite(videoElement.duration) ? videoElement.duration : 0
      );
      setVideoCurrentTime(videoElement.currentTime);
      keepPreviewMuted();
    }

    function handleTimeUpdate() {
      setVideoCurrentTime(videoElement.currentTime);
    }

    function handlePlay() {
      setIsVideoPlaying(true);
      keepPreviewMuted();
    }

    function handlePause() {
      setIsVideoPlaying(false);
    }

    videoElement.defaultMuted = forceMutedPreview;
    keepPreviewMuted();
    setIsVideoPlaying(!videoElement.paused);
    setVideoDuration(
      Number.isFinite(videoElement.duration) ? videoElement.duration : 0
    );
    setVideoCurrentTime(videoElement.currentTime);

    videoElement.addEventListener("loadedmetadata", handleLoadedMetadata);
    videoElement.addEventListener("durationchange", handleLoadedMetadata);
    videoElement.addEventListener("timeupdate", handleTimeUpdate);
    videoElement.addEventListener("play", handlePlay);
    videoElement.addEventListener("pause", handlePause);
    videoElement.addEventListener("ended", handlePause);
    videoElement.addEventListener("volumechange", keepPreviewMuted);

    return () => {
      videoElement.removeEventListener("loadedmetadata", handleLoadedMetadata);
      videoElement.removeEventListener("durationchange", handleLoadedMetadata);
      videoElement.removeEventListener("timeupdate", handleTimeUpdate);
      videoElement.removeEventListener("play", handlePlay);
      videoElement.removeEventListener("pause", handlePause);
      videoElement.removeEventListener("ended", handlePause);
      videoElement.removeEventListener("volumechange", keepPreviewMuted);
    };
  }, [forceMutedPreview, mode, videoSrc]);

  useEffect(() => {
    const video = internalVideoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas) {
      return;
    }

    const videoElement = video;
    const canvasElement = canvas;

    function syncCanvasSize() {
      resizeCanvasToVideo(videoElement, canvasElement);
    }

    syncCanvasSize();
    videoElement.addEventListener("loadedmetadata", syncCanvasSize);
    window.addEventListener("resize", syncCanvasSize);

    return () => {
      videoElement.removeEventListener("loadedmetadata", syncCanvasSize);
      window.removeEventListener("resize", syncCanvasSize);
    };
  }, [hasVideo, mode, videoSrc]);

  useEffect(() => {
    const video = internalVideoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas || mode !== "live") {
      return;
    }

    const videoElement = video;
    const canvasElement = canvas;

    const activeStream = stream && isActive ? stream : null;

    if (activeStream) {
      if (videoElement.srcObject !== activeStream) {
        cancelLiveAnimationFrame();
        videoElement.srcObject = activeStream;
      }
    } else {
      cancelLiveAnimationFrame();
      if (videoElement.srcObject) {
        videoElement.srcObject = null;
      }
      clearPoseCanvas(canvasElement);
    }

    return () => {
      if (
        mode === "live" &&
        activeStream &&
        videoElement.srcObject === activeStream
      ) {
        cancelLiveAnimationFrame();
        videoElement.srcObject = null;
      }
    };
  }, [isActive, mode, stream]);

  useEffect(() => {
    if (mode !== "upload") {
      return;
    }

    const video = internalVideoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas) {
      return;
    }

    const videoElement = video;
    const canvasElement = canvas;
    let disposed = false;

    function cancelUploadLoop() {
      if (uploadAnimationRef.current !== null) {
        window.cancelAnimationFrame(uploadAnimationRef.current);
        uploadAnimationRef.current = null;
      }
    }

    function drawCurrentUploadFrame() {
      if (disposed) {
        return;
      }

      resizeCanvasToVideo(videoElement, canvasElement);

      const baseStatus = getUploadStatus({ hasVideo, poseSequence });
      if (!hasVideo || baseStatus !== "Pose overlay active") {
        clearPoseCanvas(canvasElement);
        setOverlayStatus(baseStatus);
        return;
      }

      const poseFrame = findClosestPoseFrame(
        validUploadFrames,
        videoElement.currentTime * 1000,
        uploadFrameToleranceMs
      );

      if (!poseFrame) {
        clearPoseCanvas(canvasElement);
        setOverlayStatus("No pose frame available for this timestamp.");
        return;
      }

      const result = drawPoseSkeleton({
        canvas: canvasElement,
        landmarks: poseFrame.landmarks,
        mirrored,
        renderBox: getContainedVideoRenderBox(videoElement, canvasElement)
      });

      setOverlayStatus(
        result.visibleLandmarks > 0
          ? "Pose overlay active"
          : "No pose frame available for this timestamp."
      );
    }

    function runUploadLoop() {
      drawCurrentUploadFrame();
      if (!videoElement.paused && !videoElement.ended) {
        uploadAnimationRef.current = window.requestAnimationFrame(runUploadLoop);
      }
    }

    function handlePlay() {
      cancelUploadLoop();
      runUploadLoop();
    }

    function handlePauseOrSeek() {
      cancelUploadLoop();
      drawCurrentUploadFrame();
    }

    videoElement.addEventListener("loadedmetadata", drawCurrentUploadFrame);
    videoElement.addEventListener("timeupdate", drawCurrentUploadFrame);
    videoElement.addEventListener("seeked", drawCurrentUploadFrame);
    videoElement.addEventListener("play", handlePlay);
    videoElement.addEventListener("pause", handlePauseOrSeek);
    window.addEventListener("resize", drawCurrentUploadFrame);
    drawCurrentUploadFrame();

    return () => {
      disposed = true;
      cancelUploadLoop();
      videoElement.removeEventListener("loadedmetadata", drawCurrentUploadFrame);
      videoElement.removeEventListener("timeupdate", drawCurrentUploadFrame);
      videoElement.removeEventListener("seeked", drawCurrentUploadFrame);
      videoElement.removeEventListener("play", handlePlay);
      videoElement.removeEventListener("pause", handlePauseOrSeek);
      window.removeEventListener("resize", drawCurrentUploadFrame);
    };
  }, [
    hasVideo,
    mirrored,
    mode,
    poseSequence,
    uploadFrameToleranceMs,
    validUploadFrames
  ]);

  useEffect(() => {
    if (mode !== "live") {
      return;
    }

    const video = internalVideoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas) {
      return;
    }

    const videoElement = video;
    const canvasElement = canvas;
    let disposed = false;

    function cancelLiveLoop() {
      if (liveAnimationRef.current !== null) {
        window.cancelAnimationFrame(liveAnimationRef.current);
        liveAnimationRef.current = null;
      }
    }

    async function startLiveDetectorLoop() {
      if (!stream || !isActive) {
        cancelLiveLoop();
        clearPoseCanvas(canvasElement);
        detectorRef.current?.close();
        detectorRef.current = null;
        setOverlayStatus("Start the camera to run the pose overlay.");
        return;
      }

      if (isPaused) {
        cancelLiveLoop();
        setOverlayStatus("Camera paused - pose overlay paused");
        return;
      }

      try {
        setOverlayStatus("Loading pose detector");
        if (videoElement.srcObject !== stream) {
          videoElement.srcObject = stream;
        }
        resizeCanvasToVideo(videoElement, canvasElement);
        clearPoseCanvas(canvasElement);
        if (debugOverlay) {
          drawPoseDebugMarker(canvasElement);
        }

        await assertMediaPipeAssetsAvailable();
        if (disposed) {
          return;
        }

        await waitForVideoReady(videoElement);
        if (disposed) {
          return;
        }

        setOverlayStatus("Pose detector ready");
        if (!hasLoggedLiveDimensionsRef.current && debugOverlay) {
          hasLoggedLiveDimensionsRef.current = true;
          console.info("TrainUp live pose overlay dimensions", {
            canvasWidth: canvasElement.width,
            canvasHeight: canvasElement.height,
            videoWidth: videoElement.videoWidth,
            videoHeight: videoElement.videoHeight
          });
        }
        const createdDetector = detectorRef.current
          ? null
          : await createLivePoseLandmarker();
        const detector = detectorRef.current ?? createdDetector;
        if (!detector) {
          throw new Error("Pose detector failed to initialize.");
        }
        if (disposed) {
          createdDetector?.close();
          return;
        }

        detectorRef.current = detector;
        const activeDetector = detector;
        setOverlayStatus("Detecting movement");

        function runLiveLoop(timestamp: number) {
          if (disposed || !stream || !isActive || isPaused) {
            return;
          }

          resizeCanvasToVideo(videoElement, canvasElement);

          if (
            videoElement.readyState >= 2 &&
            timestamp - lastLiveDetectionRef.current >= LIVE_DETECTION_INTERVAL_MS
          ) {
            lastLiveDetectionRef.current = timestamp;
            const result = activeDetector.detectForVideo(videoElement, timestamp);
            const landmarks = result.landmarks[0] as NormalizedLandmark[] | undefined;

            if (landmarks?.length) {
              const drawResult = drawPoseSkeleton({
                canvas: canvasElement,
                landmarks: normalizeLandmarkArray(landmarks),
                mirrored,
                renderBox: getContainedVideoRenderBox(videoElement, canvasElement)
              });

              setOverlayStatus(
                drawResult.visibleLandmarks === 0
                  ? "No pose detected"
                  : drawResult.fullBodyDetected
                  ? "Pose detected"
                  : "Full body not detected - step back for complete analysis."
              );
              if (debugOverlay) {
                drawPoseDebugMarker(canvasElement);
              }
            } else {
              clearPoseCanvas(canvasElement);
              if (debugOverlay) {
                drawPoseDebugMarker(canvasElement);
              }
              setOverlayStatus("No pose detected");
            }
          }

          liveAnimationRef.current = window.requestAnimationFrame(runLiveLoop);
        }

        cancelLiveLoop();
        liveAnimationRef.current = window.requestAnimationFrame(runLiveLoop);
      } catch (error) {
        clearPoseCanvas(canvasElement);
        if (debugOverlay) {
          drawPoseDebugMarker(canvasElement);
        }
        setOverlayStatus(
          error instanceof Error
            ? `Detector failed: ${error.message}`
            : "Detector failed: unknown error"
        );
      }
    }

    startLiveDetectorLoop();

    return () => {
      disposed = true;
      cancelLiveLoop();
    };
  }, [debugOverlay, isActive, isPaused, mirrored, mode, stream]);

  useEffect(() => {
    return () => {
      if (liveAnimationRef.current !== null) {
        window.cancelAnimationFrame(liveAnimationRef.current);
      }
      if (uploadAnimationRef.current !== null) {
        window.cancelAnimationFrame(uploadAnimationRef.current);
      }
      detectorRef.current?.close();
      detectorRef.current = null;
    };
  }, []);

  async function handleToggleUploadPlayback() {
    const video = internalVideoRef.current;
    if (!video || mode !== "upload") {
      return;
    }

    video.muted = true;
    video.defaultMuted = true;
    video.volume = 0;

    if (video.paused) {
      try {
        await video.play();
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
      }
      return;
    }

    video.pause();
  }

  function handleUploadSeek(value: string) {
    const video = internalVideoRef.current;
    const nextTime = Number(value);
    if (!video || !Number.isFinite(nextTime)) {
      return;
    }

    video.currentTime = nextTime;
    setVideoCurrentTime(nextTime);
  }

  async function handleFullscreen() {
    const video = internalVideoRef.current;
    const container = video?.parentElement;
    if (!container?.requestFullscreen) {
      return;
    }

    try {
      await container.requestFullscreen();
    } catch {
      // Fullscreen is optional and may be blocked by the browser.
    }
  }

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[1.75rem] border border-white/10 bg-slate/40",
        className
      )}
    >
      <div
        className={cn(
          "relative w-full",
          mode === "live" ? "aspect-[4/3] min-h-[420px] lg:min-h-[560px]" : "aspect-video"
        )}
      >
        <video
          ref={(node) => {
            internalVideoRef.current = node;
            if (videoRef) {
              videoRef.current = node;
            }
          }}
          autoPlay={mode === "upload" && hasVideo ? autoPlay : false}
          controls={false}
          muted={effectiveMuted}
          playsInline
          src={mode === "upload" && hasVideo ? videoSrc ?? undefined : undefined}
          className={cn(
            "h-full w-full bg-black object-contain",
            mirrored ? "scale-x-[-1]" : null
          )}
        />
        <canvas
          className="pointer-events-none absolute inset-0 h-full w-full"
          ref={canvasRef}
        />
        <div className="pointer-events-none absolute left-4 top-4 rounded-full border border-white/12 bg-background-dark/75 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-white/80 backdrop-blur">
          {mode === "live" ? "Live pose overlay" : "Uploaded pose overlay"}
        </div>
        {!hasVideo ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[radial-gradient(circle_at_center,_rgba(255,122,0,0.09),_transparent_46%),linear-gradient(180deg,rgba(17,17,17,0.72),rgba(24,24,24,0.9))] px-7 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-3xl border border-primary/18 bg-primary/10 text-primary shadow-[0_16px_44px_rgba(255,122,0,0.08)]">
              <Camera className="h-6 w-6" />
            </div>
            <h3 className="mt-4 font-display text-2xl font-bold text-white">
              {emptyTitle}
            </h3>
            <p className="mt-2 max-w-md text-sm leading-6 text-muted-gray">
              {emptyDescription}
            </p>
            <p className="mt-4 text-[10px] uppercase tracking-[0.22em] text-white/40">
              {overlayStatus}
            </p>
          </div>
        ) : null}
      </div>
      {hasVideo ? (
        <div className="border-t border-white/10 bg-background-dark/72 px-4 py-3 backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2 text-sm text-white/85">
              <StatusIcon tone={statusTone} />
              <span className="min-w-0 break-words">{overlayStatus}</span>
            </div>
            {mode === "upload" ? (
              <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/45">
                Muted visual preview
              </span>
            ) : null}
          </div>

          {mode === "upload" && controls ? (
            <div className="mt-3 flex items-center gap-3 rounded-2xl border border-white/10 bg-black/24 px-3 py-2">
              <button
                type="button"
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-primary/25 bg-primary text-background-dark transition hover:bg-primary/90"
                onClick={() => {
                  void handleToggleUploadPlayback();
                }}
                aria-label={isVideoPlaying ? "Pause preview" : "Play preview"}
              >
                {isVideoPlaying ? (
                  <Pause className="h-4 w-4" />
                ) : (
                  <PlayCircle className="h-4 w-4" />
                )}
              </button>
              <span className="w-10 text-right text-[11px] tabular-nums text-white/55">
                {formatVideoTime(videoCurrentTime)}
              </span>
              <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-primary transition-[width] duration-150"
                  style={{
                    width:
                      videoDuration > 0
                        ? `${Math.min(100, (videoCurrentTime / videoDuration) * 100)}%`
                        : "0%"
                  }}
                />
                <input
                  aria-label="Preview progress"
                  className="absolute inset-0 h-full w-full cursor-pointer opacity-0 disabled:cursor-default"
                  disabled={videoDuration <= 0}
                  max={videoDuration || 0}
                  min={0}
                  step={0.1}
                  type="range"
                  value={Math.min(videoCurrentTime, videoDuration || 0)}
                  onChange={(event) => {
                    handleUploadSeek(event.target.value);
                  }}
                />
              </div>
              <span className="w-10 text-[11px] tabular-nums text-white/55">
                {formatVideoTime(videoDuration)}
              </span>
              <button
                type="button"
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-white/70 transition hover:border-primary/25 hover:text-white"
                onClick={() => {
                  void handleFullscreen();
                }}
                aria-label="Open preview fullscreen"
              >
                <Maximize2 className="h-4 w-4" />
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

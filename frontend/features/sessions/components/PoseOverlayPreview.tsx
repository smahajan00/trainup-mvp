"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { MutableRefObject } from "react";
import type { NormalizedLandmark, PoseLandmarker } from "@mediapipe/tasks-vision";
import { AlertTriangle, Camera, CheckCircle2, Loader2, PlayCircle } from "lucide-react";

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
    return "Upload and process a video to view skeleton overlay.";
  }

  if (!poseSequence) {
    return "Upload and process a video to view skeleton overlay.";
  }

  if (poseSequence.status === "FAILED") {
    return "Pose extraction failed, so the skeleton overlay is unavailable.";
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
        ? "Camera active - skeleton overlay running"
        : "Upload and process a video to view skeleton overlay.")
  );

  const hasVideo = mode === "live" ? Boolean(stream && isActive) : Boolean(videoSrc);
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
            ? "Camera paused - skeleton overlay paused"
            : hasVideo
              ? "Camera active - skeleton overlay running"
              : "Start the camera to run the skeleton overlay."
          : getUploadStatus({ hasVideo, poseSequence }))
    );
  }, [hasVideo, isPaused, mode, poseSequence, statusText]);

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
        setOverlayStatus("Start the camera to run the skeleton overlay.");
        return;
      }

      if (isPaused) {
        cancelLiveLoop();
        setOverlayStatus("Camera paused - skeleton overlay paused");
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
          controls={hasVideo && mode === "upload" ? controls : false}
          muted={muted}
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
          {mode === "live" ? "Live skeleton overlay" : "Uploaded pose overlay"}
        </div>
        {hasVideo ? (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-background-dark/90 to-transparent px-5 py-4">
            <div className="flex items-center gap-2 text-sm text-white/85">
              <StatusIcon tone={statusTone} />
              <span>{overlayStatus}</span>
            </div>
          </div>
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[radial-gradient(circle_at_center,_rgba(255,122,0,0.12),_transparent_45%),linear-gradient(180deg,rgba(17,17,17,0.6),rgba(31,31,31,0.78))] px-8 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-3xl border border-primary/20 bg-primary/10 text-primary">
              <Camera className="h-7 w-7" />
            </div>
            <h3 className="mt-5 font-display text-3xl font-bold text-white">
              {emptyTitle}
            </h3>
            <p className="mt-4 max-w-xl text-sm text-muted-gray">
              {emptyDescription}
            </p>
            <p className="mt-4 text-xs uppercase tracking-[0.24em] text-white/45">
              {overlayStatus}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

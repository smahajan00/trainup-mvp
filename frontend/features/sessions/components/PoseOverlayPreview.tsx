import { useEffect, useRef } from "react";
import type { MutableRefObject } from "react";
import { Camera, PlayCircle } from "lucide-react";

import { cn } from "../../../lib/utils";

type PoseOverlayPreviewProps = {
  showVideo: boolean;
  videoSrc?: string | null;
  videoRef?: MutableRefObject<HTMLVideoElement | null>;
  autoPlay?: boolean;
  controls?: boolean;
  muted?: boolean;
  emptyTitle: string;
  emptyDescription: string;
  overlayMessage?: string;
  className?: string;
};

export function PoseOverlayPreview({
  showVideo,
  videoSrc,
  videoRef,
  autoPlay = false,
  controls = false,
  muted = false,
  emptyTitle,
  emptyDescription,
  overlayMessage = "Pose overlay preview will light up here during analysis",
  className
}: PoseOverlayPreviewProps) {
  const internalVideoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const video = internalVideoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas) {
      return;
    }

    const videoElement = video;
    const canvasElement = canvas;

    function syncCanvasSize() {
      canvasElement.width =
        videoElement.videoWidth || videoElement.clientWidth || 1280;
      canvasElement.height =
        videoElement.videoHeight || videoElement.clientHeight || 720;
    }

    syncCanvasSize();
    videoElement.addEventListener("loadedmetadata", syncCanvasSize);
    window.addEventListener("resize", syncCanvasSize);

    return () => {
      videoElement.removeEventListener("loadedmetadata", syncCanvasSize);
      window.removeEventListener("resize", syncCanvasSize);
    };
  }, [showVideo, videoSrc]);

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[1.75rem] border border-white/10 bg-slate/40",
        className
      )}
    >
      {showVideo ? (
        <div className="relative aspect-video w-full">
          <video
            ref={(node) => {
              internalVideoRef.current = node;
              if (videoRef) {
                videoRef.current = node;
              }
            }}
            autoPlay={autoPlay}
            controls={controls}
            muted={muted}
            playsInline
            src={videoSrc ?? undefined}
            className="aspect-video h-full w-full bg-black object-cover"
          />
          <canvas className="overlay pointer-events-none absolute inset-0 h-full w-full" ref={canvasRef} />
          <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-background-dark/90 to-transparent px-5 py-4">
            <div className="flex items-center gap-2 text-sm text-white/85">
              <PlayCircle className="h-4 w-4 text-primary" />
              <span>{overlayMessage}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex aspect-video w-full flex-col items-center justify-center bg-[radial-gradient(circle_at_center,_rgba(255,122,0,0.12),_transparent_45%),linear-gradient(180deg,rgba(17,17,17,0.86),rgba(31,31,31,0.92))] px-8 text-center">
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
            Overlay-ready preview surface
          </p>
        </div>
      )}
    </div>
  );
}

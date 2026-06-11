"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Camera,
  ListChecks,
  Maximize2,
  Pause,
  Play,
  PlayCircle,
  Sparkles,
  Target,
  UploadCloud
} from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { CTAButton } from "../../../components/ui/cta-button";
import { SkeletonLoader } from "../../../components/ui/skeleton-loader";
import { AppShell } from "../../../features/app-shell/components/AppShell";
import { EmptyState } from "../../../features/app-shell/components/EmptyState";
import { InfoCard } from "../../../features/app-shell/components/InfoCard";
import { SectionTitle } from "../../../features/app-shell/components/SectionTitle";
import {
  formatEnumLabel,
  formatTokenLabel,
  truncateText
} from "../../../lib/formatters";
import { getMetricDescription } from "../../../lib/metric-descriptions";
import { useStartSessionFromDrill } from "../../../features/sessions/hooks/useStartSessionFromDrill";
import { getDrillById } from "../../../services/drills";
import type { DrillDetail } from "../../../types/drills";
import type { ProfileResponse } from "../../../types/profile";

function formatDemoTime(value: number) {
  if (!Number.isFinite(value) || value <= 0) {
    return "0:00";
  }

  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60)
    .toString()
    .padStart(2, "0");

  return `${minutes}:${seconds}`;
}

function DrillDemoVideo({ src }: { src: string }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    const keepVideoMuted = () => {
      video.muted = true;
      video.defaultMuted = true;
      video.volume = 0;
    };

    const handleMetadata = () => {
      keepVideoMuted();
      setDuration(Number.isFinite(video.duration) ? video.duration : 0);
    };
    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
    };
    const handlePlay = () => {
      keepVideoMuted();
      setIsPlaying(true);
    };
    const handlePause = () => {
      setIsPlaying(false);
    };

    keepVideoMuted();
    video.addEventListener("loadedmetadata", handleMetadata);
    video.addEventListener("timeupdate", handleTimeUpdate);
    video.addEventListener("play", handlePlay);
    video.addEventListener("pause", handlePause);
    video.addEventListener("ended", handlePause);
    video.addEventListener("volumechange", keepVideoMuted);

    return () => {
      video.removeEventListener("loadedmetadata", handleMetadata);
      video.removeEventListener("timeupdate", handleTimeUpdate);
      video.removeEventListener("play", handlePlay);
      video.removeEventListener("pause", handlePause);
      video.removeEventListener("ended", handlePause);
      video.removeEventListener("volumechange", keepVideoMuted);
    };
  }, [src]);

  const togglePlayback = () => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    video.muted = true;
    video.defaultMuted = true;
    video.volume = 0;

    if (video.paused) {
      const playPromise = video.play();
      if (playPromise !== undefined) {
        playPromise.catch((playError: unknown) => {
          if (
            playError instanceof DOMException &&
            playError.name === "AbortError"
          ) {
            return;
          }
        });
      }
      return;
    }

    video.pause();
  };

  const handleSeek = (value: string) => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    const nextTime = Number(value);
    if (!Number.isFinite(nextTime)) {
      return;
    }

    video.currentTime = nextTime;
    setCurrentTime(nextTime);
  };

  const openFullscreen = () => {
    const container = containerRef.current;
    if (!container || !container.requestFullscreen) {
      return;
    }

    void container.requestFullscreen();
  };

  return (
    <div ref={containerRef} className="bg-black">
      <div className="relative aspect-video overflow-hidden bg-black">
        <video
          ref={videoRef}
          muted
          playsInline
          preload="metadata"
          disablePictureInPicture
          className="absolute inset-0 h-full w-full bg-black object-cover"
          src={src}
        />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_58%,rgba(0,0,0,0.22)_100%),linear-gradient(180deg,rgba(0,0,0,0.10),transparent_28%,transparent_72%,rgba(0,0,0,0.18))]" />
      </div>

      <div className="border-t border-white/10 bg-[linear-gradient(180deg,rgba(12,12,12,0.96),rgba(20,20,20,0.98))] px-3 py-2">
        <div className="flex items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.035] px-2.5 py-1.5 shadow-[0_8px_20px_rgba(0,0,0,0.18)]">
          <button
            type="button"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-primary/25 bg-primary/15 text-primary transition hover:border-primary/45 hover:bg-primary/20"
            aria-label={isPlaying ? "Pause reference demo" : "Play reference demo"}
            onClick={togglePlayback}
          >
            {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          </button>

          <input
            type="range"
            min={0}
            max={duration || 0}
            step="0.1"
            value={Math.min(currentTime, duration || currentTime)}
            aria-label="Seek reference demo"
            className="h-1 min-w-0 flex-1 cursor-pointer accent-primary"
            onChange={(event) => {
              handleSeek(event.target.value);
            }}
          />

          <span className="flex h-7 shrink-0 items-center text-[0.62rem] font-semibold tabular-nums uppercase tracking-[0.12em] text-white/50">
            {formatDemoTime(currentTime)} / {formatDemoTime(duration)}
          </span>

          <button
            type="button"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.06] text-white/70 transition hover:border-white/20 hover:bg-white/[0.10] hover:text-white"
            aria-label="View reference demo fullscreen"
            onClick={openFullscreen}
          >
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

function DrillDetailContent({
  drillId,
  profile
}: {
  drillId: string;
  profile: ProfileResponse | null;
}) {
  const [drill, setDrill] = useState<DrillDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { startError, startingMode, startSession } = useStartSessionFromDrill({
    drill,
    profile
  });

  useEffect(() => {
    let ignore = false;

    async function loadDrill() {
      setError(null);

      try {
        const drillDetail = await getDrillById(drillId);
        if (!ignore) {
          setDrill(drillDetail);
        }
      } catch (loadError) {
        if (!ignore) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load drill details."
          );
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    loadDrill();

    return () => {
      ignore = true;
    };
  }, [drillId]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader className="h-72" />
        <div className="grid gap-5 xl:grid-cols-2">
          <SkeletonLoader className="h-64" />
          <SkeletonLoader className="h-64" />
        </div>
        <SkeletonLoader className="h-72" />
      </div>
    );
  }

  if (error || !drill) {
    return (
      <EmptyState
        icon={PlayCircle}
        title="Drill detail unavailable"
        description={error ?? "We couldn't load this drill right now."}
        action={
          <CTAButton asChild>
            <Link href="/sports">Back to Sports</Link>
          </CTAButton>
        }
      />
    );
  }

  const metrics = drill.target_metrics.metrics ?? [];
  const phases = drill.reference_payload.phases ?? [];
  const joints = drill.reference_payload.tracked_joints ?? [];
  const primaryFocus = drill.coaching_rules.primary_focus ?? [];
  const positiveCues = drill.coaching_rules.positive_cues ?? [];
  const recommendationTemplates =
    drill.coaching_rules.recommendation_templates ?? [];
  const idealRanges = Object.entries(drill.reference_payload.ideal_ranges ?? {});
  const stabilityExpectations = Object.entries(
    drill.reference_payload.stability_expectations ?? {}
  );
  const recommendedViewLabel = drill.capture_protocol
    ? formatEnumLabel(drill.canonical_view ?? "FRONTAL")
    : "No drill-specific requirement";
  const activeSideLabel = drill.requires_dominant_side
    ? "Detected from movement by default. You can still override to Left or Right in session setup."
    : drill.supports_active_side_selection
      ? "Auto-detect by default. You can override to Left or Right in session setup."
      : "Not required for this drill.";
  const demoVideoUrl = drill.demo_video_url ?? null;
  const outputPreview = [
    "Capture validation",
    "Performance score",
    "Coaching cues",
    "Progress tracking"
  ];

  return (
    <div className="space-y-8">
      <InfoCard className="relative overflow-hidden border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.16),_transparent_35%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))]">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap gap-2">
              <Badge variant="accent">{drill.sport_name}</Badge>
              <Badge variant="slate">All skill levels</Badge>
            </div>
            <h2 className="mt-5 font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">
              {drill.drill_name}
            </h2>
            <p className="mt-4 text-sm text-muted-gray sm:text-base">
              {truncateText(drill.description, 110)}
            </p>

            <div className="mt-4 overflow-hidden rounded-[1.5rem] border border-white/10 bg-background-dark/70 shadow-soft transition duration-300 hover:border-primary/25 hover:shadow-[0_18px_45px_rgba(255,122,0,0.10)]">
              <div className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-2">
                <p className="text-[0.68rem] font-semibold uppercase tracking-[0.24em] text-primary/75">
                  Reference demo
                </p>
                <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.18em] text-white/55">
                  Model rep
                </span>
              </div>
              {demoVideoUrl ? (
                <DrillDemoVideo src={demoVideoUrl} />
              ) : (
                <div className="flex aspect-video flex-col items-center justify-center bg-[radial-gradient(circle_at_center,_rgba(255,122,0,0.10),_transparent_45%),linear-gradient(180deg,rgba(17,17,17,0.72),rgba(31,31,31,0.88))] px-6 text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
                    <PlayCircle className="h-5 w-5" />
                  </div>
                  <p className="mt-4 font-display text-xl font-bold text-white">
                    Demo video coming soon
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="grid w-full gap-3 xl:max-w-sm xl:-mt-1">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <CTAButton
                type="button"
                className="justify-between rounded-2xl px-5 py-5"
                disabled={startingMode !== null}
                onClick={() => {
                  void startSession("UPLOAD");
                }}
              >
                <span className="flex items-center gap-2">
                  <UploadCloud className="h-4 w-4" />
                  {startingMode === "UPLOAD"
                    ? "Creating upload session..."
                    : "Upload Video"}
                </span>
              </CTAButton>
              <CTAButton
                type="button"
                variant="outline"
                className="justify-between rounded-2xl border-white/15 bg-white/[0.03] px-5 py-5 text-white"
                disabled={startingMode !== null}
                onClick={() => {
                  void startSession("LIVE");
                }}
              >
                <span className="flex items-center gap-2">
                  <Camera className="h-4 w-4" />
                  {startingMode === "LIVE"
                    ? "Creating live session..."
                    : "Live Camera"}
                </span>
              </CTAButton>
            </div>
            {startError ? (
              <div className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm leading-6 text-rose-100">
                {startError}
              </div>
            ) : null}
            <p className="text-sm text-muted-gray">
              Pick a capture mode to open the training flow. Setup controls are available before capture starts.
            </p>
            <div className="rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-3.5">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                You’ll get
              </p>
              <div className="mt-3 space-y-2">
                {outputPreview.map((item) => (
                  <div
                    key={item}
                    className="flex items-start gap-2.5 rounded-2xl border border-white/10 bg-background-dark/50 px-3.5 py-2.5"
                  >
                    <Sparkles className="mt-0.5 h-3.5 w-3.5 text-primary" />
                    <p className="text-sm text-white/85">{item}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </InfoCard>

      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <InfoCard>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
            Overview
          </p>
          <h3 className="mt-4 font-display text-2xl font-bold text-white">
            Drill overview
          </h3>
          <p className="mt-4 text-sm text-muted-gray">
            {truncateText(drill.reference_payload.notes ?? drill.description, 120)}
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Movement Type
              </p>
              <p className="mt-3 text-base font-semibold text-white">
                {formatTokenLabel(drill.reference_payload.movement_type ?? "dynamic")}
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Phases
              </p>
              <p className="mt-3 text-base font-semibold text-white">
                {phases.length}
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Tracked Joints
              </p>
              <p className="mt-3 text-base font-semibold text-white">
                {joints.length}
              </p>
            </div>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Phases
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {phases.map((phase) => (
                  <Badge key={phase} variant="slate">
                    {formatTokenLabel(phase)}
                  </Badge>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Tracked joints
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {joints.map((joint) => (
                  <Badge key={joint} variant="slate">
                    {formatTokenLabel(joint)}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </InfoCard>

        <InfoCard>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
            Target Metrics
          </p>
          <h3 className="mt-4 font-display text-2xl font-bold text-white">
            Key metrics
          </h3>
          <div className="mt-6 grid gap-3">
            {metrics.map((metric) => (
              <div
                key={metric}
                className="rounded-2xl border border-primary/15 bg-primary/10 px-4 py-4"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-primary/20 bg-primary/15 text-primary">
                    <Target className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">
                      {formatTokenLabel(metric)}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-white/72">
                      {getMetricDescription(metric)}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </InfoCard>
      </div>

      <InfoCard>
        <SectionTitle
          eyebrow="Capture Setup"
          title="Capture protocol"
          description="Set the camera, framing, and active side before you log the set."
        />

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Recommended camera view
            </p>
            <p className="mt-3 text-base font-semibold text-white">
              {recommendedViewLabel}
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Supported views
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {drill.allowed_camera_views.map((view) => (
                <Badge key={view} variant="slate">
                  {formatEnumLabel(view)}
                </Badge>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Active side
            </p>
            <p className="mt-3 text-sm leading-6 text-white/85">
              {activeSideLabel}
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Recording tips
            </p>
            <p className="mt-3 text-sm leading-6 text-white/85">
              {drill.reference_payload.notes || "Keep the full movement in frame with steady lighting and a stable camera."}
            </p>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <Badge variant="accent">Live Camera</Badge>
          <Badge variant="slate">Upload Video</Badge>
        </div>
      </InfoCard>

      <div className="grid gap-5 xl:grid-cols-3">
        <InfoCard>
          <SectionTitle
            eyebrow="Coaching Focus"
            title="Focus points"
            description="What to lock in first."
          />
          <div className="mt-6 flex flex-wrap gap-2">
            {primaryFocus.map((item) => (
              <Badge key={item} variant="accent">
                {formatTokenLabel(item)}
              </Badge>
            ))}
          </div>
        </InfoCard>

        <InfoCard>
          <SectionTitle
            eyebrow="Positive Cues"
            title="Good reps"
            description="Repeat these movement habits."
          />
          <ul className="mt-6 space-y-3">
            {positiveCues.map((cue) => (
              <li
                key={cue}
                className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white/85"
              >
                {cue}
              </li>
            ))}
          </ul>
        </InfoCard>

        <InfoCard>
          <SectionTitle
            eyebrow="Recommendations"
            title="Next actions"
            description="Use these cues next."
          />
          <ul className="mt-6 space-y-3">
            {recommendationTemplates.map((item) => (
              <li
                key={item}
                className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white/85"
              >
                {item}
              </li>
            ))}
          </ul>
        </InfoCard>
      </div>

      <div className="space-y-5">
        <SectionTitle
          eyebrow="Targets"
          title="Ranges and stability"
          description="Target values for this drill."
          action={
            <Link
              href={`/sports/${drill.sport_id}/drills`}
              className="inline-flex items-center gap-2 text-sm font-semibold text-primary transition-colors hover:text-primary/80"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to drill list
            </Link>
          }
        />

        <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
          <InfoCard>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
              Ideal Ranges
            </p>
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {idealRanges.map(([key, value]) => (
                <div
                  key={key}
                  className="rounded-2xl border border-white/10 bg-white/[0.04] p-4"
                >
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    {formatTokenLabel(key)}
                  </p>
                  <p className="mt-3 text-lg font-semibold text-white">
                    {value.min ?? 0} - {value.max ?? 0}
                  </p>
                </div>
              ))}
            </div>
          </InfoCard>

          <InfoCard>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
              Stability Expectations
            </p>
            <div className="mt-6 space-y-3">
              {stabilityExpectations.map(([key, value]) => (
                <div
                  key={key}
                  className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3"
                >
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    {formatTokenLabel(key)}
                  </p>
                  <p className="mt-2 text-base font-semibold text-white">
                    {String(value)}
                  </p>
                </div>
              ))}
            </div>
          </InfoCard>
        </div>
      </div>

      <InfoCard>
        <SectionTitle
          eyebrow="Preview"
          title="What your review unlocks"
          description="Every analyzed session comes back with these performance checkpoints."
        />
        <div className="mt-6 grid gap-4 lg:grid-cols-4">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
              <UploadCloud className="h-5 w-5" />
            </div>
            <p className="mt-4 text-sm font-semibold text-white">Validation</p>
            <p className="mt-2 text-sm text-muted-gray">
              File checks
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
              <ListChecks className="h-5 w-5" />
            </div>
            <p className="mt-4 text-sm font-semibold text-white">Evaluation</p>
            <p className="mt-2 text-sm text-muted-gray">
              Scores and issues
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
              <Sparkles className="h-5 w-5" />
            </div>
            <p className="mt-4 text-sm font-semibold text-white">Summary</p>
            <p className="mt-2 text-sm text-muted-gray">
              Strengths and next steps
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
              <Target className="h-5 w-5" />
            </div>
            <p className="mt-4 text-sm font-semibold text-white">Progress</p>
            <p className="mt-2 text-sm text-muted-gray">
              Performance dashboard trends
            </p>
          </div>
        </div>
      </InfoCard>
    </div>
  );
}

export default function DrillDetailPage({
  params
}: {
  params: { drillId: string };
}) {
  return (
    <AppShell
      eyebrow="Drill"
      title="Drill preview"
      description="Review the setup, lock in the capture plan, then start training."
      capsule="Ready"
      actions={
        <CTAButton asChild>
          <Link href="/sports">All Sports</Link>
        </CTAButton>
      }
    >
      {({ profile }) => (
        <DrillDetailContent drillId={params.drillId} profile={profile} />
      )}
    </AppShell>
  );
}

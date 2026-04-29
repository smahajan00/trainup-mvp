"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { PlayCircle, Sparkles, UploadCloud } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { CTAButton } from "../../../components/ui/cta-button";
import { Label } from "../../../components/ui/label";
import { Select } from "../../../components/ui/select";
import { SkeletonLoader } from "../../../components/ui/skeleton-loader";
import { AppShell } from "../../../features/app-shell/components/AppShell";
import { EmptyState } from "../../../features/app-shell/components/EmptyState";
import { InfoCard } from "../../../features/app-shell/components/InfoCard";
import { SectionTitle } from "../../../features/app-shell/components/SectionTitle";
import { ModeCard } from "../../../features/sessions/components/ModeCard";
import { getErrorMessage } from "../../../lib/api";
import { formatEnumLabel, formatTokenLabel } from "../../../lib/formatters";
import { getDrillById } from "../../../services/drills";
import { createSession } from "../../../services/sessions";
import type { DrillDetail } from "../../../types/drills";
import type { ProfileResponse, SkillLevel } from "../../../types/profile";
import type {
  CameraView,
  DominantSide,
  SessionInputType
} from "../../../types/sessions";

const DEFAULT_CAMERA_VIEWS: CameraView[] = [
  "FRONTAL",
  "LEFT_SAGITTAL",
  "RIGHT_SAGITTAL"
];

const dominantSideOptions: { value: DominantSide; label: string }[] = [
  { value: "AUTO", label: "Auto-detect" },
  { value: "LEFT", label: "Left" },
  { value: "RIGHT", label: "Right" }
];

function isSessionInputType(value: string | null): value is SessionInputType {
  return value === "UPLOAD" || value === "LIVE";
}

function isCameraView(value: string): value is CameraView {
  return DEFAULT_CAMERA_VIEWS.includes(value as CameraView);
}

function SessionCreationContent({
  profile
}: {
  profile: ProfileResponse | null;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const drillId = searchParams.get("drillId");
  const requestedInputType = useMemo(() => {
    const mode = searchParams.get("mode");
    return isSessionInputType(mode) ? mode : null;
  }, [searchParams]);
  const [drill, setDrill] = useState<DrillDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [creatingMode, setCreatingMode] = useState<SessionInputType | null>(null);
  const [selectedInputType, setSelectedInputType] = useState<SessionInputType | null>(
    requestedInputType
  );
  const [selectedCameraView, setSelectedCameraView] = useState<CameraView | "">("");
  const [selectedDominantSide, setSelectedDominantSide] =
    useState<DominantSide>("AUTO");

  useEffect(() => {
    if (requestedInputType) {
      setSelectedInputType(requestedInputType);
    }
  }, [requestedInputType]);

  useEffect(() => {
    let ignore = false;

    async function loadDrill() {
      if (!drillId) {
        setIsLoading(false);
        return;
      }

      setLoadError(null);

      try {
        const drillDetail = await getDrillById(drillId);
        if (!ignore) {
          setDrill(drillDetail);
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

    loadDrill();

    return () => {
      ignore = true;
    };
  }, [drillId]);

  useEffect(() => {
    if (!drill) {
      return;
    }

    const defaultCameraView =
      drill.canonical_view ?? drill.allowed_camera_views[0] ?? DEFAULT_CAMERA_VIEWS[0];

    setSelectedCameraView((current) =>
      current && drill.allowed_camera_views.includes(current)
        ? current
        : defaultCameraView
    );

    if (!drill.supports_active_side_selection) {
      setSelectedDominantSide("AUTO");
    }
  }, [drill]);

  const metrics = useMemo(
    () => drill?.target_metrics.metrics.slice(0, 5) ?? [],
    [drill]
  );
  const isModePreselected = requestedInputType !== null;
  const isCrossSportTraining = Boolean(
    profile && drill && profile.sport_id !== drill.sport_id
  );
  const resolvedSkillLevel: SkillLevel = profile?.skill_level && !isCrossSportTraining
    ? profile.skill_level
    : "BEGINNER";
  const usesFallbackSkillLevel = !profile?.skill_level || isCrossSportTraining;

  if (!drillId) {
    return (
      <EmptyState
        icon={Sparkles}
        title="Choose a drill before starting a session"
        description="Open a drill detail page first, then launch either the live or upload training flow."
        action={
          <CTAButton asChild>
            <Link href="/sports">Browse Sports</Link>
          </CTAButton>
        }
      />
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader className="h-64" />
        <div className="grid gap-5 lg:grid-cols-2">
          <SkeletonLoader className="h-[340px]" />
          <SkeletonLoader className="h-[420px]" />
        </div>
      </div>
    );
  }

  if (loadError || !drill) {
    return (
      <EmptyState
        icon={Sparkles}
        title="Drill session setup unavailable"
        description={loadError ?? "We couldn't load this drill."}
        action={
          <CTAButton asChild>
            <Link href="/sports">Back to Sports</Link>
          </CTAButton>
        }
      />
    );
  }

  if (!profile) {
    return (
      <EmptyState
        icon={Sparkles}
        title="Complete your profile before starting"
        description="Your profile provides the sport and skill level context needed to create a training session."
        action={
          <CTAButton asChild>
            <Link href="/profile">Complete Profile</Link>
          </CTAButton>
        }
      />
    );
  }

  const activeDrill = drill;

  async function handleCreateSession() {
    if (!selectedInputType) {
      setCreateError("Choose Upload Video or Live Camera before continuing.");
      return;
    }

    if (!selectedCameraView) {
      setCreateError("Choose a camera view before creating the session.");
      return;
    }

    setCreateError(null);
    setCreatingMode(selectedInputType);

    try {
      const session = await createSession({
        sport_id: activeDrill.sport_id,
        skill_level: resolvedSkillLevel,
        drill_id: activeDrill.id,
        input_type: selectedInputType,
        camera_view: selectedCameraView,
        dominant_side:
          activeDrill.supports_active_side_selection &&
          selectedDominantSide !== "AUTO"
            ? selectedDominantSide
            : null
      });

      router.push(
        selectedInputType === "LIVE"
          ? `/sessions/${session.id}/live`
          : `/sessions/${session.id}/upload`
      );
    } catch (error) {
      setCreateError(getErrorMessage(error));
      setCreatingMode(null);
    }
  }

  const primaryActionLabel =
    selectedInputType === "LIVE"
      ? "Open Live Camera"
      : selectedInputType === "UPLOAD"
        ? "Open Upload Flow"
        : "Choose Your Training Mode";
  const recommendedCameraView =
    drill.canonical_view ||
    selectedCameraView ||
    DEFAULT_CAMERA_VIEWS[0];

  return (
    <div className="space-y-8">
      <InfoCard className="relative overflow-hidden border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.16),_transparent_35%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))]">
        <div className="flex flex-wrap gap-2">
          <Badge variant="accent">{drill.sport_name}</Badge>
          <Badge variant="slate">{formatEnumLabel(resolvedSkillLevel)}</Badge>
          {selectedInputType ? (
            <Badge variant="slate">{formatEnumLabel(selectedInputType)}</Badge>
          ) : null}
        </div>
        <h2 className="mt-5 font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">
          {drill.drill_name}
        </h2>
        <p className="mt-4 max-w-3xl text-sm text-muted-gray sm:text-base">
          Run through this pre-training checklist before you create the session.
        </p>
        <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-4">
          <p className="text-sm font-semibold text-white">
            Training in {drill.sport_name}
          </p>
          <p className="mt-2 text-sm leading-6 text-muted-gray">
            {usesFallbackSkillLevel
              ? "No skill level is set for this sport yet, so Beginner will be used for this session."
              : `Using your ${formatEnumLabel(resolvedSkillLevel).toLowerCase()} skill level for this sport.`}
          </p>
        </div>
        <div className="mt-6 flex flex-wrap gap-2">
          {metrics.map((metric) => (
            <Badge key={metric} variant="slate">
              {formatTokenLabel(metric)}
            </Badge>
          ))}
        </div>
      </InfoCard>

      {createError ? (
        <div className="rounded-[1.5rem] border border-rose-400/30 bg-rose-500/10 px-5 py-4 text-sm text-rose-100">
          {createError}
        </div>
      ) : null}

      {creatingMode ? (
        <InfoCard className="border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.16),_transparent_35%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))]">
          <Badge variant="accent">{formatEnumLabel(creatingMode)}</Badge>
          <h2 className="mt-4 font-display text-4xl font-bold text-white">
            Creating session
          </h2>
          <p className="mt-4 max-w-2xl text-sm text-muted-gray">
            Setting up {drill.drill_name}. You’ll move to the selected input flow next.
          </p>
        </InfoCard>
      ) : null}

      <div className="space-y-5">
        <SectionTitle
          eyebrow="Checklist"
          title={isModePreselected ? "Training mode selected" : "Choose your training mode"}
          description={
            isModePreselected
              ? "Your capture mode is locked in. Confirm the remaining setup details, then start training."
              : "Pick the capture flow that fits the rep you want to review."
          }
        />
        {isModePreselected ? (
          <div className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                  Training mode
                </p>
                <p className="mt-3 text-lg font-semibold text-white">
                  {selectedInputType === "LIVE" ? "Live Camera" : "Upload Video"}
                </p>
                <p className="mt-2 text-sm leading-6 text-muted-gray">
                  {selectedInputType === "LIVE"
                    ? "Camera controls and the live preview will open as soon as this session is created."
                    : "You’ll move straight into clip upload and preview as soon as this session is created."}
                </p>
              </div>
              <Button asChild variant="ghost" className="border border-white/10 bg-white/[0.03]">
                <Link href={`/drills/${drill.id}`}>Change mode</Link>
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid gap-5 lg:grid-cols-2">
            <ModeCard
              title="Live Camera"
              description="Use your camera for a guided real-time rep capture."
              badge="Camera"
              eyebrow="Live"
              detail="Open the camera, control the rep, and review it when you stop."
              ctaLabel="Choose Live Camera"
              icon={PlayCircle}
              isSelected={selectedInputType === "LIVE"}
              onSelect={() => setSelectedInputType("LIVE")}
            />
            <ModeCard
              title="Upload Video"
              description="Submit a recorded clip for a polished breakdown."
              badge="Video"
              eyebrow="Upload"
              detail="Drop in one clip, preview it, then run the full analysis."
              ctaLabel="Choose Upload Video"
              icon={UploadCloud}
              isSelected={selectedInputType === "UPLOAD"}
              onSelect={() => setSelectedInputType("UPLOAD")}
            />
          </div>
        )}
      </div>

      <InfoCard>
        <SectionTitle
          eyebrow="Setup"
          title="Confirm your training checklist"
          description="Review the sport, drill, and capture settings before you lock in the session."
        />

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Selected sport
            </p>
            <p className="mt-3 text-base font-semibold text-white">
              {drill.sport_name}
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Selected drill
            </p>
            <p className="mt-3 text-base font-semibold text-white">
              {drill.drill_name}
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Skill level
            </p>
            <p className="mt-3 text-base font-semibold text-white">
              {formatEnumLabel(resolvedSkillLevel)}
            </p>
            {usesFallbackSkillLevel ? (
              <p className="mt-2 text-sm leading-6 text-muted-gray">
                Using Beginner level for this sport.
              </p>
            ) : null}
          </div>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="camera_view">Camera view</Label>
            <Select
              id="camera_view"
              value={selectedCameraView}
              onChange={(event) =>
                setSelectedCameraView(
                  isCameraView(event.target.value) ? event.target.value : ""
                )
              }
            >
              {drill.allowed_camera_views.map((view) => (
                <option key={view} value={view} className="bg-slate text-white">
                  {formatEnumLabel(view)}
                </option>
              ))}
            </Select>
            <p className="text-sm text-muted-gray">
              Recommended setup angle:{" "}
              {formatEnumLabel(recommendedCameraView)}
            </p>
          </div>

          {drill.supports_active_side_selection ? (
            <div className="space-y-2">
              <Label htmlFor="dominant_side">Active side</Label>
              <Select
                id="dominant_side"
                value={selectedDominantSide}
                onChange={(event) =>
                  setSelectedDominantSide(event.target.value as DominantSide)
                }
              >
                {dominantSideOptions.map((option) => (
                  <option
                    key={option.value}
                    value={option.value}
                    className="bg-slate text-white"
                  >
                    {option.label}
                  </option>
                ))}
              </Select>
              <p className="text-sm text-muted-gray">
                {drill.requires_dominant_side
                  ? "Active side will be detected from movement. Override it only if you want to lock the drill to Left or Right."
                  : "Auto-detect is the default. Override it if you want to force a side."}
              </p>
            </div>
          ) : (
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Active side
              </p>
              <p className="mt-3 text-sm leading-6 text-white/85">
                This drill does not need active-side selection during setup.
              </p>
            </div>
          )}
        </div>

        <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
            Capture guidance
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {drill.allowed_camera_views.map((view) => (
              <Badge key={view} variant="slate">
                {formatEnumLabel(view)}
              </Badge>
            ))}
          </div>
          <p className="mt-4 text-sm leading-6 text-white/85">
            {drill.reference_payload.notes}
          </p>
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <CTAButton
            type="button"
            onClick={handleCreateSession}
            disabled={
              !selectedInputType ||
              !selectedCameraView ||
              creatingMode !== null
            }
          >
            {primaryActionLabel}
          </CTAButton>
          <Button asChild variant="outline">
            <Link href={`/drills/${drill.id}`}>Back to Drill</Link>
          </Button>
          <Button asChild variant="ghost" className="border border-white/10 bg-white/[0.03]">
            <Link href="/profile">Update Profile</Link>
          </Button>
        </div>
      </InfoCard>
    </div>
  );
}

export default function NewSessionPage() {
  return (
    <AppShell
      eyebrow="Session"
      title="Pre-training checklist"
      description="Confirm the drill setup, camera angle, and active-side details before you train."
      capsule="Ready"
      actions={
        <CTAButton asChild>
          <Link href="/sports">Back to Sports</Link>
        </CTAButton>
      }
    >
      {({ profile }) => <SessionCreationContent profile={profile} />}
    </AppShell>
  );
}

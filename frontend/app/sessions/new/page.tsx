"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { PlayCircle, Sparkles, UploadCloud } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { CTAButton } from "../../../components/ui/cta-button";
import { SkeletonLoader } from "../../../components/ui/skeleton-loader";
import { AppShell } from "../../../features/app-shell/components/AppShell";
import { EmptyState } from "../../../features/app-shell/components/EmptyState";
import { InfoCard } from "../../../features/app-shell/components/InfoCard";
import { SectionTitle } from "../../../features/app-shell/components/SectionTitle";
import { ModeCard } from "../../../features/sessions/components/ModeCard";
import { formatEnumLabel, formatTokenLabel } from "../../../lib/formatters";
import { createSession } from "../../../services/sessions";
import { getDrillById } from "../../../services/drills";
import type { DrillDetail } from "../../../types/drills";
import type { SessionInputType } from "../../../types/sessions";

function isValidMode(value: string | null): value is SessionInputType {
  return value === "LIVE" || value === "UPLOAD";
}

function SessionCreationContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const drillId = searchParams.get("drillId");
  const requestedMode = searchParams.get("mode");
  const autoCreateTriggered = useRef(false);
  const [drill, setDrill] = useState<DrillDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [creatingMode, setCreatingMode] = useState<SessionInputType | null>(null);

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
          setLoadError(
            error instanceof Error ? error.message : "Unable to load the drill."
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

  useEffect(() => {
    if (!drillId || !isValidMode(requestedMode) || autoCreateTriggered.current) {
      return;
    }

    autoCreateTriggered.current = true;
    setCreatingMode(requestedMode);
    setCreateError(null);

    createSession({ drill_id: drillId, input_type: requestedMode })
      .then((session) => {
        const destination =
          requestedMode === "LIVE"
            ? `/sessions/${session.id}/live`
            : `/sessions/${session.id}/upload`;
        router.replace(destination);
      })
      .catch((error) => {
        autoCreateTriggered.current = false;
        setCreateError(
          error instanceof Error
            ? error.message
            : "Unable to create the training session."
        );
        setCreatingMode(null);
      });
  }, [drillId, requestedMode, router]);

  const metrics = useMemo(
    () => drill?.target_metrics.metrics.slice(0, 5) ?? [],
    [drill]
  );

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
          <SkeletonLoader className="h-[340px]" />
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

  if (creatingMode) {
    return (
        <InfoCard className="border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.16),_transparent_35%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))]">
        <Badge variant="accent">{formatEnumLabel(creatingMode)}</Badge>
        <h2 className="mt-4 font-display text-4xl font-bold text-white">
          Starting {creatingMode === "LIVE" ? "live" : "upload"} session
        </h2>
        <p className="mt-4 max-w-2xl text-sm text-muted-gray">
          Opening {drill.drill_name}. You’ll move in automatically.
        </p>
      </InfoCard>
    );
  }

  return (
    <div className="space-y-8">
      <InfoCard className="relative overflow-hidden border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.16),_transparent_35%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))]">
        <div className="flex flex-wrap gap-2">
          <Badge variant="accent">{drill.sport_name}</Badge>
          <Badge variant="slate">{formatEnumLabel(drill.difficulty_level)}</Badge>
        </div>
        <h2 className="mt-5 font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">
          {drill.drill_name}
        </h2>
        <p className="mt-4 max-w-3xl text-sm text-muted-gray sm:text-base">
          Pick your session mode.
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          {metrics.map((metric) => (
            <Badge key={metric} variant="slate">
              {formatTokenLabel(metric)}
            </Badge>
          ))}
        </div>
      </InfoCard>

      {createError ? (
        <EmptyState
          icon={Sparkles}
          title="Session creation failed"
          description={createError}
          action={
            <CTAButton asChild>
              <Link href={`/drills/${drill.id}`}>Back to Drill</Link>
            </CTAButton>
          }
        />
      ) : null}

      <div className="space-y-5">
        <SectionTitle
          eyebrow="Mode"
          title="Choose session mode"
          description="Live uses camera. Upload uses video."
        />
        <div className="grid gap-5 lg:grid-cols-2">
          <ModeCard
            title="Live Session"
            description="Use your camera for guided real-time training flow."
            badge="Camera"
            eyebrow="Live"
            detail="Open camera. Start when ready."
            ctaLabel="Start Live"
            icon={PlayCircle}
            onSelect={() => router.push(`/sessions/new?drillId=${drill.id}&mode=LIVE`)}
          />
          <ModeCard
            title="Upload Video"
            description="Submit a recorded clip for structured review."
            badge="Video"
            eyebrow="Upload"
            detail="Pick a clip. Review results."
            ctaLabel="Start Upload"
            icon={UploadCloud}
            onSelect={() => router.push(`/sessions/new?drillId=${drill.id}&mode=UPLOAD`)}
          />
        </div>
      </div>
    </div>
  );
}

export default function NewSessionPage() {
  return (
    <AppShell
      eyebrow="Session"
      title="Start session"
      description="Choose how you want to train."
      capsule="Ready"
      actions={
        <CTAButton asChild>
          <Link href="/sports">Back to Sports</Link>
        </CTAButton>
      }
    >
      {() => <SessionCreationContent />}
    </AppShell>
  );
}

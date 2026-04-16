"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";
import { ArrowLeft, FileCheck2, UploadCloud } from "lucide-react";

import { Badge } from "../../../../components/ui/badge";
import { Button } from "../../../../components/ui/button";
import { CTAButton } from "../../../../components/ui/cta-button";
import { SkeletonLoader } from "../../../../components/ui/skeleton-loader";
import { AppShell } from "../../../../features/app-shell/components/AppShell";
import { EmptyState } from "../../../../features/app-shell/components/EmptyState";
import { InfoCard } from "../../../../features/app-shell/components/InfoCard";
import { SectionTitle } from "../../../../features/app-shell/components/SectionTitle";
import { SessionStatusBadge } from "../../../../features/sessions/components/SessionStatusBadge";
import { formatDateTime, formatEnumLabel, formatFileSize } from "../../../../lib/formatters";
import { validateVideoFile } from "../../../../lib/session-validation";
import { getSession, submitSessionUpload } from "../../../../services/sessions";
import type {
  TrainingSession,
  UploadValidationResponse
} from "../../../../types/sessions";

function UploadSessionContent({ sessionId }: { sessionId: string }) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [session, setSession] = useState<TrainingSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [localErrors, setLocalErrors] = useState<string[]>([]);
  const [localWarnings, setLocalWarnings] = useState<string[]>([]);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadValidationResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDragActive, setIsDragActive] = useState(false);

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
              : "Unable to load the upload session."
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

  const displayWarnings = [
    ...localWarnings,
    ...(uploadResult?.validation.warnings ?? [])
  ];
  const displayErrors = [...localErrors, ...(uploadResult?.validation.errors ?? [])];

  function handleSelectedFile(file: File | null) {
    setSelectedFile(file);
    setUploadResult(null);
    setSubmitError(null);

    if (!file) {
      setLocalErrors([]);
      setLocalWarnings([]);
      return;
    }

    const validation = validateVideoFile(file);
    setLocalErrors(validation.errors);
    setLocalWarnings(validation.warnings);
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    handleSelectedFile(event.target.files?.[0] ?? null);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragActive(false);
    handleSelectedFile(event.dataTransfer.files?.[0] ?? null);
  }

  async function handleUpload() {
    if (!selectedFile) {
      setSubmitError("Select a video file before submitting.");
      return;
    }

    const validation = validateVideoFile(selectedFile);
    setLocalErrors(validation.errors);
    setLocalWarnings(validation.warnings);
    setSubmitError(null);
    setUploadResult(null);

    if (!validation.isValid) {
      return;
    }

    try {
      setIsSubmitting(true);
      const result = await submitSessionUpload(sessionId, selectedFile);
      setUploadResult(result);
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "Unable to submit this video."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader className="h-64" />
        <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
          <SkeletonLoader className="h-[440px]" />
          <SkeletonLoader className="h-[440px]" />
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

  if (session.input_type !== "UPLOAD") {
    return (
      <EmptyState
        icon={UploadCloud}
        title="This session is not in upload mode"
        description="Open the matching live session page or create a dedicated upload session from the drill detail screen."
        action={
          <CTAButton asChild>
            <Link href={`/drills/${session.drill_id}`}>Back to Drill</Link>
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
              <SessionStatusBadge status={session.status} />
            </div>
            <h2 className="mt-5 font-display text-4xl font-bold text-white sm:text-5xl">
              {session.drill_name}
            </h2>
            <p className="mt-4 text-sm leading-7 text-muted-gray sm:text-base">
              Validate a recorded drill clip and hand it into the upload
              processing scaffold. TrainUp is checking file hygiene now; the
              future Perception stage will attach extraction and analysis next.
            </p>
          </div>

          <div className="grid gap-3 xl:min-w-[280px]">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                Session Started
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

      <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <InfoCard className="relative overflow-hidden">
          <SectionTitle
            eyebrow="Upload Capture"
            title="Submit a drill video into the scaffolded pipeline"
            description="Accepted formats: MP4, MOV, WEBM, and MKV. Raw media is validated but not permanently stored in this phase."
          />

          <div
            onDragOver={(event) => {
              event.preventDefault();
              setIsDragActive(true);
            }}
            onDragLeave={() => setIsDragActive(false)}
            onDrop={handleDrop}
            className={`mt-6 rounded-[1.75rem] border border-dashed px-6 py-10 text-center transition-all duration-300 ${
              isDragActive
                ? "border-primary/45 bg-primary/10"
                : "border-white/12 bg-white/[0.03]"
            }`}
          >
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl border border-primary/20 bg-primary/10 text-primary">
              <UploadCloud className="h-7 w-7" />
            </div>
            <h3 className="mt-5 font-display text-2xl font-bold text-white">
              Drag a video here or browse locally
            </h3>
            <p className="mt-3 text-sm leading-7 text-muted-gray">
              Keep the full movement visible, maintain a stable camera angle,
              and prefer landscape framing for drill review.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <CTAButton type="button" onClick={() => inputRef.current?.click()}>
                Choose Video
              </CTAButton>
              <Button
                type="button"
                variant="outline"
                className="rounded-xl"
                onClick={() => handleSelectedFile(null)}
              >
                Clear Selection
              </Button>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept="video/mp4,video/quicktime,video/webm,video/x-matroska"
              className="hidden"
              onChange={handleInputChange}
            />
            {selectedFile ? (
              <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 text-left">
                <p className="text-sm font-semibold text-white">{selectedFile.name}</p>
                <p className="mt-2 text-sm text-muted-gray">
                  {selectedFile.type || "Unknown type"} · {formatFileSize(selectedFile.size)}
                </p>
              </div>
            ) : null}
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <Button
              type="button"
              onClick={handleUpload}
              className="rounded-2xl px-6"
              disabled={!selectedFile || isSubmitting}
            >
              {isSubmitting ? "Validating Video" : "Submit Video"}
            </Button>
            <Badge variant="slate">100 MB max</Badge>
            <Badge variant="slate">No analysis yet</Badge>
          </div>
        </InfoCard>

        <div className="space-y-5">
          <InfoCard>
            <SectionTitle
              eyebrow="Validation"
              title="Session-side upload checks"
              description="This is where TrainUp confirms the media is suitable for the next Perception-layer stage."
            />

            {submitError ? (
              <div className="mt-6 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-4 text-sm leading-7 text-rose-100">
                {submitError}
              </div>
            ) : null}

            {displayErrors.length ? (
              <div className="mt-6 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-rose-200">
                  Errors
                </p>
                <ul className="mt-3 space-y-2 text-sm leading-7 text-rose-100">
                  {displayErrors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {displayWarnings.length ? (
              <div className="mt-4 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-amber-200">
                  Warnings
                </p>
                <ul className="mt-3 space-y-2 text-sm leading-7 text-amber-100">
                  {displayWarnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {uploadResult ? (
              <div className="mt-6 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-4">
                <div className="flex items-center gap-3">
                  <FileCheck2 className="h-5 w-5 text-emerald-200" />
                  <p className="text-sm font-semibold text-white">
                    {uploadResult.upload_received
                      ? "Video accepted"
                      : "Video received but not cleared for the next stage"}
                  </p>
                </div>
                <p className="mt-3 text-sm leading-7 text-emerald-50">
                  {uploadResult.next_step}
                </p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm text-white/85">
                    <span className="block text-xs uppercase tracking-[0.2em] text-white/50">
                      Content Type
                    </span>
                    <span className="mt-2 block">
                      {uploadResult.validation.content_type ?? "Unknown"}
                    </span>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm text-white/85">
                    <span className="block text-xs uppercase tracking-[0.2em] text-white/50">
                      File Size
                    </span>
                    <span className="mt-2 block">
                      {formatFileSize(uploadResult.validation.file_size_bytes)}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="mt-6 text-sm leading-7 text-muted-gray">
                Video accepted. Perception extraction stage will be connected next.
              </p>
            )}
          </InfoCard>

          <InfoCard>
            <SectionTitle
              eyebrow="Capture Guidance"
              title="Record with later analysis in mind"
              description="These are practical prep notes for the upcoming perception stage."
            />
            <ul className="mt-6 space-y-3 text-sm leading-7 text-white/85">
              <li>Keep the athlete and the full drill motion inside the frame.</li>
              <li>Use a stable camera angle and avoid rapid zooming or panning.</li>
              <li>Prefer clear side or front angles that expose the key joints.</li>
              <li>Good lighting and uncluttered backgrounds improve the next stage.</li>
            </ul>
          </InfoCard>
        </div>
      </div>
    </div>
  );
}

export default function UploadSessionPage() {
  const params = useParams<{ sessionId: string }>();

  return (
    <AppShell
      eyebrow="Upload Session"
      title="Recorded video intake"
      description="Validate a drill video and route it into TrainUp's Perception-layer scaffold."
      capsule="Upload pipeline"
      actions={
        <CTAButton asChild>
          <Link href="/sports">Browse Sports</Link>
        </CTAButton>
      }
    >
      {() => <UploadSessionContent sessionId={params.sessionId} />}
    </AppShell>
  );
}

import { Loader2, Pause, Play } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Badge } from "../../../components/ui/badge";
import { ApiError, getErrorMessage } from "../../../lib/api";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { generateSessionFeedbackTTS } from "../../../services/sessions";
import type { FeedbackTTSSegments, SeverityLevel } from "../../../types/sessions";
import {
  areCoachingTextsSimilar,
  formatSeverityLabel,
  getSeverityVariant
} from "./session-results-utils";

const AUDIO_PLAY_EVENT = "trainup-feedback-audio-play";

type CoachingFeedbackCardProps = {
  sessionId: string;
  feedbackItemKey: string;
  title: string;
  severity?: SeverityLevel | null;
  whatHappened: string;
  whyItHappened: string;
  whatToFix: string;
  nextAction: string;
  simpleCue?: string | null;
  isEnhanced: boolean;
  backupNote?: string | null;
  ttsSegments: FeedbackTTSSegments;
};

function formatAudioTime(value: number) {
  if (!Number.isFinite(value) || value <= 0) {
    return "0:00";
  }

  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60)
    .toString()
    .padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function getAudioErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Your login session expired. Sign in again and retry audio coaching.";
    }
    if (error.status === 404) {
      return "This session could not be found for audio coaching. Open a current session and try again.";
    }
    if (error.status === 503) {
      return "Audio coaching is unavailable right now.";
    }
    return getErrorMessage(error);
  }

  return "Voice guidance was generated, but the browser could not start playback. Tap Listen to coaching again.";
}

export function CoachingFeedbackCard({
  sessionId,
  feedbackItemKey,
  title,
  severity,
  whatHappened,
  whyItHappened,
  whatToFix,
  nextAction,
  simpleCue,
  isEnhanced,
  backupNote,
  ttsSegments
}: CoachingFeedbackCardProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  const loadedAudioKeyRef = useRef<string | null>(null);
  const [isPreparingAudio, setIsPreparingAudio] = useState(false);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [audioCached, setAudioCached] = useState<boolean | null>(null);
  const [audioDuration, setAudioDuration] = useState(0);
  const [audioCurrentTime, setAudioCurrentTime] = useState(0);
  const [loadingLabel, setLoadingLabel] = useState("Generating voice guidance...");
  const audioKey = `${sessionId}:${feedbackItemKey}:${JSON.stringify(ttsSegments)}`;

  useEffect(() => {
    function handleExternalPlay(event: Event) {
      const detail = (event as CustomEvent<{ key: string }>).detail;
      if (detail?.key === audioKey || !audioRef.current) {
        return;
      }

      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setAudioCurrentTime(0);
      setIsAudioPlaying(false);
    }

    window.addEventListener(AUDIO_PLAY_EVENT, handleExternalPlay);
    return () => {
      window.removeEventListener(AUDIO_PLAY_EVENT, handleExternalPlay);
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
    };
  }, [audioKey]);

  async function prepareAudio() {
    if (audioRef.current && loadedAudioKeyRef.current === audioKey) {
      return;
    }

    setIsPreparingAudio(true);
    setLoadingLabel("Checking saved voice guidance...");
    setAudioError(null);
    const slowGenerationTimer = window.setTimeout(() => {
      setLoadingLabel("Generating voice guidance...");
    }, 650);

    try {
      const response = await generateSessionFeedbackTTS(sessionId, {
        feedback_item_key: feedbackItemKey,
        segments: ttsSegments
      });
      window.clearTimeout(slowGenerationTimer);
      if (response.cached) {
        setLoadingLabel("Loading saved voice guidance...");
      }
      const binary = window.atob(response.audio_base64);
      const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
      const blob = new Blob([bytes], { type: response.media_type || "audio/wav" });
      const nextUrl = URL.createObjectURL(blob);

      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
      }
      objectUrlRef.current = nextUrl;

      const audio = new Audio(nextUrl);
      audio.preload = "auto";
      audio.addEventListener("ended", () => {
        setIsAudioPlaying(false);
        setAudioCurrentTime(0);
        audio.currentTime = 0;
      });
      audio.addEventListener("pause", () => {
        setIsAudioPlaying(false);
      });
      audio.addEventListener("play", () => {
        window.dispatchEvent(
          new CustomEvent(AUDIO_PLAY_EVENT, { detail: { key: audioKey } })
        );
        setIsAudioPlaying(true);
      });
      audio.addEventListener("loadedmetadata", () => {
        setAudioDuration(Number.isFinite(audio.duration) ? audio.duration : 0);
      });
      audio.addEventListener("timeupdate", () => {
        setAudioCurrentTime(audio.currentTime);
      });

      audioRef.current = audio;
      loadedAudioKeyRef.current = audioKey;
      setAudioCached(response.cached);
      await audio.play();
    } catch (error) {
      window.clearTimeout(slowGenerationTimer);
      setAudioError(getAudioErrorMessage(error));
      setIsAudioPlaying(false);
    } finally {
      setIsPreparingAudio(false);
    }
  }

  async function handleAudioClick() {
    if (isPreparingAudio) {
      return;
    }

    if (!audioRef.current || loadedAudioKeyRef.current !== audioKey) {
      await prepareAudio();
      return;
    }

    if (audioRef.current.paused) {
      try {
        await audioRef.current.play();
      } catch (error) {
        setAudioError(getAudioErrorMessage(error));
      }
      return;
    }

    audioRef.current.pause();
  }

  function handleSeek(value: string) {
    const nextTime = Number(value);
    if (!audioRef.current || !Number.isFinite(nextTime)) {
      return;
    }
    audioRef.current.currentTime = nextTime;
    setAudioCurrentTime(nextTime);
  }

  const audioProgress =
    audioDuration > 0 ? Math.min(100, (audioCurrentTime / audioDuration) * 100) : 0;
  const displaySimpleCue =
    simpleCue &&
    !areCoachingTextsSimilar(simpleCue, title) &&
    !areCoachingTextsSimilar(simpleCue, whatToFix)
      ? simpleCue
      : null;
  const displayBackupNote =
    backupNote &&
    !areCoachingTextsSimilar(backupNote, title) &&
    !areCoachingTextsSimilar(backupNote, whatToFix) &&
    !areCoachingTextsSimilar(backupNote, nextAction)
      ? backupNote
      : null;

  return (
    <InfoCard className="h-full border-white/10 p-5 sm:p-6">
      <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-start">
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
            Primary Performance Focus
          </p>
          <h3 className="mt-2 break-words font-display text-2xl font-bold leading-tight text-white">
            {title}
          </h3>
          {displaySimpleCue ? (
            <p className="mt-3 inline-flex max-w-full whitespace-normal break-words rounded-2xl border border-primary/20 bg-primary/10 px-3 py-1.5 text-left text-xs font-semibold leading-5 text-primary">
              {displaySimpleCue}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2 lg:justify-end">
          <Badge variant={isEnhanced ? "success" : "slate"}>
            {isEnhanced ? "AI refined" : "Rule-based"}
          </Badge>
          {severity ? (
            <Badge variant={getSeverityVariant(severity)}>
              {formatSeverityLabel(severity)}
            </Badge>
          ) : null}
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-primary/20 bg-[linear-gradient(135deg,rgba(255,122,0,0.13),rgba(255,255,255,0.035))] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[10px] uppercase tracking-[0.2em] text-primary">
              Voice guidance
            </p>
            <p className="mt-1 text-xs text-white/60">Voice: Coach</p>
          </div>
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary px-4 py-2 text-sm font-semibold text-background-dark transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-70"
            disabled={isPreparingAudio}
            onClick={() => {
              void handleAudioClick();
            }}
          >
            {isPreparingAudio ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : isAudioPlaying ? (
              <Pause className="h-4 w-4" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {isPreparingAudio
              ? loadingLabel
              : isAudioPlaying
                ? "Pause coaching"
                : audioRef.current
                  ? "Resume coaching"
                  : "Listen to coaching"}
          </button>
        </div>
        <div className="mt-4 rounded-full border border-white/10 bg-black/25 px-3 py-2">
          <div className="flex items-center gap-3">
            <span className="w-9 text-right text-[11px] tabular-nums text-white/55">
              {formatAudioTime(audioCurrentTime)}
            </span>
            <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-primary transition-[width] duration-150"
                style={{ width: `${audioProgress}%` }}
              />
              <input
                aria-label="Voice guidance progress"
                className="absolute inset-0 h-full w-full cursor-pointer opacity-0 disabled:cursor-default"
                disabled={!audioRef.current || audioDuration <= 0}
                max={audioDuration || 0}
                min={0}
                step={0.1}
                type="range"
                value={Math.min(audioCurrentTime, audioDuration || 0)}
                onChange={(event) => {
                  handleSeek(event.target.value);
                }}
              />
            </div>
            <span className="w-9 text-[11px] tabular-nums text-white/55">
              {formatAudioTime(audioDuration)}
            </span>
          </div>
        </div>
        {audioError ? (
          <p className="mt-3 text-xs leading-5 text-amber-100">{audioError}</p>
        ) : audioCached ? (
          <p className="mt-3 text-xs leading-5 text-white/50">
            Using saved voice guidance.
          </p>
        ) : null}
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
            Movement Observation
          </p>
          <p className="mt-2 text-sm leading-6 text-white/85">{whatHappened}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
            Performance Impact
          </p>
          <p className="mt-2 text-sm leading-6 text-white/85">{whyItHappened}</p>
        </div>
        <div className="rounded-2xl border border-primary/20 bg-primary/10 p-4">
          <p className="text-[10px] uppercase tracking-[0.2em] text-primary">
            Corrective Focus
          </p>
          <p className="mt-2 text-sm leading-6 text-white/90">{whatToFix}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
            Next Set Objective
          </p>
          <p className="mt-2 text-sm leading-6 text-white/85">{nextAction}</p>
        </div>
      </div>

      {displayBackupNote ? (
        <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.035] px-4 py-3 text-xs leading-5 text-white/60">
          <span className="font-semibold text-white">Technical Baseline:</span>{" "}
          {displayBackupNote}
        </div>
      ) : null}
    </InfoCard>
  );
}

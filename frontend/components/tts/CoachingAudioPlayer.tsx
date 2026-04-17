"use client";

import { Pause, Play, Square, Volume2 } from "lucide-react";
import { useEffect, useId, useMemo, useState } from "react";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { cn } from "../../lib/utils";

type PlaybackStatus = "idle" | "playing" | "paused";
type GlobalPlaybackState = {
  activeId: string | null;
  status: PlaybackStatus;
};

const listeners = new Set<(state: GlobalPlaybackState) => void>();

let currentUtterance: SpeechSynthesisUtterance | null = null;
let playbackState: GlobalPlaybackState = {
  activeId: null,
  status: "idle"
};

function emitPlaybackState(nextState: GlobalPlaybackState) {
  playbackState = nextState;
  listeners.forEach((listener) => listener(nextState));
}

function subscribeToPlayback(listener: (state: GlobalPlaybackState) => void) {
  listeners.add(listener);
  listener(playbackState);

  return () => {
    listeners.delete(listener);
  };
}

function stopGlobalPlayback() {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    return;
  }

  window.speechSynthesis.cancel();
  currentUtterance = null;
  emitPlaybackState({
    activeId: null,
    status: "idle"
  });
}

type CoachingAudioPlayerProps = {
  text: string;
  label?: string;
  className?: string;
  compact?: boolean;
};

export function CoachingAudioPlayer({
  text,
  label = "Play audio",
  className,
  compact = false
}: CoachingAudioPlayerProps) {
  const playbackId = useId();
  const [isSupported, setIsSupported] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [activeState, setActiveState] = useState<GlobalPlaybackState>(playbackState);

  const sanitizedText = useMemo(() => text.trim(), [text]);
  const isActive = activeState.activeId === playbackId;
  const isPlaying = isActive && activeState.status === "playing";
  const isPaused = isActive && activeState.status === "paused";

  useEffect(() => {
    setIsMounted(true);
    setIsSupported(
      typeof window !== "undefined" && "speechSynthesis" in window
    );

    return subscribeToPlayback(setActiveState);
  }, []);

  useEffect(() => {
    return () => {
      if (playbackState.activeId === playbackId) {
        stopGlobalPlayback();
      }
    };
  }, [playbackId]);

  function handlePlay() {
    if (!isSupported || !sanitizedText) {
      return;
    }

    if (isPaused) {
      window.speechSynthesis.resume();
      emitPlaybackState({
        activeId: playbackId,
        status: "playing"
      });
      return;
    }

    if (isPlaying) {
      return;
    }

    stopGlobalPlayback();

    const utterance = new SpeechSynthesisUtterance(sanitizedText);
    utterance.rate = 0.9;
    utterance.pitch = 1.0;
    utterance.onstart = () => {
      emitPlaybackState({
        activeId: playbackId,
        status: "playing"
      });
    };
    utterance.onpause = () => {
      emitPlaybackState({
        activeId: playbackId,
        status: "paused"
      });
    };
    utterance.onresume = () => {
      emitPlaybackState({
        activeId: playbackId,
        status: "playing"
      });
    };
    utterance.onend = () => {
      if (currentUtterance === utterance) {
        currentUtterance = null;
        emitPlaybackState({
          activeId: null,
          status: "idle"
        });
      }
    };
    utterance.onerror = () => {
      if (currentUtterance === utterance) {
        currentUtterance = null;
        emitPlaybackState({
          activeId: null,
          status: "idle"
        });
      }
    };

    currentUtterance = utterance;
    window.speechSynthesis.speak(utterance);
  }

  function handlePause() {
    if (!isSupported || !isPlaying) {
      return;
    }

    window.speechSynthesis.pause();
    emitPlaybackState({
      activeId: playbackId,
      status: "paused"
    });
  }

  function handleStop() {
    if (!isSupported || !isActive) {
      return;
    }

    stopGlobalPlayback();
  }

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.035] px-3 py-3",
        isPlaying && "border-primary/25 bg-primary/10 shadow-[0_0_0_1px_rgba(255,122,0,0.08)]",
        className
      )}
    >
      <div className="flex items-center gap-2">
        <div
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] text-white/80 transition-all duration-300",
            isPlaying && "animate-pulse border-primary/25 bg-primary/15 text-primary"
          )}
        >
          <Volume2 className="h-4 w-4" />
        </div>
        {!compact ? (
          <div>
            <p className="text-sm font-semibold text-white">{label}</p>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-gray">
              {isPlaying
                ? "Playing..."
                : isPaused
                  ? "Paused"
                  : isSupported
                    ? "Ready"
                    : "Unavailable"}
            </p>
          </div>
        ) : null}
      </div>

      <div className="ml-auto flex flex-wrap items-center gap-2">
        {!isSupported || !isMounted ? (
          <Badge variant="slate">Audio unavailable</Badge>
        ) : null}
        {isPlaying ? <Badge variant="accent">Playing…</Badge> : null}
        {isPaused ? <Badge variant="warning">Paused</Badge> : null}
        <Button
          type="button"
          size="sm"
          onClick={handlePlay}
          disabled={!isSupported || !isMounted || !sanitizedText}
          className="gap-2"
        >
          <Play className="h-4 w-4" />
          {isPaused ? "Resume" : "Play"}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={handlePause}
          disabled={!isPlaying}
          className="gap-2"
        >
          <Pause className="h-4 w-4" />
          Pause
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={handleStop}
          disabled={!isActive}
          className="gap-2"
        >
          <Square className="h-4 w-4" />
          Stop
        </Button>
      </div>
    </div>
  );
}

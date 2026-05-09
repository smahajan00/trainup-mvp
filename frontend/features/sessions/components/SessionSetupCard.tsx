import { AlertTriangle } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { Label } from "../../../components/ui/label";
import { Select } from "../../../components/ui/select";
import { formatEnumLabel } from "../../../lib/formatters";
import type { DrillDetail } from "../../../types/drills";
import type { SkillLevel } from "../../../types/profile";
import type {
  CameraView,
  DominantSide,
  SessionInputType
} from "../../../types/sessions";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { SectionTitle } from "../../app-shell/components/SectionTitle";
import {
  ACTIVE_SIDE_OPTIONS,
  getCameraViewOptions
} from "../session-setup-utils";

type SessionSetupCardProps = {
  drill: DrillDetail | null;
  drillName: string;
  sportName: string;
  skillLevel: SkillLevel;
  inputType: SessionInputType;
  cameraView: CameraView | "";
  dominantSide: DominantSide;
  isEditable: boolean;
  isLocked: boolean;
  hasChanges: boolean;
  isApplying?: boolean;
  setupError?: string | null;
  setupNotice?: string | null;
  usesFallbackSkillLevel?: boolean;
  onCameraViewChange: (value: CameraView) => void;
  onDominantSideChange: (value: DominantSide) => void;
  onApplyChanges: () => void;
};

export function SessionSetupCard({
  drill,
  drillName,
  sportName,
  skillLevel,
  inputType,
  cameraView,
  dominantSide,
  isEditable,
  isLocked,
  hasChanges,
  isApplying = false,
  setupError,
  setupNotice,
  usesFallbackSkillLevel = false,
  onCameraViewChange,
  onDominantSideChange,
  onApplyChanges
}: SessionSetupCardProps) {
  const cameraViewOptions = getCameraViewOptions(drill);
  const controlsDisabled = !isEditable || isLocked || isApplying;
  const lockCopy = isLocked
    ? "Setup is locked after capture starts."
    : isEditable
      ? "Changing setup before capture will restart this session with the new settings."
      : "This existing session is shown with the setup used at capture time.";

  return (
    <InfoCard>
      <SectionTitle
        eyebrow="Setup"
        title="Session setup"
        description="Confirm the capture angle and active side before recording."
      />

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">Drill</p>
          <p className="mt-3 line-clamp-2 break-words text-sm font-semibold text-white">
            {drillName}
          </p>
        </div>
        <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">Sport</p>
          <p className="mt-3 line-clamp-2 break-words text-sm font-semibold text-white">
            {sportName}
          </p>
        </div>
        <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
            Skill level
          </p>
          <p className="mt-3 line-clamp-2 break-words text-sm font-semibold text-white">
            {formatEnumLabel(skillLevel)}
          </p>
          {usesFallbackSkillLevel ? (
            <p className="mt-2 text-xs leading-5 text-muted-gray">
              Beginner is used for cross-sport training.
            </p>
          ) : null}
        </div>
        <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
            Training mode
          </p>
          <p className="mt-3 line-clamp-2 break-words text-sm font-semibold text-white">
            {inputType === "LIVE" ? "Live Camera" : "Upload Video"}
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor={`camera-view-${inputType.toLowerCase()}`}>
            Camera view
          </Label>
          <Select
            id={`camera-view-${inputType.toLowerCase()}`}
            value={cameraView}
            disabled={controlsDisabled}
            onChange={(event) => onCameraViewChange(event.target.value as CameraView)}
          >
            {cameraViewOptions.map((view) => (
              <option key={view} value={view} className="bg-slate text-white">
                {formatEnumLabel(view)}
              </option>
            ))}
          </Select>
          <p className="text-sm leading-6 text-muted-gray">
            Use the recommended camera angle for the most reliable analysis.
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor={`active-side-${inputType.toLowerCase()}`}>
            Active side
          </Label>
          <Select
            id={`active-side-${inputType.toLowerCase()}`}
            value={dominantSide}
            disabled={controlsDisabled}
            onChange={(event) =>
              onDominantSideChange(event.target.value as DominantSide)
            }
          >
            {ACTIVE_SIDE_OPTIONS.map((option) => (
              <option
                key={option.value}
                value={option.value}
                className="bg-slate text-white"
              >
                {option.label}
              </option>
            ))}
          </Select>
          <p className="text-sm leading-6 text-muted-gray">
            Auto-detect lets TrainUp resolve the active side from movement.
          </p>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4">
        <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
          Capture protocol tips
        </p>
        <p className="mt-3 text-sm leading-6 text-white/85">
          {drill?.reference_payload.notes ||
            "Keep the full movement in frame with steady lighting and a stable camera."}
        </p>
      </div>

      {setupError ? (
        <div className="mt-5 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-4 text-sm leading-7 text-rose-100">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{setupError}</span>
          </div>
        </div>
      ) : null}

      {setupNotice ? (
        <div className="mt-5 rounded-2xl border border-primary/25 bg-primary/10 px-4 py-4 text-sm leading-7 text-primary">
          {setupNotice}
        </div>
      ) : null}

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Badge variant={isLocked ? "warning" : isEditable ? "accent" : "slate"}>
          {isLocked ? "Locked" : isEditable ? "Editable before capture" : "Read-only"}
        </Badge>
        <p className="max-w-2xl text-sm leading-6 text-muted-gray">{lockCopy}</p>
        {isEditable && !isLocked ? (
          <Button
            type="button"
            variant={hasChanges ? "default" : "outline"}
            onClick={onApplyChanges}
            disabled={!hasChanges || isApplying}
            className="ml-0 lg:ml-auto"
          >
            {isApplying ? "Applying setup" : "Apply setup changes"}
          </Button>
        ) : null}
      </div>
    </InfoCard>
  );
}

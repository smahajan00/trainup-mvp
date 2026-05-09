import type { DrillDetail } from "../../types/drills";
import type { ProfileResponse, SkillLevel } from "../../types/profile";
import type {
  CameraView,
  DominantSide,
  SessionCreateRequest,
  SessionInputType,
  StoredDominantSide,
  TrainingSession
} from "../../types/sessions";

export const DEFAULT_CAMERA_VIEWS: CameraView[] = [
  "FRONTAL",
  "LEFT_SAGITTAL",
  "RIGHT_SAGITTAL"
];

export const DEFAULT_CAMERA_VIEW: CameraView = "FRONTAL";

export const ACTIVE_SIDE_OPTIONS: { value: DominantSide; label: string }[] = [
  { value: "AUTO", label: "Auto-detect" },
  { value: "LEFT", label: "Left" },
  { value: "RIGHT", label: "Right" }
];

export function resolveCameraView(
  drill: DrillDetail | null,
  preferredCameraView?: CameraView | null
): CameraView {
  if (
    preferredCameraView &&
    (drill?.allowed_camera_views.includes(preferredCameraView) ?? true)
  ) {
    return preferredCameraView;
  }

  return (
    drill?.canonical_view ??
    drill?.allowed_camera_views[0] ??
    DEFAULT_CAMERA_VIEW
  );
}

export function getCameraViewOptions(drill: DrillDetail | null): CameraView[] {
  return drill?.allowed_camera_views.length
    ? drill.allowed_camera_views
    : DEFAULT_CAMERA_VIEWS;
}

export function resolveDominantSide(
  dominantSide?: StoredDominantSide | null
): DominantSide {
  return dominantSide ?? "AUTO";
}

export function toStoredDominantSide(
  dominantSide: DominantSide
): StoredDominantSide | null {
  return dominantSide === "AUTO" ? null : dominantSide;
}

export function resolveSkillLevelForDrill(
  profile: ProfileResponse | null,
  drill: DrillDetail | null,
  fallbackSkillLevel: SkillLevel = "BEGINNER"
): SkillLevel {
  if (profile && drill && profile.sport_id === drill.sport_id) {
    return profile.skill_level;
  }

  return fallbackSkillLevel;
}

export function usesFallbackSkillLevel(
  profile: ProfileResponse | null,
  drill: DrillDetail | null
) {
  return !profile || !drill || profile.sport_id !== drill.sport_id;
}

export function buildSessionCreatePayload({
  drill,
  profile,
  inputType,
  cameraView,
  dominantSide,
  fallbackSkillLevel = "BEGINNER"
}: {
  drill: DrillDetail;
  profile: ProfileResponse | null;
  inputType: SessionInputType;
  cameraView?: CameraView | null;
  dominantSide?: DominantSide;
  fallbackSkillLevel?: SkillLevel;
}): SessionCreateRequest {
  return {
    sport_id: drill.sport_id,
    drill_id: drill.id,
    skill_level: resolveSkillLevelForDrill(profile, drill, fallbackSkillLevel),
    input_type: inputType,
    camera_view: resolveCameraView(drill, cameraView),
    dominant_side: toStoredDominantSide(dominantSide ?? "AUTO")
  };
}

export function buildReplacementSessionPayload({
  session,
  drill,
  profile,
  cameraView,
  dominantSide
}: {
  session: TrainingSession;
  drill: DrillDetail | null;
  profile: ProfileResponse | null;
  cameraView: CameraView;
  dominantSide: DominantSide;
}): SessionCreateRequest {
  return drill
    ? buildSessionCreatePayload({
        drill,
        profile,
        inputType: session.input_type,
        cameraView,
        dominantSide
      })
    : {
        sport_id: session.sport_id,
        drill_id: session.drill_id,
        skill_level: session.skill_level,
        input_type: session.input_type,
        camera_view: cameraView,
        dominant_side: toStoredDominantSide(dominantSide)
      };
}

export function validateSessionSetup({
  drill,
  cameraView,
  dominantSide
}: {
  drill: DrillDetail | null;
  cameraView: CameraView | "";
  dominantSide: DominantSide;
}) {
  if (!cameraView) {
    return "Choose a camera view before continuing.";
  }

  if (drill && !getCameraViewOptions(drill).includes(cameraView)) {
    return "Choose a supported camera view for this drill.";
  }

  if (
    drill?.requires_dominant_side &&
    !drill.supports_active_side_selection &&
    dominantSide === "AUTO"
  ) {
    return "Choose Left or Right for this drill before continuing.";
  }

  return null;
}

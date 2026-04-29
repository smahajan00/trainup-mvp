import { apiRequest } from "../lib/api";
import type {
  DrillCaptureProtocol,
  DrillDetail,
  DrillDetailResponse,
  DrillListItem
} from "../types/drills";
import type { CameraView } from "../types/sessions";

const DEFAULT_CAMERA_VIEWS: CameraView[] = [
  "FRONTAL",
  "LEFT_SAGITTAL",
  "RIGHT_SAGITTAL"
];

const DRILLS_REQUIRING_DOMINANT_SIDE = new Set(["Set Shot Form"]);
const DRILLS_SUPPORTING_ACTIVE_SIDE_SELECTION = new Set([
  "Set Shot Form",
  "Instep Pass",
  "Basic Shooting Form"
]);

function isCameraView(value: string): value is CameraView {
  return DEFAULT_CAMERA_VIEWS.includes(value as CameraView);
}

function normalizeCaptureProtocol(
  protocol: DrillDetailResponse["reference_payload"]["capture_protocol"]
): DrillCaptureProtocol | null {
  if (!protocol) {
    return null;
  }

  const allowed_camera_views = protocol.allowed_camera_views.filter(isCameraView);
  const canonical_view = isCameraView(protocol.canonical_view)
    ? protocol.canonical_view
    : allowed_camera_views[0];

  if (!canonical_view) {
    return null;
  }

  return {
    required: protocol.required,
    allowed_camera_views:
      allowed_camera_views.length > 0 ? allowed_camera_views : [canonical_view],
    canonical_view
  };
}

function normalizeDrillDetail(drill: DrillDetailResponse): DrillDetail {
  const capture_protocol = normalizeCaptureProtocol(
    drill.reference_payload.capture_protocol
  );
  const requires_dominant_side =
    Boolean(drill.reference_payload.requires_dominant_side) ||
    DRILLS_REQUIRING_DOMINANT_SIDE.has(drill.drill_name);

  return {
    ...drill,
    capture_protocol,
    allowed_camera_views:
      capture_protocol?.allowed_camera_views.length
        ? capture_protocol.allowed_camera_views
        : DEFAULT_CAMERA_VIEWS,
    canonical_view:
      capture_protocol?.canonical_view ??
      capture_protocol?.allowed_camera_views[0] ??
      DEFAULT_CAMERA_VIEWS[0],
    requires_dominant_side,
    supports_active_side_selection:
      requires_dominant_side ||
      DRILLS_SUPPORTING_ACTIVE_SIDE_SELECTION.has(drill.drill_name)
  };
}

export function getDrillsBySport(sportId: string) {
  return apiRequest<DrillListItem[]>(`/sports/${sportId}/drills`);
}

export async function getDrillById(drillId: string) {
  const drill = await apiRequest<DrillDetailResponse>(`/drills/${drillId}`);
  return normalizeDrillDetail(drill);
}

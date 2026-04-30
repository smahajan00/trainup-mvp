import type {
  PoseFrame,
  PoseLandmarkCoordinate,
  PoseSequence
} from "../../../types/sessions";

export type PoseOverlayLandmark = PoseLandmarkCoordinate & {
  z?: number;
};

export type PoseOverlayLandmarkRecord = Record<string, PoseOverlayLandmark>;

export type PoseOverlayDrawResult = {
  visibleLandmarks: number;
  drawnConnections: number;
  lowerBodyLandmarks: number;
  fullBodyDetected: boolean;
};

export type VideoRenderBox = {
  left: number;
  top: number;
  width: number;
  height: number;
};

export const MEDIAPIPE_POSE_LANDMARK_NAMES = [
  "nose",
  "left_eye_inner",
  "left_eye",
  "left_eye_outer",
  "right_eye_inner",
  "right_eye",
  "right_eye_outer",
  "left_ear",
  "right_ear",
  "mouth_left",
  "mouth_right",
  "left_shoulder",
  "right_shoulder",
  "left_elbow",
  "right_elbow",
  "left_wrist",
  "right_wrist",
  "left_pinky",
  "right_pinky",
  "left_index",
  "right_index",
  "left_thumb",
  "right_thumb",
  "left_hip",
  "right_hip",
  "left_knee",
  "right_knee",
  "left_ankle",
  "right_ankle",
  "left_heel",
  "right_heel",
  "left_foot_index",
  "right_foot_index"
] as const;

export const POSE_SKELETON_CONNECTIONS: Array<[string, string]> = [
  ["left_shoulder", "right_shoulder"],
  ["left_shoulder", "left_elbow"],
  ["left_elbow", "left_wrist"],
  ["right_shoulder", "right_elbow"],
  ["right_elbow", "right_wrist"],
  ["left_shoulder", "left_hip"],
  ["right_shoulder", "right_hip"],
  ["left_hip", "right_hip"],
  ["left_hip", "left_knee"],
  ["left_knee", "left_ankle"],
  ["right_hip", "right_knee"],
  ["right_knee", "right_ankle"],
  ["left_ankle", "left_heel"],
  ["left_heel", "left_foot_index"],
  ["left_ankle", "left_foot_index"],
  ["right_ankle", "right_heel"],
  ["right_heel", "right_foot_index"],
  ["right_ankle", "right_foot_index"]
];

const MIN_VISIBILITY = 0.45;
const FALLBACK_CANVAS_WIDTH = 1280;
const FALLBACK_CANVAS_HEIGHT = 720;
const LOWER_BODY_LANDMARKS = [
  "left_hip",
  "right_hip",
  "left_knee",
  "right_knee",
  "left_ankle",
  "right_ankle"
];

export function resizeCanvasToVideo(
  video: HTMLVideoElement,
  canvas: HTMLCanvasElement
) {
  const dpr = window.devicePixelRatio || 1;
  const width = video.clientWidth || video.videoWidth || FALLBACK_CANVAS_WIDTH;
  const height = video.clientHeight || video.videoHeight || FALLBACK_CANVAS_HEIGHT;
  const targetWidth = Math.max(1, Math.round(width * dpr));
  const targetHeight = Math.max(1, Math.round(height * dpr));

  if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
    canvas.width = targetWidth;
    canvas.height = targetHeight;
  }
}

export function clearPoseCanvas(canvas: HTMLCanvasElement) {
  const context = canvas.getContext("2d");
  if (!context) {
    return;
  }

  context.clearRect(0, 0, canvas.width, canvas.height);
}

export function getContainedVideoRenderBox(
  video: HTMLVideoElement,
  canvas: HTMLCanvasElement
): VideoRenderBox {
  const videoWidth = video.videoWidth || FALLBACK_CANVAS_WIDTH;
  const videoHeight = video.videoHeight || FALLBACK_CANVAS_HEIGHT;
  const scale = Math.min(canvas.width / videoWidth, canvas.height / videoHeight);
  const width = videoWidth * scale;
  const height = videoHeight * scale;

  return {
    left: (canvas.width - width) / 2,
    top: (canvas.height - height) / 2,
    width,
    height
  };
}

export function drawPoseDebugMarker(canvas: HTMLCanvasElement) {
  const context = canvas.getContext("2d");
  if (!context) {
    return;
  }

  const radius = Math.max(5, canvas.width * 0.005);
  const x = canvas.width - radius * 3;
  const y = radius * 3;

  context.save();
  context.shadowColor = "rgba(255, 122, 0, 0.9)";
  context.shadowBlur = 12;
  context.fillStyle = "rgba(255, 122, 0, 0.95)";
  context.strokeStyle = "rgba(17, 17, 17, 0.75)";
  context.lineWidth = Math.max(2, canvas.width * 0.0015);
  context.beginPath();
  context.arc(x, y, radius, 0, Math.PI * 2);
  context.fill();
  context.stroke();
  context.restore();
}

export function normalizeLandmarkArray(
  landmarks: PoseOverlayLandmark[]
): PoseOverlayLandmarkRecord {
  return landmarks.reduce<PoseOverlayLandmarkRecord>((record, landmark, index) => {
    const name = MEDIAPIPE_POSE_LANDMARK_NAMES[index];
    if (name) {
      record[name] = landmark;
    }
    return record;
  }, {});
}

export function isRenderablePoseFrame(frame: PoseFrame | null | undefined) {
  return Boolean(
    frame?.frame_valid &&
      frame.landmarks &&
      Object.keys(frame.landmarks).length > 0
  );
}

export function getValidPoseFrames(poseSequence: PoseSequence | null | undefined) {
  if (!poseSequence?.sequence_data?.length) {
    return [];
  }

  return poseSequence.sequence_data
    .filter((frame) => isRenderablePoseFrame(frame))
    .sort((left, right) => left.timestamp_ms - right.timestamp_ms);
}

export function getPoseFrameToleranceMs(frames: PoseFrame[]) {
  if (frames.length <= 1) {
    return 500;
  }

  const deltas = frames
    .slice(1)
    .map((frame, index) => frame.timestamp_ms - frames[index].timestamp_ms)
    .filter((delta) => delta > 0)
    .sort((left, right) => left - right);

  const medianDelta = deltas[Math.floor(deltas.length / 2)] ?? 66;
  return Math.max(180, medianDelta * 3);
}

export function findClosestPoseFrame(
  frames: PoseFrame[],
  timestampMs: number,
  toleranceMs = getPoseFrameToleranceMs(frames)
) {
  if (!frames.length) {
    return null;
  }

  let low = 0;
  let high = frames.length - 1;

  while (low <= high) {
    const middle = Math.floor((low + high) / 2);
    if (frames[middle].timestamp_ms < timestampMs) {
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }

  const candidates = [frames[low], frames[low - 1]].filter(
    (frame): frame is PoseFrame => Boolean(frame)
  );
  const closest = candidates.reduce<PoseFrame | null>((currentClosest, frame) => {
    if (!currentClosest) {
      return frame;
    }

    return Math.abs(frame.timestamp_ms - timestampMs) <
      Math.abs(currentClosest.timestamp_ms - timestampMs)
      ? frame
      : currentClosest;
  }, null);

  if (!closest || Math.abs(closest.timestamp_ms - timestampMs) > toleranceMs) {
    return null;
  }

  return closest;
}

function getCanvasPoint(
  landmark: PoseOverlayLandmark,
  renderBox: VideoRenderBox,
  mirrored: boolean
) {
  const normalizedX = mirrored ? 1 - landmark.x : landmark.x;

  return {
    x: renderBox.left + normalizedX * renderBox.width,
    y: renderBox.top + landmark.y * renderBox.height
  };
}

function canDrawLandmark(landmark: PoseOverlayLandmark | undefined) {
  if (!landmark) {
    return false;
  }

  if (!Number.isFinite(landmark.x) || !Number.isFinite(landmark.y)) {
    return false;
  }

  if (landmark.x < 0 || landmark.x > 1 || landmark.y < 0 || landmark.y > 1) {
    return false;
  }

  return (landmark.visibility ?? 1) >= MIN_VISIBILITY;
}

export function drawPoseSkeleton({
  canvas,
  landmarks,
  mirrored = false,
  renderBox
}: {
  canvas: HTMLCanvasElement;
  landmarks: PoseOverlayLandmarkRecord;
  mirrored?: boolean;
  renderBox?: VideoRenderBox;
}): PoseOverlayDrawResult {
  const context = canvas.getContext("2d");
  if (!context) {
    return {
      visibleLandmarks: 0,
      drawnConnections: 0,
      lowerBodyLandmarks: 0,
      fullBodyDetected: false
    };
  }

  clearPoseCanvas(canvas);

  const activeRenderBox = renderBox ?? {
    left: 0,
    top: 0,
    width: canvas.width,
    height: canvas.height
  };
  const visibleNames = Object.keys(landmarks).filter((name) =>
    canDrawLandmark(landmarks[name])
  );
  const lowerBodyLandmarks = LOWER_BODY_LANDMARKS.filter((name) =>
    canDrawLandmark(landmarks[name])
  ).length;

  context.save();
  context.lineCap = "round";
  context.lineJoin = "round";
  context.shadowColor = "rgba(255, 122, 0, 0.65)";
  context.shadowBlur = 14;
  context.strokeStyle = "rgba(255, 122, 0, 0.88)";
  context.lineWidth = Math.max(3, canvas.width * 0.003);

  let drawnConnections = 0;
  for (const [fromName, toName] of POSE_SKELETON_CONNECTIONS) {
    const from = landmarks[fromName];
    const to = landmarks[toName];

    if (!canDrawLandmark(from) || !canDrawLandmark(to)) {
      continue;
    }

    const fromPoint = getCanvasPoint(from, activeRenderBox, mirrored);
    const toPoint = getCanvasPoint(to, activeRenderBox, mirrored);

    context.beginPath();
    context.moveTo(fromPoint.x, fromPoint.y);
    context.lineTo(toPoint.x, toPoint.y);
    context.stroke();
    drawnConnections += 1;
  }

  context.fillStyle = "rgba(255, 174, 82, 0.96)";
  context.strokeStyle = "rgba(17, 17, 17, 0.72)";
  context.lineWidth = Math.max(2, canvas.width * 0.0017);

  for (const name of visibleNames) {
    const point = getCanvasPoint(landmarks[name], activeRenderBox, mirrored);
    const radius = Math.max(4, canvas.width * 0.0042);

    context.beginPath();
    context.arc(point.x, point.y, radius, 0, Math.PI * 2);
    context.fill();
    context.stroke();
  }

  context.restore();

  return {
    visibleLandmarks: visibleNames.length,
    drawnConnections,
    lowerBodyLandmarks,
    fullBodyDetected: lowerBodyLandmarks >= 4
  };
}

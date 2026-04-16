const ALLOWED_VIDEO_CONTENT_TYPES = new Set([
  "video/mp4",
  "video/quicktime",
  "video/webm",
  "video/x-matroska"
]);

const MAX_UPLOAD_FILE_SIZE_BYTES = 100 * 1024 * 1024;

export type LocalVideoValidation = {
  isValid: boolean;
  warnings: string[];
  errors: string[];
};

export function validateVideoFile(file: File): LocalVideoValidation {
  const warnings: string[] = [];
  const errors: string[] = [];

  if (!file.name.trim()) {
    errors.push("Select a video file before submitting.");
  }

  if (!ALLOWED_VIDEO_CONTENT_TYPES.has(file.type)) {
    errors.push("Use MP4, MOV, WEBM, or MKV video formats.");
  }

  if (file.size <= 0) {
    errors.push("The selected file does not contain video data.");
  }

  if (file.size > MAX_UPLOAD_FILE_SIZE_BYTES) {
    errors.push("Video files must be 100 MB or smaller for this MVP flow.");
  }

  if (!/\.(mp4|m4v|mov|qt|webm|mkv)$/i.test(file.name)) {
    warnings.push("The file extension is unusual for a supported video format.");
  }

  return {
    isValid: errors.length === 0,
    warnings,
    errors
  };
}

export function formatEnumLabel(value: string) {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatTokenLabel(value: string) {
  return value
    .split(/[_-]/g)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function truncateText(value: string | null | undefined, maxLength = 160) {
  if (!value) {
    return "";
  }

  if (value.length <= maxLength) {
    return value;
  }

  return `${value.slice(0, maxLength).trimEnd()}...`;
}

export function calculateProfileCompletion(profile: {
  sport_id?: string | null;
  skill_level?: string | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  injury_notes?: string | null;
} | null) {
  if (!profile) {
    return 0;
  }

  const completedFields = [
    Boolean(profile.sport_id),
    Boolean(profile.skill_level),
    Boolean(profile.height_cm),
    Boolean(profile.weight_kg),
    Boolean(profile.injury_notes)
  ].filter(Boolean).length;

  return Math.round((completedFields / 5) * 100);
}

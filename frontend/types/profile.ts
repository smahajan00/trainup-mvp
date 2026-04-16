export type SkillLevel = "BEGINNER" | "INTERMEDIATE" | "ADVANCED";

export type ProfileResponse = {
  id: string;
  user_id: string;
  sport_id: string;
  sport_name: string;
  height_cm: number | null;
  weight_kg: number | null;
  skill_level: SkillLevel;
  injury_notes: string | null;
  created_at: string;
};

export type ProfileEnvelopeResponse = {
  profile: ProfileResponse | null;
};

export type ProfileUpsertRequest = {
  sport_id: string;
  height_cm?: number;
  weight_kg?: number;
  skill_level: SkillLevel;
  injury_notes?: string | null;
};

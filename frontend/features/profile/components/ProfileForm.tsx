"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Activity } from "lucide-react";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { Select } from "../../../components/ui/select";
import { Textarea } from "../../../components/ui/textarea";
import { SkeletonLoader } from "../../../components/ui/skeleton-loader";
import { EmptyState } from "../../app-shell/components/EmptyState";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { ApiError, getErrorMessage } from "../../../lib/api";
import { clearAuthToken } from "../../../lib/auth";
import { getProfile, upsertProfile } from "../../../services/profile";
import { getSports } from "../../../services/sports";
import type { SkillLevel } from "../../../types/profile";
import type { SportOption } from "../../../types/sports";

const skillLevels: { value: SkillLevel; label: string }[] = [
  { value: "BEGINNER", label: "Beginner" },
  { value: "INTERMEDIATE", label: "Intermediate" },
  { value: "ADVANCED", label: "Advanced" }
];

const profileSchema = z.object({
  sport_id: z.string().uuid("Select a sport."),
  skill_level: z.enum(["BEGINNER", "INTERMEDIATE", "ADVANCED"]),
  height_cm: z.number().positive("Height must be greater than 0.").optional(),
  weight_kg: z.number().positive("Weight must be greater than 0.").optional(),
  injury_notes: z
    .string()
    .trim()
    .max(2000, "Injury notes must be 2000 characters or less.")
    .optional()
});

type ProfileFormValues = z.infer<typeof profileSchema>;

export function ProfileForm({ embedded = false }: { embedded?: boolean }) {
  const router = useRouter();
  const [sports, setSports] = useState<SportOption[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "success">("idle");
  const [hasExistingProfile, setHasExistingProfile] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting }
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      sport_id: "",
      skill_level: "BEGINNER",
      height_cm: undefined,
      weight_kg: undefined,
      injury_notes: ""
    }
  });

  useEffect(() => {
    let ignore = false;

    async function hydrateForm() {
      setLoadError(null);
      try {
        const [profileResult, sportsResult] = await Promise.all([
          getProfile(),
          getSports()
        ]);

        if (ignore) {
          return;
        }

        setSports(sportsResult);

        if (profileResult.profile) {
          setHasExistingProfile(true);
          reset({
            sport_id: profileResult.profile.sport_id,
            skill_level: profileResult.profile.skill_level,
            height_cm: profileResult.profile.height_cm ?? undefined,
            weight_kg: profileResult.profile.weight_kg ?? undefined,
            injury_notes: profileResult.profile.injury_notes ?? ""
          });
        }
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          clearAuthToken();
          router.replace("/login");
          return;
        }

        if (!ignore) {
          setLoadError(getErrorMessage(error));
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    hydrateForm();

    return () => {
      ignore = true;
    };
  }, [reset, router]);

  const onSubmit = handleSubmit(async (values) => {
    setLoadError(null);
    setSaveState("idle");

    try {
      router.prefetch("/dashboard");
      await upsertProfile({
        sport_id: values.sport_id,
        skill_level: values.skill_level,
        height_cm: values.height_cm,
        weight_kg: values.weight_kg,
        injury_notes: values.injury_notes || null
      });
      setSaveState("success");
      window.setTimeout(() => {
        router.push("/dashboard");
      }, 850);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearAuthToken();
        router.replace("/login");
        return;
      }

      setLoadError(getErrorMessage(error));
    }
  });

  if (isLoading) {
    return embedded ? (
      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <SkeletonLoader className="h-[560px]" />
        <div className="space-y-6">
          <SkeletonLoader className="h-56" />
          <SkeletonLoader className="h-56" />
        </div>
      </div>
    ) : (
      <main className="flex min-h-screen items-center justify-center bg-background-dark px-6 py-10">
        <div className="rounded-2xl border border-white/10 bg-charcoal/70 px-6 py-5 text-sm text-muted-gray backdrop-blur">
          Loading your athlete profile...
        </div>
      </main>
    );
  }

  const content = (
    <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
      <InfoCard className="relative overflow-hidden border-primary/15">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.14),_transparent_38%)]" />
        <form className="relative z-10 space-y-6" onSubmit={onSubmit}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <Badge variant="accent">
                {hasExistingProfile ? "Profile Update" : "Profile Setup"}
              </Badge>
              <h2 className="mt-4 font-display text-3xl font-bold text-white">
                Set your athlete profile
              </h2>
              <p className="mt-3 max-w-2xl text-sm text-muted-gray">
                Keep your training context current.
              </p>
            </div>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="sport_id">Sport</Label>
              <Select id="sport_id" {...register("sport_id")}>
                <option value="" className="bg-slate text-white">
                  Select a sport
                </option>
                {sports.map((sport) => (
                  <option
                    key={sport.id}
                    value={sport.id}
                    className="bg-slate text-white"
                  >
                    {sport.sport_name}
                  </option>
                ))}
              </Select>
              {errors.sport_id ? (
                <p className="text-sm text-red-300">{errors.sport_id.message}</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="skill_level">Skill level</Label>
              <Select id="skill_level" {...register("skill_level")}>
                {skillLevels.map((level) => (
                  <option
                    key={level.value}
                    value={level.value}
                    className="bg-slate text-white"
                  >
                    {level.label}
                  </option>
                ))}
              </Select>
              {errors.skill_level ? (
                <p className="text-sm text-red-300">
                  {errors.skill_level.message}
                </p>
              ) : null}
            </div>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="height_cm">Height (cm)</Label>
              <Input
                id="height_cm"
                type="number"
                step="0.1"
                min="0"
                placeholder="180"
                {...register("height_cm", {
                  setValueAs: (value) =>
                    value === "" ? undefined : Number(value)
                })}
              />
              {errors.height_cm ? (
                <p className="text-sm text-red-300">
                  {errors.height_cm.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="weight_kg">Weight (kg)</Label>
              <Input
                id="weight_kg"
                type="number"
                step="0.1"
                min="0"
                placeholder="78"
                {...register("weight_kg", {
                  setValueAs: (value) =>
                    value === "" ? undefined : Number(value)
                })}
              />
              {errors.weight_kg ? (
                <p className="text-sm text-red-300">
                  {errors.weight_kg.message}
                </p>
              ) : null}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="injury_notes">Injury notes</Label>
            <Textarea
              id="injury_notes"
              placeholder="Optional: current restrictions or pain points."
              {...register("injury_notes")}
            />
            {errors.injury_notes ? (
              <p className="text-sm text-red-300">
                {errors.injury_notes.message}
              </p>
            ) : null}
          </div>

          {loadError ? (
            <div className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {loadError}
            </div>
          ) : null}

          {saveState === "success" ? (
            <div className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
              Profile saved. Opening dashboard...
            </div>
          ) : null}

          <div className="flex flex-col gap-3 border-t border-white/10 pt-6 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-muted-gray">
              You can update this anytime.
            </p>
            <Button size="lg" disabled={isSubmitting || saveState === "success"}>
              {isSubmitting
                ? "Saving profile..."
                : saveState === "success"
                  ? "Saved"
                  : "Save Profile"}
            </Button>
          </div>
        </form>
      </InfoCard>

      <div className="space-y-6">
        <InfoCard>
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
                Quick Notes
              </p>
              <h3 className="mt-3 font-display text-2xl font-bold text-white">
                Keep it simple
              </h3>
              <ul className="mt-4 space-y-2 text-sm text-muted-gray">
                <li>• Pick your main sport</li>
                <li>• Set your current level</li>
                <li>• Add notes if needed</li>
              </ul>
            </div>
          </div>
        </InfoCard>
      </div>
    </div>
  );

  if (embedded) {
    return content;
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-background-dark px-6 py-10">
      {content}
    </main>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { Select } from "../../../components/ui/select";
import { Textarea } from "../../../components/ui/textarea";
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

export function ProfileForm() {
  const router = useRouter();
  const [sports, setSports] = useState<SportOption[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
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

    try {
      await upsertProfile({
        sport_id: values.sport_id,
        skill_level: values.skill_level,
        height_cm: values.height_cm,
        weight_kg: values.weight_kg,
        injury_notes: values.injury_notes || null
      });
      router.push("/dashboard");
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
    return (
      <main className="flex min-h-screen items-center justify-center bg-background-dark px-6 py-10">
        <div className="rounded-2xl border border-white/10 bg-charcoal/70 px-6 py-5 text-sm text-muted-gray backdrop-blur">
          Loading your athlete profile...
        </div>
      </main>
    );
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-background-dark px-6 py-10">
      <div
        className="absolute inset-0 bg-hero-grid opacity-60"
        style={{ backgroundSize: "auto, 72px 72px, 72px 72px" }}
      />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,122,0,0.16),_transparent_36%),radial-gradient(circle_at_bottom_right,_rgba(255,255,255,0.05),_transparent_28%)]" />

      <section className="relative z-10 mx-auto w-full max-w-3xl rounded-[2rem] border border-white/10 bg-charcoal/72 p-8 shadow-glow backdrop-blur lg:p-10">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-primary">
              Athlete Profile
            </p>
            <h1 className="mt-3 font-display text-4xl font-bold text-white">
              Build your sport context
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-gray sm:text-base">
              TrainUp uses this profile to anchor future coaching logic around
              the athlete’s sport, current level, and movement constraints.
            </p>
          </div>
          <Link
            href="/dashboard"
            className="text-sm font-semibold text-primary transition-colors hover:text-primary/80"
          >
            Back to dashboard
          </Link>
        </div>

        <form className="mt-8 space-y-6" onSubmit={onSubmit}>
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
              placeholder="Optional: note current restrictions, pain points, or return-to-play context."
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

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-muted-gray">
              Your profile remains editable, so you can adjust sport context and
              physical data as training needs change.
            </p>
            <Button size="lg" disabled={isSubmitting}>
              {isSubmitting ? "Saving profile..." : "Save Profile"}
            </Button>
          </div>
        </form>
      </section>
    </main>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "../../components/ui/button";
import { ApiError, getErrorMessage } from "../../lib/api";
import { clearAuthToken } from "../../lib/auth";
import { ProtectedRoute } from "../../features/auth/components/ProtectedRoute";
import { getCurrentUser } from "../../services/auth";
import { getProfile } from "../../services/profile";
import type { CurrentUserResponse } from "../../types/auth";
import type { ProfileResponse } from "../../types/profile";

function formatSkillLevel(value: string) {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function DashboardContent() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUserResponse | null>(null);
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let ignore = false;

    async function loadDashboard() {
      setError(null);
      try {
        const [currentUser, profileResult] = await Promise.all([
          getCurrentUser(),
          getProfile()
        ]);

        if (ignore) {
          return;
        }

        setUser(currentUser);
        setProfile(profileResult.profile);
      } catch (loadError) {
        if (loadError instanceof ApiError && loadError.status === 401) {
          clearAuthToken();
          router.replace("/login");
          return;
        }

        if (!ignore) {
          setError(getErrorMessage(loadError));
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    loadDashboard();

    return () => {
      ignore = true;
    };
  }, [router]);

  const handleLogout = () => {
    clearAuthToken();
    router.replace("/login");
  };

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background-dark px-6 py-10">
        <div className="rounded-2xl border border-white/10 bg-charcoal/70 px-6 py-5 text-sm text-muted-gray backdrop-blur">
          Loading your dashboard...
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

      <section className="relative z-10 mx-auto w-full max-w-5xl rounded-[2rem] border border-white/10 bg-charcoal/72 p-8 shadow-glow backdrop-blur lg:p-10">
        <div className="flex flex-col gap-4 border-b border-white/10 pb-8 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-primary">
              Dashboard
            </p>
            <h1 className="mt-3 font-display text-4xl font-bold text-white">
              Welcome back{user ? `, ${user.full_name}` : ""}.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-gray sm:text-base">
              This protected workspace is the baseline post-login landing page
              for TrainUp. Your athlete profile is shown here until training,
              analysis, and performance modules are added in later phases.
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" asChild>
              <Link href="/profile">Edit Profile</Link>
            </Button>
            <Button variant="ghost" onClick={handleLogout}>
              Logout
            </Button>
          </div>
        </div>

        {error ? (
          <div className="mt-8 rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        ) : null}

        <div className="mt-8 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-6">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-primary">
              Account
            </p>
            <div className="mt-5 space-y-4">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                  Full name
                </p>
                <p className="mt-2 text-lg font-semibold text-white">
                  {user?.full_name ?? "Unknown user"}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                  Email
                </p>
                <p className="mt-2 text-base text-white/90">{user?.email}</p>
              </div>
            </div>
          </div>

          <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-6">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-primary">
              Athlete Context
            </p>
            {profile ? (
              <div className="mt-5 space-y-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                    Selected sport
                  </p>
                  <p className="mt-2 text-lg font-semibold text-white">
                    {profile.sport_name}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                    Skill level
                  </p>
                  <p className="mt-2 text-base text-white/90">
                    {formatSkillLevel(profile.skill_level)}
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                      Height
                    </p>
                    <p className="mt-2 text-base text-white/90">
                      {profile.height_cm ? `${profile.height_cm} cm` : "Not set"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                      Weight
                    </p>
                    <p className="mt-2 text-base text-white/90">
                      {profile.weight_kg ? `${profile.weight_kg} kg` : "Not set"}
                    </p>
                  </div>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-gray">
                    Injury notes
                  </p>
                  <p className="mt-2 text-base leading-7 text-white/90">
                    {profile.injury_notes ?? "No injury notes recorded."}
                  </p>
                </div>
              </div>
            ) : (
              <div className="mt-5 space-y-4">
                <p className="text-base leading-7 text-muted-gray">
                  Your athlete profile is still empty. Complete it now so your
                  later drill analysis has a clean sport and skill context.
                </p>
                <Button asChild>
                  <Link href="/profile">Complete Profile</Link>
                </Button>
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}

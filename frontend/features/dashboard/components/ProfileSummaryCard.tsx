import Link from "next/link";
import { HeartPulse, ShieldAlert, UserRound } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { formatEnumLabel } from "../../../lib/formatters";
import type { ProfileResponse } from "../../../types/profile";
import { EmptyState } from "../../app-shell/components/EmptyState";
import { InfoCard } from "../../app-shell/components/InfoCard";

type ProfileSummaryCardProps = {
  profile: ProfileResponse | null;
};

export function ProfileSummaryCard({ profile }: ProfileSummaryCardProps) {
  if (!profile) {
    return (
      <EmptyState
        icon={UserRound}
        title="Complete your athlete profile"
        description="TrainUp uses your selected sport, skill level, and physical context to shape the drill catalog and prepare the platform for later movement analysis."
        action={
          <Button asChild>
            <Link href="/profile">Set Up Profile</Link>
          </Button>
        }
      />
    );
  }

  return (
    <InfoCard className="relative overflow-hidden">
      <div className="absolute inset-y-0 right-0 w-1/3 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.14),_transparent_62%)]" />
      <div className="relative z-10">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
              Profile Summary
            </p>
            <h3 className="mt-3 font-display text-3xl font-bold text-white">
              {profile.sport_name}
            </h3>
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge variant="accent">{formatEnumLabel(profile.skill_level)}</Badge>
              <Badge variant="slate">
                {profile.height_cm ? `${profile.height_cm} cm` : "Height not set"}
              </Badge>
              <Badge variant="slate">
                {profile.weight_kg ? `${profile.weight_kg} kg` : "Weight not set"}
              </Badge>
            </div>
          </div>
          <Button variant="outline" asChild>
            <Link href="/profile">Edit Profile</Link>
          </Button>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              Readiness
            </p>
            <div className="mt-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-emerald-400/20 bg-emerald-500/10 text-emerald-200">
                <HeartPulse className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">
                  Training mode configured
                </p>
                <p className="text-sm text-muted-gray">
                  Sport context and athlete level are ready for drill browsing.
                </p>
              </div>
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="flex items-center gap-2 text-xs uppercase tracking-[0.22em] text-muted-gray">
              <ShieldAlert className="h-3.5 w-3.5" />
              Injury Notes
            </p>
            <p className="mt-4 text-sm leading-7 text-white/85">
              {profile.injury_notes ?? "No injury notes recorded for this athlete profile."}
            </p>
          </div>
        </div>
      </div>
    </InfoCard>
  );
}

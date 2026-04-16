"use client";

import Link from "next/link";

import { CTAButton } from "../../components/ui/cta-button";
import { AppShell } from "../../features/app-shell/components/AppShell";
import { ProfileForm } from "../../features/profile/components/ProfileForm";

export default function ProfilePage() {
  return (
    <AppShell
      eyebrow="Athlete Profile"
      title="Configure the athlete context"
      description="Keep sport, level, and physical context current so the dashboard, drill library, and future analysis layers stay grounded in the right athlete data."
      capsule="Protected route"
      actions={
        <CTAButton asChild>
          <Link href="/dashboard">Back to Dashboard</Link>
        </CTAButton>
      }
    >
      {() => <ProfileForm embedded />}
    </AppShell>
  );
}

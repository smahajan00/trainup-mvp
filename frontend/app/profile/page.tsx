"use client";

import Link from "next/link";

import { CTAButton } from "../../components/ui/cta-button";
import { AppShell } from "../../features/app-shell/components/AppShell";
import { ProfileForm } from "../../features/profile/components/ProfileForm";

export default function ProfilePage() {
  return (
    <AppShell
      eyebrow="Athlete Profile"
      title="Update your profile"
      description="Set your sport, level, and body stats."
      capsule="Profile"
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

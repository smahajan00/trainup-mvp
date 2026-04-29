"use client";

import Link from "next/link";

import { CTAButton } from "../../components/ui/cta-button";
import { AppShell } from "../../features/app-shell/components/AppShell";
import { ProgressAnalyticsView } from "../../features/dashboard/components/ProgressAnalyticsView";

export default function ProgressPage() {
  return (
    <AppShell
      eyebrow="Progress"
      title="Performance analytics"
      description="Track score trends, drill comparisons, and recurring coaching patterns."
      capsule="Analytics"
      actions={
        <CTAButton asChild>
          <Link href="/sports">Start Training</Link>
        </CTAButton>
      }
    >
      {({ user, profile }) => <ProgressAnalyticsView user={user} profile={profile} />}
    </AppShell>
  );
}

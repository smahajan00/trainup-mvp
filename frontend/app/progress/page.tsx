"use client";

import Link from "next/link";

import { CTAButton } from "../../components/ui/cta-button";
import { AppShell } from "../../features/app-shell/components/AppShell";
import { ProgressAnalyticsView } from "../../features/dashboard/components/ProgressAnalyticsView";

export default function ProgressPage() {
  return (
    <AppShell
      eyebrow="Dashboard"
      title="Performance Dashboard"
      description="Track your score trends, training patterns, and key focus areas across sessions."
      capsule="Performance"
      actions={
        <CTAButton asChild>
          <Link href="/sports">Start Training</Link>
        </CTAButton>
      }
      showHeader={false}
    >
      {({ user, profile }) => <ProgressAnalyticsView user={user} profile={profile} />}
    </AppShell>
  );
}

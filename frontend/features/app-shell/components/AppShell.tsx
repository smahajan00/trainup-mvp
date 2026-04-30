"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  ChevronRight,
  House,
  LogOut,
  PanelLeft,
  Trophy,
  UserCircle2
} from "lucide-react";
import { motion } from "framer-motion";

import { Button } from "../../../components/ui/button";
import { Badge } from "../../../components/ui/badge";
import { CTAButton } from "../../../components/ui/cta-button";
import { SkeletonLoader } from "../../../components/ui/skeleton-loader";
import { formatEnumLabel } from "../../../lib/formatters";
import { useAppSession } from "../../../hooks/useAppSession";
import { cn } from "../../../lib/utils";
import { EmptyState } from "./EmptyState";
import { PageHeader } from "./PageHeader";

type AppShellProps = {
  eyebrow: string;
  title: string;
  description: string;
  capsule?: string;
  actions?: React.ReactNode;
  showHeader?: boolean;
  children: (session: ReturnType<typeof useAppSession>) => React.ReactNode;
};

type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
  disabled?: boolean;
};

const navigationItems: NavItem[] = [
  { label: "Home", href: "/dashboard", icon: House },
  { label: "Sports", href: "/sports", icon: Trophy },
  { label: "Profile", href: "/profile", icon: UserCircle2 },
  { label: "Dashboard", href: "/progress", icon: BarChart3 }
];

function isActiveRoute(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({
  eyebrow,
  title,
  description,
  capsule,
  actions,
  showHeader = true,
  children
}: AppShellProps) {
  const pathname = usePathname();
  const session = useAppSession();

  return (
    <div className="min-h-screen bg-background-dark text-white">
      <div
        className="fixed inset-0 bg-hero-grid opacity-50"
        style={{ backgroundSize: "auto, 72px 72px, 72px 72px" }}
      />
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,122,0,0.18),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(255,255,255,0.05),_transparent_26%)]" />

      <div className="relative z-10 lg:grid lg:min-h-screen lg:grid-cols-[280px_1fr]">
        <aside className="hidden border-r border-white/10 bg-[linear-gradient(180deg,rgba(31,31,31,0.95),rgba(17,17,17,0.92))] px-6 py-8 backdrop-blur lg:flex lg:flex-col">
          <Link href="/dashboard" className="group">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary shadow-glow">
                <PanelLeft className="h-5 w-5" />
              </div>
              <div>
                <p className="font-display text-2xl font-bold tracking-tight text-white">
                  TrainUp
                </p>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-gray">
                  Performance Lab
                </p>
              </div>
            </div>
          </Link>

          <nav className="mt-10 space-y-2">
            {navigationItems.map(({ label, href, icon: Icon, disabled }) => {
              const active = isActiveRoute(pathname, href);

              return disabled ? (
                <div
                  key={label}
                  className="flex items-center justify-between rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3 text-sm text-white/45"
                >
                  <div className="flex items-center gap-3">
                    <Icon className="h-4 w-4" />
                    <span>{label}</span>
                  </div>
                  <Badge variant="slate" className="text-[10px] tracking-[0.18em]">
                    Soon
                  </Badge>
                </div>
              ) : (
                <Link
                  key={label}
                  href={href}
                  className={cn(
                    "group flex items-center justify-between rounded-2xl border px-4 py-3 text-sm transition-all duration-300 motion-reduce:transition-none hover:-translate-y-0.5",
                    active
                      ? "border-primary/30 bg-primary/14 text-white shadow-[0_12px_34px_rgba(255,122,0,0.16)]"
                      : "border-white/8 bg-white/[0.03] text-white/70 hover:border-white/18 hover:bg-white/[0.05] hover:text-white"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <Icon className="h-4 w-4" />
                    <span>{label}</span>
                  </div>
                  <ChevronRight
                    className={cn(
                      "h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5",
                      active ? "text-primary" : "text-white/35"
                    )}
                  />
                </Link>
              );
            })}
          </nav>

          <div className="mt-8 rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-muted-gray">
              Athlete profile
            </p>
            <p className="mt-3 text-lg font-semibold text-white">
              {session.user?.full_name ?? "Loading athlete..."}
            </p>
            <p className="mt-1 text-sm text-muted-gray">{session.user?.email ?? " "}</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {session.profile ? (
                <>
                  <Badge variant="accent">{session.profile.sport_name}</Badge>
                  <Badge variant="slate">
                    {formatEnumLabel(session.profile.skill_level)}
                  </Badge>
                </>
              ) : (
                <Badge variant="warning">Profile incomplete</Badge>
              )}
            </div>
          </div>

          <div className="mt-auto">
            <Button
              variant="ghost"
              className="w-full justify-start rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-6 text-white/75 hover:bg-white/[0.06] hover:text-white"
              onClick={session.logout}
            >
              <LogOut className="mr-3 h-4 w-4" />
              Logout
            </Button>
          </div>
        </aside>

        <div className="min-h-screen px-4 pb-10 pt-4 sm:px-6 lg:px-10 lg:py-8">
          <div className="rounded-[1.6rem] border border-white/10 bg-charcoal/55 px-4 py-4 backdrop-blur md:px-5 lg:hidden">
            <div className="flex items-center justify-between gap-3">
              <Link href="/dashboard" className="font-display text-2xl font-bold text-white">
                TrainUp
              </Link>
              <Button variant="ghost" onClick={session.logout}>
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </Button>
            </div>
            <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
              {navigationItems.map(({ label, href, disabled }) =>
                disabled ? (
                  <div
                    key={label}
                    className="rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-white/45"
                  >
                    {label}
                  </div>
                ) : (
                  <Link
                    key={label}
                    href={href}
                    className={cn(
                      "rounded-full border px-4 py-2 text-sm whitespace-nowrap transition-colors",
                      isActiveRoute(pathname, href)
                        ? "border-primary/25 bg-primary/12 text-white"
                        : "border-white/10 bg-white/[0.03] text-white/70"
                    )}
                  >
                    {label}
                  </Link>
                )
              )}
            </div>
          </div>

          <div className="mt-4 space-y-6 lg:mt-0">
            {showHeader ? (
              <PageHeader
                eyebrow={eyebrow}
                title={title}
                description={description}
                capsule={
                  session.profile
                    ? `${session.profile.sport_name} · ${formatEnumLabel(session.profile.skill_level)}`
                    : capsule
                }
                actions={actions}
              />
            ) : null}

            {session.isLoading ? (
              <div className="space-y-6">
                <div className="grid gap-5 xl:grid-cols-4">
                  <SkeletonLoader className="h-36" />
                  <SkeletonLoader className="h-36" />
                  <SkeletonLoader className="h-36" />
                  <SkeletonLoader className="h-36" />
                </div>
                <SkeletonLoader className="h-72" />
              </div>
            ) : session.error ? (
              <EmptyState
                icon={PanelLeft}
                title="We couldn't load the product shell."
                description={session.error}
                action={
                  <CTAButton asChild>
                    <Link href="/dashboard">Reload workspace</Link>
                  </CTAButton>
                }
              />
            ) : (
              <motion.div
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.45, ease: "easeOut" }}
              >
                {children(session)}
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

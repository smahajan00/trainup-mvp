import type { LucideIcon } from "lucide-react";

import { InfoCard } from "../../app-shell/components/InfoCard";

type AnalyticsKpiCardProps = {
  label: string;
  value: string;
  description?: string;
  icon: LucideIcon;
  tone?: "accent" | "success" | "warning" | "danger" | "slate";
};

export function AnalyticsKpiCard({
  label,
  value,
  description,
  icon: Icon,
  tone = "accent"
}: AnalyticsKpiCardProps) {
  const compactValue = value.length > 14;
  const iconTone = {
    accent: "border-primary/20 bg-primary/10 text-primary",
    success: "border-emerald-400/20 bg-emerald-500/10 text-emerald-200",
    warning: "border-amber-400/20 bg-amber-500/10 text-amber-200",
    danger: "border-rose-400/20 bg-rose-500/10 text-rose-200",
    slate: "border-white/10 bg-white/[0.05] text-white/75"
  }[tone];

  return (
    <InfoCard className="relative min-w-0 overflow-hidden p-4">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/45 to-transparent" />
      <div className="flex items-center gap-3">
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border ${iconTone}`}>
          <Icon className="h-4 w-4" />
        </div>
        <p className="min-w-0 text-xs font-semibold uppercase tracking-[0.2em] text-muted-gray">
          {label}
        </p>
      </div>
      <p
        className={`mt-4 break-words font-display font-bold tracking-tight text-white ${
          compactValue ? "text-xl leading-7" : "text-3xl"
        }`}
      >
        {value}
      </p>
      {description ? (
        <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted-gray">
          {description}
        </p>
      ) : null}
    </InfoCard>
  );
}

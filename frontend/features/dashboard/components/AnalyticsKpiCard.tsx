import type { LucideIcon } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { InfoCard } from "../../app-shell/components/InfoCard";

type AnalyticsKpiCardProps = {
  label: string;
  value: string;
  description: string;
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
  const compactValue = value.length > 18;

  return (
    <InfoCard className="relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/45 to-transparent" />
      <div className="flex items-start justify-between gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <Badge variant={tone}>Analytics</Badge>
      </div>
      <p className="mt-6 text-xs uppercase tracking-[0.22em] text-muted-gray">{label}</p>
      <p
        className={`mt-4 font-display font-bold tracking-tight text-white ${
          compactValue ? "text-xl leading-8" : "text-4xl"
        }`}
      >
        {value}
      </p>
      <p className="mt-4 text-sm leading-7 text-muted-gray">{description}</p>
    </InfoCard>
  );
}

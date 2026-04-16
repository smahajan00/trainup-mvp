import type { LucideIcon } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { InfoCard } from "./InfoCard";

type StatCardProps = {
  label: string;
  value: string;
  description: string;
  icon: LucideIcon;
  tone?: "accent" | "success" | "warning";
};

export function StatCard({
  label,
  value,
  description,
  icon: Icon,
  tone = "accent"
}: StatCardProps) {
  const badgeTone = tone === "success" ? "success" : tone === "warning" ? "warning" : "accent";

  return (
    <InfoCard className="relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/45 to-transparent" />
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">{label}</p>
          <p className="mt-4 text-3xl font-bold tracking-tight text-white">{value}</p>
        </div>
        <Badge variant={badgeTone}>
          <Icon className="mr-1.5 h-3.5 w-3.5" />
          Live
        </Badge>
      </div>
      <p className="mt-5 text-sm leading-7 text-muted-gray">{description}</p>
    </InfoCard>
  );
}

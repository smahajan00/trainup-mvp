import type { LucideIcon } from "lucide-react";

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
  const iconTone =
    tone === "success"
      ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-200"
      : tone === "warning"
        ? "border-amber-400/20 bg-amber-500/10 text-amber-200"
        : "border-primary/20 bg-primary/10 text-primary";
  const isLongValue = value.length > 12;

  return (
    <InfoCard className="group h-full min-w-0 p-6 transition-transform duration-300 hover:-translate-y-1 hover:scale-[1.01] hover:border-primary/25 hover:shadow-glow">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/45 to-transparent" />
      <div className="flex min-w-0 items-start justify-between gap-4">
        <p className="line-clamp-2 min-w-0 break-words text-lg font-semibold leading-snug text-white md:text-xl">
          {label}
        </p>
        <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border ${iconTone}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <p
        className={`mt-4 break-words font-bold tracking-tight text-white ${
          isLongValue
            ? "line-clamp-2 text-2xl leading-snug md:text-3xl"
            : "text-4xl leading-tight"
        }`}
      >
        {value}
      </p>
      <p className="mt-2 line-clamp-2 break-words text-sm leading-relaxed text-neutral-300 md:text-base">
        {description}
      </p>
    </InfoCard>
  );
}

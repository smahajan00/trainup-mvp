import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { motion } from "framer-motion";

import { Badge } from "../../../components/ui/badge";
import { getSportPreset } from "../../../lib/sport-presets";
import type { SportOption } from "../../../types/sports";

type SportCardProps = {
  sport: SportOption;
  drillCount: number;
  highlighted?: boolean;
};

function getCompactSportBadge(label: string) {
  const compactLabels: Record<string, string> = {
    "Mobility & Strength": "Strength",
    "Ball Control": "Control",
    "Form & Stance": "Form",
    "Training Focus": "Training"
  };

  return compactLabels[label] ?? label;
}

export function SportCard({
  sport,
  drillCount,
  highlighted = false
}: SportCardProps) {
  const preset = getSportPreset(sport.sport_name);
  const Icon = preset.icon;
  const badgeLabel = getCompactSportBadge(preset.badge);

  return (
    <motion.div
      className="h-full min-w-0"
      whileHover={{ y: -4, scale: 1.01 }}
      transition={{ duration: 0.2 }}
    >
      <Link
        href={`/sports/${sport.id}/drills`}
        className="block h-full min-w-0"
      >
        <section
          className={`group relative h-full min-h-[360px] min-w-0 overflow-hidden rounded-[1.75rem] border p-7 shadow-[0_24px_80px_rgba(0,0,0,0.34)] backdrop-blur transition-[border-color,box-shadow,transform] duration-300 ${preset.surfaceClass} ${
            highlighted
              ? "border-primary/35 shadow-[0_0_0_1px_rgba(255,122,0,0.14),0_28px_90px_rgba(255,122,0,0.16)]"
              : "border-white/10 hover:border-primary/25 hover:shadow-[0_30px_90px_rgba(0,0,0,0.42)]"
          }`}
        >
          <div className="relative z-10 flex h-full flex-col">
            <div className="flex min-w-0 items-start justify-between gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-3xl border border-primary/20 bg-primary/10 text-primary">
                <Icon className="h-6 w-6" />
              </div>
              <div className="flex min-w-0 flex-wrap justify-end gap-2 overflow-visible">
                <Badge
                  variant={highlighted ? "accent" : "slate"}
                  className="max-w-full whitespace-nowrap tracking-[0.16em]"
                >
                  {badgeLabel}
                </Badge>
                <Badge variant="slate" className="max-w-full whitespace-nowrap tracking-[0.16em]">
                  {drillCount} drills
                </Badge>
              </div>
            </div>

            <div className="mt-4 min-w-0 overflow-hidden">
              <p className="line-clamp-1 break-words text-xs uppercase tracking-[0.2em] text-neutral-400">
                {preset.category}
              </p>
              <h3 className="mt-3 line-clamp-2 break-words font-display text-3xl font-semibold leading-tight text-white">
                {sport.sport_name}
              </h3>
              <p className="mt-3 line-clamp-2 break-words text-sm leading-relaxed text-neutral-300 md:text-base">
                {preset.subtitle}
              </p>
            </div>

            <div className="mt-auto pt-5">
              <div className="inline-flex w-full items-center justify-between gap-2 rounded-2xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-[0_16px_40px_rgba(255,122,0,0.24)] transition duration-300 group-hover:bg-primary/90 group-hover:shadow-[0_20px_48px_rgba(255,122,0,0.3)]">
                <span>Open Drills</span>
                <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5" />
              </div>
            </div>
          </div>
        </section>
      </Link>
    </motion.div>
  );
}

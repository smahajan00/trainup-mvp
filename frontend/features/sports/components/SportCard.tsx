import Link from "next/link";
import { motion } from "framer-motion";

import { Badge } from "../../../components/ui/badge";
import { CTAButton } from "../../../components/ui/cta-button";
import { getSportPreset } from "../../../lib/sport-presets";
import type { SportOption } from "../../../types/sports";
import { InfoCard } from "../../app-shell/components/InfoCard";

type SportCardProps = {
  sport: SportOption;
  drillCount: number;
  highlighted?: boolean;
};

export function SportCard({
  sport,
  drillCount,
  highlighted = false
}: SportCardProps) {
  const preset = getSportPreset(sport.sport_name);
  const Icon = preset.icon;

  return (
    <motion.div whileHover={{ y: -6 }} transition={{ duration: 0.2 }}>
      <InfoCard
        className={`group relative h-full overflow-hidden border-white/10 before:absolute before:inset-0 before:content-[''] ${preset.surfaceClass} ${
          highlighted ? "border-primary/25 shadow-glow" : ""
        }`}
      >
        <div
          className={`absolute inset-0 bg-gradient-to-br ${preset.glowClass} opacity-90`}
        />
        <div className="relative z-10 flex h-full flex-col">
          <div className="flex items-start justify-between gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-3xl border border-primary/20 bg-primary/10 text-primary">
              <Icon className="h-6 w-6" />
            </div>
            <div className="flex flex-col items-end gap-2">
              <Badge variant={highlighted ? "accent" : "slate"}>{preset.badge}</Badge>
              <Badge variant="slate">{drillCount} drills</Badge>
            </div>
          </div>

          <div className="mt-8">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              {preset.category}
            </p>
            <h3 className="mt-3 font-display text-3xl font-bold text-white">
              {sport.sport_name}
            </h3>
            <p className="mt-3 text-sm leading-7 text-white/80">{preset.subtitle}</p>
            <p className="mt-4 text-sm leading-7 text-muted-gray">{preset.insight}</p>
          </div>

          <div className="mt-auto pt-8">
            <CTAButton asChild className="w-full justify-between rounded-2xl">
              <Link href={`/sports/${sport.id}/drills`}>Explore Drills</Link>
            </CTAButton>
          </div>
        </div>
      </InfoCard>
    </motion.div>
  );
}

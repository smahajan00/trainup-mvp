import type { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";

import { Badge } from "../../../components/ui/badge";
import { CTAButton } from "../../../components/ui/cta-button";
import { InfoCard } from "../../app-shell/components/InfoCard";

type ModeCardProps = {
  title: string;
  description: string;
  badge: string;
  eyebrow: string;
  detail: string;
  ctaLabel: string;
  icon: LucideIcon;
  onSelect: () => void;
  isSubmitting?: boolean;
};

export function ModeCard({
  title,
  description,
  badge,
  eyebrow,
  detail,
  ctaLabel,
  icon: Icon,
  onSelect,
  isSubmitting = false
}: ModeCardProps) {
  return (
    <motion.div whileHover={{ y: -6 }} transition={{ duration: 0.2 }}>
      <InfoCard className="relative h-full overflow-hidden border-white/10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.14),_transparent_38%)]" />
        <div className="relative z-10 flex h-full flex-col">
          <div className="flex items-start justify-between gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-3xl border border-primary/20 bg-primary/10 text-primary">
              <Icon className="h-6 w-6" />
            </div>
            <Badge variant="accent">{badge}</Badge>
          </div>

          <div className="mt-8">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
              {eyebrow}
            </p>
            <h3 className="mt-3 font-display text-3xl font-bold text-white">
              {title}
            </h3>
            <p className="mt-3 text-sm text-white/85">{description}</p>
            <p className="mt-4 text-sm text-muted-gray">{detail}</p>
          </div>

          <div className="mt-auto pt-8">
            <CTAButton
              type="button"
              onClick={onSelect}
              className="w-full justify-between rounded-2xl"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Creating" : ctaLabel}
            </CTAButton>
          </div>
        </div>
      </InfoCard>
    </motion.div>
  );
}

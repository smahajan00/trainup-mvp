import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";

import { Badge } from "../../../components/ui/badge";
import { InfoCard } from "../../app-shell/components/InfoCard";

type QuickActionCardProps = {
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
  badge: string;
};

export function QuickActionCard({
  title,
  description,
  href,
  icon: Icon,
  badge
}: QuickActionCardProps) {
  return (
    <motion.div whileHover={{ y: -4 }}>
      <Link href={href}>
        <InfoCard className="h-full transition-colors duration-300 hover:border-primary/20">
          <div className="flex items-start justify-between gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
              <Icon className="h-5 w-5" />
            </div>
            <Badge variant="slate">{badge}</Badge>
          </div>
          <h3 className="mt-6 font-display text-2xl font-bold text-white">{title}</h3>
          <p className="mt-3 text-sm leading-7 text-muted-gray">{description}</p>
        </InfoCard>
      </Link>
    </motion.div>
  );
}

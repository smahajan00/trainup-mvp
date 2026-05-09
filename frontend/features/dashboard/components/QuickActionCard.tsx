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
    <motion.div
      className="h-full min-w-0"
      whileHover={{ y: -4, scale: 1.01 }}
      transition={{ duration: 0.2 }}
    >
      <Link href={href} className="block h-full min-w-0">
        <InfoCard className="group flex h-full min-h-[260px] min-w-0 flex-col space-y-5 p-7 transition-all duration-300 hover:border-primary/25 hover:shadow-glow">
          <div className="flex min-w-0 items-start justify-between gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-3xl border border-primary/20 bg-primary/10 text-primary">
              <Icon className="h-6 w-6" />
            </div>
            <Badge variant="slate" className="max-w-[10rem] truncate">
              {badge}
            </Badge>
          </div>
          <h3 className="line-clamp-2 min-w-0 break-words font-display text-2xl font-semibold leading-tight text-white md:text-3xl">
            {title}
          </h3>
          <p className="line-clamp-2 min-w-0 break-words text-sm leading-relaxed text-neutral-300 md:text-base">
            {description}
          </p>
          <p className="mt-auto text-xs font-semibold uppercase tracking-[0.2em] text-primary">
            Open
          </p>
        </InfoCard>
      </Link>
    </motion.div>
  );
}

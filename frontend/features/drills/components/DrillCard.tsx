import Link from "next/link";
import { motion } from "framer-motion";
import { Radar } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { formatEnumLabel, formatTokenLabel, truncateText } from "../../../lib/formatters";
import type { DrillListItem } from "../../../types/drills";
import { InfoCard } from "../../app-shell/components/InfoCard";

type DrillCardProps = {
  drill: DrillListItem;
};

export function DrillCard({ drill }: DrillCardProps) {
  const metrics = drill.target_metrics.metrics ?? [];

  return (
    <motion.div whileHover={{ y: -5 }} transition={{ duration: 0.2 }}>
      <InfoCard className="flex h-full flex-col overflow-hidden transition-colors duration-300 hover:border-primary/20">
        <div className="flex items-start justify-between gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
            <Radar className="h-5 w-5" />
          </div>
          <Badge variant="accent">{formatEnumLabel(drill.difficulty_level)}</Badge>
        </div>

        <div className="mt-6">
          <h3 className="font-display text-2xl font-bold text-white">
            {drill.drill_name}
          </h3>
          <p className="mt-3 text-sm leading-7 text-muted-gray">
            {truncateText(drill.description, 190)}
          </p>
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          {metrics.slice(0, 4).map((metric) => (
            <Badge key={metric} variant="slate">
              {formatTokenLabel(metric)}
            </Badge>
          ))}
          {metrics.length > 4 ? (
            <Badge variant="slate">+{metrics.length - 4} more</Badge>
          ) : null}
        </div>

        <div className="mt-auto pt-8">
          <Button asChild className="w-full rounded-2xl">
            <Link href={`/drills/${drill.id}`}>View Drill</Link>
          </Button>
        </div>
      </InfoCard>
    </motion.div>
  );
}

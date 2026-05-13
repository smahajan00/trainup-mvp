import Link from "next/link";
import { motion } from "framer-motion";
import { Radar } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { formatTokenLabel } from "../../../lib/formatters";
import type { DrillListItem } from "../../../types/drills";
import { InfoCard } from "../../app-shell/components/InfoCard";

type DrillCardProps = {
  drill: DrillListItem;
};

const FOCUS_LABELS: Record<string, string> = {
  ankle_lock: "Ankle lock",
  approach_angle: "Approach",
  balance_control: "Balance",
  core_bracing: "Core brace",
  depth_consistency: "Depth",
  elbow_alignment: "Elbow line",
  elbow_extension: "Lockout",
  follow_through: "Follow-through",
  heel_pressure: "Heel pressure",
  hip_height: "Hip height",
  hip_rotation: "Hip rotation",
  knee_alignment_score: "Knee tracking",
  knee_drive: "Knee drive",
  knee_flexion: "Knee bend",
  lockout_control: "Lockout",
  posture_accuracy: "Torso control",
  release_timing: "Release timing",
  repetition_consistency: "Consistency",
  shooting_alignment: "Alignment",
  shoulder_symmetry: "Shoulder control",
  stance_width: "Stance width",
  swing_path: "Swing path",
  torso_control: "Torso control",
  trunk_lean: "Trunk lean",
  wrist_follow_through: "Wrist finish"
};

function getFocusLabel(metric: string) {
  return FOCUS_LABELS[metric] ?? formatTokenLabel(metric).replace(/\bScore\b/g, "").trim();
}

export function DrillCard({ drill }: DrillCardProps) {
  const focusAreas = Array.from(
    new Set((drill.target_metrics.metrics ?? []).map(getFocusLabel).filter(Boolean))
  ).slice(0, 3);

  return (
    <motion.div className="h-full" whileHover={{ y: -5 }} transition={{ duration: 0.2 }}>
      <InfoCard className="flex h-full min-h-[340px] min-w-0 flex-col overflow-hidden transition-colors duration-300 hover:border-primary/20">
        <div className="flex items-start">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
            <Radar className="h-5 w-5" />
          </div>
        </div>

        <div className="mt-6 min-w-0">
          <h3 className="line-clamp-2 whitespace-normal break-normal font-display text-2xl font-bold leading-tight text-white">
            {drill.drill_name}
          </h3>
          <p className="mt-3 line-clamp-3 text-sm leading-6 text-muted-gray">
            {drill.description}
          </p>
        </div>

        <div className="mt-5 min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-gray">
            Focus areas
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {focusAreas.map((focus) => (
              <Badge
                key={focus}
                variant="slate"
                className="max-w-full px-2.5 py-1 text-[10px] leading-4 tracking-[0.12em]"
              >
                {focus}
              </Badge>
            ))}
          </div>
        </div>

        <div className="mt-auto pt-7">
          <Button asChild className="w-full rounded-2xl">
            <Link href={`/drills/${drill.id}`}>View Drill</Link>
          </Button>
        </div>
      </InfoCard>
    </motion.div>
  );
}

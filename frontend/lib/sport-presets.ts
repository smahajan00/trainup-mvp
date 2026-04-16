import type { LucideIcon } from "lucide-react";
import { Crosshair, Dumbbell, Goal } from "lucide-react";

type SportPreset = {
  label: string;
  subtitle: string;
  badge: string;
  category: string;
  insight: string;
  icon: LucideIcon;
  glowClass: string;
  surfaceClass: string;
};

const sportPresets: Record<string, SportPreset> = {
  Gym: {
    label: "Gym",
    subtitle: "Build strength, control, and movement quality",
    badge: "Mobility & Strength",
    category: "Strength base",
    insight: "Pattern-driven lower and upper body mechanics.",
    icon: Dumbbell,
    glowClass: "from-primary/25 via-primary/5 to-transparent",
    surfaceClass: "before:bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.18),_transparent_40%)]"
  },
  Football: {
    label: "Football",
    subtitle: "Improve striking, passing, and lower-body mechanics",
    badge: "Ball Control",
    category: "Field technique",
    insight: "Plant foot control, hip rotation, and follow-through timing.",
    icon: Goal,
    glowClass: "from-primary/20 via-white/5 to-transparent",
    surfaceClass: "before:bg-[radial-gradient(circle_at_top_right,_rgba(255,255,255,0.08),_transparent_36%)]"
  },
  Basketball: {
    label: "Basketball",
    subtitle: "Refine shooting form, stance, and balance",
    badge: "Form & Stance",
    category: "Shot mechanics",
    insight: "Alignment, release control, and balanced defensive posture.",
    icon: Crosshair,
    glowClass: "from-primary/22 via-slate/20 to-transparent",
    surfaceClass: "before:bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.14),_transparent_38%)]"
  }
};

const sportOrder = ["Gym", "Football", "Basketball"];

export function getSportPreset(sportName: string) {
  return (
    sportPresets[sportName] ?? {
      label: sportName,
      subtitle: "Explore movement quality and training fundamentals",
      badge: "Training Focus",
      category: "Movement library",
      insight: "Structured drills designed for performance consistency.",
      icon: Crosshair,
      glowClass: "from-primary/20 via-white/5 to-transparent",
      surfaceClass:
        "before:bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.14),_transparent_38%)]"
    }
  );
}

export function sortSportsByPresetOrder<T extends { sport_name: string }>(sports: T[]) {
  return [...sports].sort((left, right) => {
    const leftIndex = sportOrder.indexOf(left.sport_name);
    const rightIndex = sportOrder.indexOf(right.sport_name);

    const resolvedLeft = leftIndex === -1 ? Number.MAX_SAFE_INTEGER : leftIndex;
    const resolvedRight = rightIndex === -1 ? Number.MAX_SAFE_INTEGER : rightIndex;

    return resolvedLeft - resolvedRight;
  });
}

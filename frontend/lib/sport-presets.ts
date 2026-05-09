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
    subtitle: "Build strength and control",
    badge: "Mobility & Strength",
    category: "Strength base",
    insight: "Strength and form.",
    icon: Dumbbell,
    glowClass: "from-primary/25 via-primary/5 to-transparent",
    surfaceClass:
      "bg-[radial-gradient(circle_at_18%_18%,rgba(255,122,0,0.34),transparent_36%),radial-gradient(circle_at_88%_8%,rgba(255,122,0,0.14),transparent_34%),linear-gradient(145deg,rgba(55,36,22,0.96)_0%,rgba(30,28,26,0.97)_48%,rgba(17,17,17,0.99)_100%)]"
  },
  Football: {
    label: "Football",
    subtitle: "Sharpen striking and passing",
    badge: "Ball Control",
    category: "Field technique",
    insight: "Control and timing.",
    icon: Goal,
    glowClass: "from-primary/20 via-white/5 to-transparent",
    surfaceClass:
      "bg-[radial-gradient(circle_at_18%_18%,rgba(255,122,0,0.22),transparent_36%),radial-gradient(circle_at_86%_8%,rgba(255,255,255,0.11),transparent_34%),linear-gradient(145deg,rgba(48,39,30,0.96)_0%,rgba(29,30,30,0.97)_50%,rgba(17,17,17,0.99)_100%)]"
  },
  Basketball: {
    label: "Basketball",
    subtitle: "Refine shooting and stance",
    badge: "Form & Stance",
    category: "Shot mechanics",
    insight: "Balance and release.",
    icon: Crosshair,
    glowClass: "from-primary/22 via-slate/20 to-transparent",
    surfaceClass:
      "bg-[radial-gradient(circle_at_18%_18%,rgba(255,122,0,0.24),transparent_36%),radial-gradient(circle_at_88%_8%,rgba(148,163,184,0.12),transparent_34%),linear-gradient(145deg,rgba(42,35,29,0.96)_0%,rgba(31,31,32,0.97)_50%,rgba(17,17,17,0.99)_100%)]"
  }
};

const sportOrder = ["Gym", "Football", "Basketball"];

export function getSportPreset(sportName: string) {
  return (
    sportPresets[sportName] ?? {
      label: sportName,
      subtitle: "Open drills and train",
      badge: "Training Focus",
      category: "Movement library",
      insight: "Focused drill library.",
      icon: Crosshair,
      glowClass: "from-primary/20 via-white/5 to-transparent",
      surfaceClass:
        "bg-[radial-gradient(circle_at_18%_18%,rgba(255,122,0,0.24),transparent_36%),radial-gradient(circle_at_88%_8%,rgba(255,255,255,0.1),transparent_34%),linear-gradient(145deg,rgba(45,36,29,0.96)_0%,rgba(30,30,30,0.97)_50%,rgba(17,17,17,0.99)_100%)]"
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

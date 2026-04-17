const metricDescriptions: Record<string, string> = {
  posture_accuracy:
    "How well you hold position through the drill.",
  knee_alignment_score:
    "How well your knees stay on line.",
  elbow_angle_consistency:
    "How repeatable your elbow position stays.",
  balance_stability:
    "How steady you stay through the drill.",
  torso_alignment:
    "How well your torso stays set.",
  repetition_consistency:
    "How consistent each rep looks.",
  hip_stability:
    "How controlled your hips stay.",
  shoulder_control:
    "How stable your shoulders stay.",
  shooting_alignment:
    "How clean your shot line stays.",
  stance_width_control:
    "How well you hold your base width."
};

export function getMetricDescription(metricName: string) {
  return metricDescriptions[metricName] ?? "A movement score for this drill.";
}

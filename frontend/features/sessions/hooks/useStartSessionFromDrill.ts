import { useRouter } from "next/navigation";
import { useState } from "react";

import { getErrorMessage } from "../../../lib/api";
import { createSession } from "../../../services/sessions";
import type { DrillDetail } from "../../../types/drills";
import type { ProfileResponse } from "../../../types/profile";
import type { SessionInputType } from "../../../types/sessions";
import { buildSessionCreatePayload } from "../session-setup-utils";

export function useStartSessionFromDrill({
  drill,
  profile
}: {
  drill: DrillDetail | null;
  profile: ProfileResponse | null;
}) {
  const router = useRouter();
  const [startingMode, setStartingMode] = useState<SessionInputType | null>(null);
  const [startError, setStartError] = useState<string | null>(null);

  async function startSession(inputType: SessionInputType) {
    if (!drill) {
      setStartError("Drill details are still loading. Try again in a moment.");
      return;
    }

    setStartingMode(inputType);
    setStartError(null);

    try {
      const session = await createSession(
        buildSessionCreatePayload({
          drill,
          profile,
          inputType,
          cameraView: drill.canonical_view,
          dominantSide: "AUTO"
        })
      );

      router.push(
        inputType === "LIVE"
          ? `/sessions/${session.id}/live?setup=1`
          : `/sessions/${session.id}/upload?setup=1`
      );
    } catch (error) {
      setStartError(getErrorMessage(error));
      setStartingMode(null);
    }
  }

  return {
    startError,
    startingMode,
    startSession
  };
}

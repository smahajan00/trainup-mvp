import Link from "next/link";
import { ArrowRight, Camera, UploadCloud } from "lucide-react";

import { Button } from "../../../components/ui/button";
import { formatEnumLabel } from "../../../lib/formatters";
import type { SessionInputType } from "../../../types/sessions";

type SessionInputModeToggleProps = {
  mode: SessionInputType;
  sessionDrillId: string;
  secondaryActionLabel?: string;
  helperText?: string;
  secondaryActionHref?: string;
};

export function SessionInputModeToggle({
  mode,
  sessionDrillId,
  secondaryActionLabel,
  helperText,
  secondaryActionHref
}: SessionInputModeToggleProps) {
  const isUploadMode = mode === "UPLOAD";
  const actionHref =
    secondaryActionHref ?? `/sessions/new?drillId=${sessionDrillId}`;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
            Input Mode
          </p>
          <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-white/90">
            {isUploadMode ? (
              <UploadCloud className="h-4 w-4 text-primary" />
            ) : (
              <Camera className="h-4 w-4 text-primary" />
            )}
            {formatEnumLabel(mode)}
          </p>
        </div>
        {secondaryActionLabel ? (
          <Button asChild variant="outline" className="rounded-2xl">
            <Link href={actionHref}>
              <ArrowRight className="mr-2 h-4 w-4" />
              {secondaryActionLabel}
            </Link>
          </Button>
        ) : null}
      </div>
      <p className="text-sm leading-6 text-muted-gray">
        {helperText
          ? helperText
          : "This session stays locked to its current input mode. Start a fresh session if you want to switch how you capture the next rep."}
      </p>
    </div>
  );
}

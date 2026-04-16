import Link from "next/link";
import { ArrowUpRight, UploadCloud, Video } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { formatDateTime, formatEnumLabel } from "../../../lib/formatters";
import type { TrainingSession } from "../../../types/sessions";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { SessionStatusBadge } from "./SessionStatusBadge";

function getSessionHref(session: TrainingSession) {
  return session.input_type === "LIVE"
    ? `/sessions/${session.id}/live`
    : `/sessions/${session.id}/upload`;
}

export function RecentSessionCard({ session }: { session: TrainingSession }) {
  const Icon = session.input_type === "LIVE" ? Video : UploadCloud;

  return (
    <Link href={getSessionHref(session)} className="block">
      <InfoCard className="group h-full border-white/10 transition-all duration-300 hover:border-primary/20 hover:shadow-glow">
        <div className="flex items-start justify-between gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/15 bg-primary/10 text-primary">
            <Icon className="h-5 w-5" />
          </div>
          <div className="flex flex-col items-end gap-2">
            <SessionStatusBadge status={session.status} />
            <Badge variant="slate">{formatEnumLabel(session.input_type)}</Badge>
          </div>
        </div>

        <div className="mt-6">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
            {session.sport_name}
          </p>
          <h3 className="mt-3 font-display text-2xl font-bold text-white">
            {session.drill_name}
          </h3>
          <p className="mt-3 text-sm leading-7 text-muted-gray">
            Started {formatDateTime(session.start_time)}
          </p>
        </div>

        <div className="mt-6 flex items-center justify-between text-sm font-semibold text-white/80">
          <span>Open Session</span>
          <ArrowUpRight className="h-4 w-4 transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
        </div>
      </InfoCard>
    </Link>
  );
}

import Link from "next/link";
import { ArrowUpRight, UploadCloud, Video } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import {
  formatDateTime,
  truncateText
} from "../../../lib/formatters";
import type { RecentProgressSession } from "../../../types/progress";
import type { TrainingSession } from "../../../types/sessions";
import { InfoCard } from "../../app-shell/components/InfoCard";

type RecentSessionCardModel =
  | TrainingSession
  | RecentProgressSession;

function getSessionId(session: RecentSessionCardModel) {
  return "session_id" in session ? session.session_id : session.id;
}

function getSessionHref(session: RecentSessionCardModel) {
  const sessionId = getSessionId(session);
  return session.input_type === "LIVE"
    ? `/sessions/${sessionId}/live`
    : `/sessions/${sessionId}/upload`;
}

export function RecentSessionCard({ session }: { session: RecentSessionCardModel }) {
  const Icon = session.input_type === "LIVE" ? Video : UploadCloud;
  const overallAccuracy = "overall_accuracy" in session ? session.overall_accuracy : null;
  const summaryText = "summary_text" in session ? session.summary_text : null;
  const focus = summaryText ? truncateText(summaryText, 64) : "Review coaching";

  return (
    <Link href={getSessionHref(session)} className="block h-full min-w-0">
      <InfoCard className="group flex h-full min-h-[320px] min-w-0 flex-col space-y-4 border-white/10 p-6 transition-all duration-300 hover:-translate-y-1 hover:scale-[1.01] hover:border-primary/25 hover:shadow-glow">
        <div className="flex min-w-0 items-start justify-between gap-4">
          <div className="min-w-0 overflow-hidden">
            <p className="line-clamp-1 break-words text-xs font-semibold uppercase tracking-[0.2em] text-neutral-400">
              {session.sport_name}
            </p>
            <h3 className="mt-2 line-clamp-2 min-h-[3.5rem] break-words font-display text-xl font-semibold leading-snug text-white md:min-h-[4rem] md:text-2xl">
              {session.drill_name}
            </h3>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/15 bg-primary/10 text-primary">
              <Icon className="h-5 w-5" />
            </div>
            <Badge
              variant={session.status === "COMPLETED" ? "success" : "slate"}
              className="max-w-[8rem] truncate tracking-[0.16em]"
            >
              {session.status}
            </Badge>
          </div>
        </div>

        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.2em] text-neutral-400">Score</p>
          <p className="mt-1 text-5xl font-bold leading-tight text-white">
            {overallAccuracy !== null ? `${overallAccuracy.toFixed(0)}%` : "--"}
          </p>
        </div>

        <div className="min-w-0 space-y-1">
          <p className="text-xs uppercase tracking-[0.2em] text-neutral-400">Focus</p>
          <p className="line-clamp-1 break-words text-sm leading-relaxed text-neutral-300 md:text-base">
            {focus}
          </p>
        </div>

        <p className="line-clamp-1 break-words text-xs text-neutral-400">
          {formatDateTime(session.start_time)}
        </p>

        <div className="mt-auto flex items-center justify-between pt-2 text-sm font-semibold text-white/80">
          <span>Open Session</span>
          <ArrowUpRight className="h-4 w-4 transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
        </div>
      </InfoCard>
    </Link>
  );
}

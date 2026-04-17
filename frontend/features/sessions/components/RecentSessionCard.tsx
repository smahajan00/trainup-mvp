import Link from "next/link";
import { ArrowUpRight, UploadCloud, Video } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import {
  formatDateTime,
  formatEnumLabel,
  truncateText
} from "../../../lib/formatters";
import type { RecentProgressSession } from "../../../types/progress";
import type { TrainingSession } from "../../../types/sessions";
import { InfoCard } from "../../app-shell/components/InfoCard";
import { SessionStatusBadge } from "./SessionStatusBadge";

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
          <p className="mt-3 text-sm text-muted-gray">
            {formatDateTime(session.start_time)}
          </p>
        </div>

        {overallAccuracy !== null ? (
          <div className="mt-6 rounded-2xl border border-emerald-400/25 bg-emerald-500/10 px-4 py-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-emerald-200">
                  Accuracy
                </p>
                <p className="mt-3 text-3xl font-bold text-white">
                  {overallAccuracy.toFixed(1)}%
                </p>
              </div>
              <Badge variant="success">Processed</Badge>
            </div>
          </div>
        ) : null}

        {summaryText ? (
          <p className="mt-5 text-sm text-white/72">
            {truncateText(summaryText, 120)}
          </p>
        ) : null}

        <div className="mt-6 flex items-center justify-between text-sm font-semibold text-white/80">
          <span>Open Session</span>
          <ArrowUpRight className="h-4 w-4 transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
        </div>
      </InfoCard>
    </Link>
  );
}

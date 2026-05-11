import { ChevronDown } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { InfoCard } from "../../app-shell/components/InfoCard";

type AdvancedInsightItem = {
  label: string;
  value: string;
  detail?: string | null;
};

type AdvancedInsightsPanelProps = {
  items: AdvancedInsightItem[];
  hasAnyAdvancedData: boolean;
};

export function AdvancedInsightsPanel({
  items,
  hasAnyAdvancedData
}: AdvancedInsightsPanelProps) {
  return (
    <InfoCard className="p-4 sm:p-5">
      <details className="group [&_summary::-webkit-details-marker]:hidden">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-primary/80">
              Advanced
            </p>
            <h2 className="mt-1 font-display text-xl font-bold tracking-tight text-white sm:text-2xl">
              Advanced Analysis
            </h2>
            <p className="mt-1 max-w-xl text-xs leading-5 text-muted-gray">
              Optional reasoning details. Core coaching above remains the main guidance.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="slate">
              {hasAnyAdvancedData ? "Available" : "Pending"}
            </Badge>
            <ChevronDown className="h-5 w-5 text-white/70 transition-transform duration-200 group-open:rotate-180" />
          </div>
        </summary>

        <div className="mt-4">
          {items.length ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {items.map((item) => (
                <div
                  key={item.label}
                  className="rounded-2xl border border-white/10 bg-white/[0.035] p-3.5"
                >
                  <p className="text-[10px] uppercase tracking-[0.2em] text-muted-gray">
                    {item.label}
                  </p>
                  <p className="mt-2 text-sm font-semibold leading-5 text-white">
                    {item.value}
                  </p>
                  {item.detail ? (
                    <p className="mt-2 line-clamp-3 text-xs leading-5 text-white/62">
                      {item.detail}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm leading-6 text-muted-gray">
              Advanced insights will appear after analysis.
            </p>
          )}
        </div>
      </details>
    </InfoCard>
  );
}

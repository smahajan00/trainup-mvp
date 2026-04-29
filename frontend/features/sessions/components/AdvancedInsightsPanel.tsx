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
    <InfoCard>
      <details className="group [&_summary::-webkit-details-marker]:hidden">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-primary">
              Advanced
            </p>
            <h2 className="mt-2 font-display text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Advanced Analysis
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-muted-gray">
              Open this section for the deeper performance readout without crowding the main coaching view.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="slate">
              {hasAnyAdvancedData ? "Available" : "Pending"}
            </Badge>
            <ChevronDown className="h-5 w-5 text-white/70 transition-transform duration-200 group-open:rotate-180" />
          </div>
        </summary>

        <div className="mt-6">
          {items.length ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {items.map((item) => (
                <div
                  key={item.label}
                  className="rounded-2xl border border-white/10 bg-white/[0.04] p-4"
                >
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-gray">
                    {item.label}
                  </p>
                  <p className="mt-3 text-sm font-semibold leading-6 text-white">
                    {item.value}
                  </p>
                  {item.detail ? (
                    <p className="mt-3 text-sm leading-6 text-white/72">
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

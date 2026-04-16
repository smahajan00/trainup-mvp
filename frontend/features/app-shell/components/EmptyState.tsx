import type { LucideIcon } from "lucide-react";

import { InfoCard } from "./InfoCard";

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
};

export function EmptyState({
  icon: Icon,
  title,
  description,
  action
}: EmptyStateProps) {
  return (
    <InfoCard className="border-dashed border-white/15 text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="mt-5 font-display text-2xl font-bold text-white">{title}</h3>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-muted-gray">
        {description}
      </p>
      {action ? <div className="mt-6">{action}</div> : null}
    </InfoCard>
  );
}

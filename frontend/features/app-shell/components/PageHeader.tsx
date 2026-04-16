import { Sparkles } from "lucide-react";

import { Badge } from "../../../components/ui/badge";
import { InfoCard } from "./InfoCard";

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  actions?: React.ReactNode;
  capsule?: string;
};

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  capsule
}: PageHeaderProps) {
  return (
    <InfoCard className="relative overflow-hidden border-primary/15 bg-[radial-gradient(circle_at_top_right,_rgba(255,122,0,0.16),_transparent_35%),linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))]">
      <div className="absolute -right-16 -top-16 h-40 w-40 rounded-full bg-primary/10 blur-3xl" />
      <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <Badge variant="accent" className="gap-2">
            <Sparkles className="h-3.5 w-3.5" />
            {eyebrow}
          </Badge>
          <h1 className="mt-5 font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">
            {title}
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-muted-gray sm:text-base">
            {description}
          </p>
        </div>
        <div className="flex flex-col items-start gap-3 lg:items-end">
          {capsule ? <Badge variant="slate">{capsule}</Badge> : null}
          {actions}
        </div>
      </div>
    </InfoCard>
  );
}

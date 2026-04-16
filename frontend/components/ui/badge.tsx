import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "../../lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em]",
  {
    variants: {
      variant: {
        accent: "border-primary/30 bg-primary/10 text-primary",
        slate: "border-white/10 bg-white/5 text-white/80",
        success: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
        warning: "border-amber-400/30 bg-amber-500/10 text-amber-200",
        danger: "border-rose-400/30 bg-rose-500/10 text-rose-200"
      }
    },
    defaultVariants: {
      variant: "slate"
    }
  }
);

type BadgeProps = React.HTMLAttributes<HTMLDivElement> &
  VariantProps<typeof badgeVariants>;

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant, className }))} {...props} />;
}

import { cn } from "../../lib/utils";

type SkeletonLoaderProps = {
  className?: string;
};

export function SkeletonLoader({ className }: SkeletonLoaderProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-2xl border border-white/10 bg-white/5",
        className
      )}
    />
  );
}

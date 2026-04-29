import { cn } from "../../../lib/utils";

type InfoCardProps = {
  children: React.ReactNode;
  className?: string;
};

export function InfoCard({ children, className }: InfoCardProps) {
  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.055),rgba(255,255,255,0.02))] p-6 shadow-[0_22px_80px_rgba(0,0,0,0.28)] backdrop-blur transition-[border-color,box-shadow,transform] duration-300 motion-reduce:transition-none hover:border-white/14 hover:shadow-[0_28px_92px_rgba(0,0,0,0.36)]",
        className
      )}
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.18),transparent)]" />
      {children}
    </section>
  );
}

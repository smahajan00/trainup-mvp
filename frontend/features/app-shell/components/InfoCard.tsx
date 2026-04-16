import { cn } from "../../../lib/utils";

type InfoCardProps = {
  children: React.ReactNode;
  className?: string;
};

export function InfoCard({ children, className }: InfoCardProps) {
  return (
    <section
      className={cn(
        "rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))] p-6 shadow-[0_20px_70px_rgba(0,0,0,0.25)] backdrop-blur",
        className
      )}
    >
      {children}
    </section>
  );
}

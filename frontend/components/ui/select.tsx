import * as React from "react";

import { cn } from "../../lib/utils";

const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => {
  return (
    <select
      className={cn(
        "flex h-12 w-full appearance-none rounded-2xl border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.03))] px-4 py-2 text-sm text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] outline-none transition-all duration-300 focus:border-primary/60 focus:bg-white/[0.07] focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60",
        className
      )}
      ref={ref}
      {...props}
    >
      {children}
    </select>
  );
});

Select.displayName = "Select";

export { Select };

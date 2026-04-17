import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "../../lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-2xl text-sm font-semibold transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:translate-y-0 disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow-[0_14px_34px_rgba(255,122,0,0.22)] hover:-translate-y-0.5 hover:scale-[1.02] hover:bg-primary/90 hover:shadow-[0_18px_42px_rgba(255,122,0,0.28)]",
        secondary:
          "bg-secondary/90 text-secondary-foreground hover:-translate-y-0.5 hover:scale-[1.02] hover:bg-secondary",
        ghost:
          "bg-transparent hover:-translate-y-0.5 hover:scale-[1.02] hover:bg-white/10 hover:text-white",
        outline:
          "border border-white/12 bg-white/[0.03] text-white/90 hover:-translate-y-0.5 hover:scale-[1.02] hover:border-white/20 hover:bg-white/[0.08]"
      },
      size: {
        default: "h-11 px-4 py-2.5",
        sm: "h-9 px-3.5",
        lg: "h-12 px-8",
        icon: "h-11 w-11"
      }
    },
    defaultVariants: {
      variant: "default",
      size: "default"
    }
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";

    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);

Button.displayName = "Button";

export { Button, buttonVariants };

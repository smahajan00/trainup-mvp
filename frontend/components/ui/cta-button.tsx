import * as React from "react";
import { ArrowRight } from "lucide-react";

import { cn } from "../../lib/utils";
import { Button, type ButtonProps, buttonVariants } from "./button";

type CTAButtonProps = ButtonProps & {
  children: React.ReactNode;
};

export function CTAButton({
  className,
  children,
  asChild = false,
  variant = "default",
  size = "default",
  ...props
}: CTAButtonProps) {
  const sharedClassName = cn(
    buttonVariants({ variant, size }),
    "group gap-2 rounded-xl bg-primary px-5 text-primary-foreground shadow-glow hover:bg-primary/90",
    className
  );

  if (asChild) {
    const child = React.Children.only(children) as React.ReactElement<{
      className?: string;
      children?: React.ReactNode;
    }>;

    return React.cloneElement(child, {
      ...props,
      className: cn(sharedClassName, child.props.className),
      children: (
        <>
          {child.props.children}
          <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5" />
        </>
      )
    });
  }

  return (
    <Button className={sharedClassName} variant={variant} size={size} {...props}>
      {children}
      <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5" />
    </Button>
  );
}

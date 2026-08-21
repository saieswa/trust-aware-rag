import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md";
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          size === "md" ? "h-10 px-4 text-sm" : "h-8 px-3 text-xs",
          variant === "primary" &&
            "bg-accent-phosphor text-void hover:brightness-110 active:brightness-95",
          variant === "secondary" &&
            "bg-raised text-ink-primary border border-hairline hover:bg-panel",
          variant === "ghost" && "text-ink-muted hover:text-ink-primary hover:bg-raised",
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

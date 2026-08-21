import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: "green" | "red" | "amber" | "neutral";
}

const toneStyles: Record<NonNullable<BadgeProps["tone"]>, string> = {
  green: "bg-signal-green/10 text-signal-green border-signal-green/30",
  red: "bg-signal-red/10 text-signal-red border-signal-red/30",
  amber: "bg-accent-phosphor/10 text-accent-phosphor border-accent-phosphor/30",
  neutral: "bg-raised text-ink-muted border-hairline",
};

export function Badge({ className, tone = "neutral", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs font-mono uppercase tracking-wide",
        toneStyles[tone],
        className
      )}
      {...props}
    />
  );
}

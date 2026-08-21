import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

interface ErrorAlertProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

/**
 * The interface's voice for failure: says plainly what happened, offers a
 * concrete next step (retry) when there is one, and never apologizes —
 * per the writing guidance, errors explain and point forward rather than
 * performing regret.
 */
export function ErrorAlert({ message, onRetry, className }: ErrorAlertProps) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-md border border-signal-red/30 bg-signal-red/10 px-4 py-3",
        className
      )}
      role="alert"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-signal-red" />
      <div className="flex-1">
        <p className="text-sm text-ink-primary">{message}</p>
        {onRetry && (
          <Button variant="ghost" size="sm" onClick={onRetry} className="mt-2 -ml-3">
            <RefreshCw className="h-3.5 w-3.5" />
            Try again
          </Button>
        )}
      </div>
    </div>
  );
}

/** Generic content placeholder shown while a page's initial data loads. */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-raised", className)} />;
}

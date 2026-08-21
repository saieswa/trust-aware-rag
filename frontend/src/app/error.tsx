"use client";

import { useEffect } from "react";
import { AlertOctagon } from "lucide-react";
import { Button } from "@/components/ui/Button";

/** Next.js renders this for any uncaught error thrown while rendering a
 * page — the last line of defense below the per-component ErrorAlert
 * used throughout the app for expected, handled failures. */
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
      <AlertOctagon className="h-8 w-8 text-signal-red" />
      <div>
        <p className="font-mono text-sm text-ink-primary">Something broke while rendering this page</p>
        <p className="text-xs text-ink-muted mt-1 max-w-sm">{error.message || "An unexpected error occurred."}</p>
      </div>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}

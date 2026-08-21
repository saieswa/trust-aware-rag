import Link from "next/link";
import { Button } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 px-6 text-center">
      <span className="font-mono text-4xl text-accent-phosphor">404</span>
      <p className="text-sm text-ink-primary">This page doesn&rsquo;t exist.</p>
      <Link href="/">
        <Button variant="secondary">Back to home</Button>
      </Link>
    </div>
  );
}

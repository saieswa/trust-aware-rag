"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, MessageSquare, FileSearch, Gauge, Settings, Moon, Sun } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: Home },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/evidence", label: "Evidence", icon: FileSearch },
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/admin", label: "Admin", icon: Settings },
];

/**
 * Fixed vertical rail on desktop (evocative of an instrument panel's
 * control strip), collapsing to a bottom tab bar on small screens — the
 * standard, correct responsive pattern for primary navigation, kept
 * deliberately plain so it doesn't compete with the signature Trust
 * Gauge element used throughout the pages themselves.
 */
export function NavRail() {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();

  return (
    <>
      {/* Desktop: left rail */}
      <nav className="hidden md:flex md:flex-col md:w-56 md:shrink-0 border-r border-hairline bg-panel px-3 py-6">
        <div className="px-2 mb-8">
          <span className="font-mono text-sm font-semibold tracking-wide text-ink-primary">
            TRUST<span className="text-accent-phosphor">·</span>RAG
          </span>
        </div>
        <div className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.href} {...item} active={pathname === item.href} />
          ))}
        </div>
        <div className="mt-auto">
          <button
            onClick={toggleTheme}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-ink-muted hover:bg-raised hover:text-ink-primary transition-colors"
            aria-label="Toggle dark mode"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
        </div>
      </nav>

      {/* Mobile: bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-30 flex border-t border-hairline bg-panel">
        {NAV_ITEMS.map((item) => (
          <MobileNavLink key={item.href} {...item} active={pathname === item.href} />
        ))}
        <button
          onClick={toggleTheme}
          className="flex flex-1 flex-col items-center gap-1 py-2.5 text-ink-muted"
          aria-label="Toggle dark mode"
        >
          {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          <span className="text-[10px]">{theme === "dark" ? "Light" : "Dark"}</span>
        </button>
      </nav>
    </>
  );
}

function NavLink({
  href,
  label,
  icon: Icon,
  active,
}: {
  href: string;
  label: string;
  icon: typeof Home;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
        active ? "bg-raised text-accent-phosphor" : "text-ink-muted hover:bg-raised hover:text-ink-primary"
      )}
    >
      <Icon className="h-4 w-4" />
      {label}
    </Link>
  );
}

function MobileNavLink({
  href,
  label,
  icon: Icon,
  active,
}: {
  href: string;
  label: string;
  icon: typeof Home;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex flex-1 flex-col items-center gap-1 py-2.5 text-ink-muted",
        active && "text-accent-phosphor"
      )}
    >
      <Icon className="h-5 w-5" />
      <span className="text-[10px]">{label}</span>
    </Link>
  );
}

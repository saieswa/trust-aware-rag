import type { Metadata } from "next";
import { ThemeProvider } from "@/hooks/useTheme";
import { NavRail } from "@/components/layout/NavRail";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trust-Aware RAG",
  description: "A multi-agent retrieval system that shows its evidence, its trust score, and when it doesn't know.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <ThemeProvider>
          <div className="flex min-h-screen">
            <NavRail />
            <main className="flex-1 min-w-0 pb-16 md:pb-0">{children}</main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}

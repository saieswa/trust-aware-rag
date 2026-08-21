import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Every value here reads from a CSS custom property (globals.css),
        // which flips between light/dark values based on the `.dark`
        // class on <html> -- see hooks/useTheme.tsx. This means
        // `bg-panel`, `text-ink-muted`, etc. work correctly in both modes
        // without any `dark:` prefix needed at the call site.
        void: "var(--bg-void)",
        panel: "var(--bg-panel)",
        raised: "var(--bg-raised)",
        hairline: "var(--hairline)",
        ink: {
          primary: "var(--ink-primary)",
          muted: "var(--ink-muted)",
        },
        accent: {
          phosphor: "var(--accent-phosphor)",
        },
        signal: {
          green: "var(--signal-green)",
          red: "var(--signal-red)",
        },
        trust: {
          high: "var(--signal-green)",
          medium: "var(--accent-phosphor)",
          low: "var(--signal-red)",
        },
      },
      fontFamily: {
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
        sans: ['"IBM Plex Sans"', "ui-sans-serif", "sans-serif"],
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "gauge-sweep": {
          "0%": { strokeDashoffset: "251" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.3s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;

import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      // ── Font Families ──
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        heading: ["var(--font-dm-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-dm-mono)", "JetBrains Mono", "monospace"],
      },

      // ── Anansi Color Palette (Dark Theme — Default "Night Web") ──
      colors: {
        anansi: {
          "bg-deepest": "#0C0A09",
          "bg-surface": "#1C1917",
          "surface-elevated": "#292524",
          "surface-card": "#3A3531",
          "border-subtle": "#44403C",
          "text-primary": "#FAFAF9",
          "text-secondary": "#D6D3D1",
          "text-muted": "#A8A29E",
          "text-disabled": "#78716C",
        },
        brand: {
          amber: {
            DEFAULT: "#D97706",
            light: "#F59E0B",
          },
          ember: {
            DEFAULT: "#DC2626",
            light: "#F97316",
          },
          teal: {
            DEFAULT: "#0F766E",
            light: "#14B8A6",
          },
          violet: {
            DEFAULT: "#6D28D9",
            light: "#8B5CF6",
          },
        },
        semantic: {
          success: "#16A34A",
          "success-light": "#22C55E",
          warning: "#D97706",
          "warning-light": "#FBBF24",
          error: "#DC2626",
          "error-light": "#EF4444",
          info: "#2563EB",
          "info-light": "#3B82F6",
        },
        // Light theme tokens
        day: {
          bg: "#FAFAF9",
          surface: "#F5F5F4",
          elevated: "#E7E5E4",
          border: "#D6D3D1",
          text: "#1C1917",
          "text-secondary": "#57534E",
          muted: "#A8A29E",
        },
      },

      // ── Typography Scale ──
      fontSize: {
        xs: ["0.75rem", { lineHeight: "1rem" }],
        sm: ["0.875rem", { lineHeight: "1.25rem" }],
        base: ["1rem", { lineHeight: "1.5rem" }],
        lg: ["1.125rem", { lineHeight: "1.75rem" }],
        xl: ["1.25rem", { lineHeight: "1.75rem" }],
        "2xl": ["1.5rem", { lineHeight: "2rem" }],
        "3xl": ["1.875rem", { lineHeight: "2.25rem" }],
        "4xl": ["2.25rem", { lineHeight: "2.5rem" }],
        "5xl": ["3rem", { lineHeight: "1.1" }],
        "6xl": ["3.75rem", { lineHeight: "1.1" }],
        "7xl": ["4.5rem", { lineHeight: "1.05" }],
      },

      // ── Spacing Scale ──
      spacing: {
        0: "0px",
        1: "4px",
        2: "8px",
        3: "12px",
        4: "16px",
        5: "20px",
        6: "24px",
        8: "32px",
        10: "40px",
        12: "48px",
        16: "64px",
        20: "80px",
        24: "96px",
      },

      // ── Border Radius ──
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "16px",
        xl: "24px",
        "2xl": "32px",
        full: "9999px",
      },

      // ── Box Shadows ──
      boxShadow: {
        "glass-sm": "0 1px 3px rgba(0,0,0,0.3)",
        "glass-md": "0 4px 12px rgba(0,0,0,0.4)",
        "glass-lg": "0 8px 32px rgba(0,0,0,0.5)",
        "glass-xl": "0 16px 48px rgba(0,0,0,0.6)",
        "glow-amber":
          "0 0 20px rgba(245, 158, 11, 0.15), inset 0 1px 0 rgba(245, 158, 11, 0.1)",
        "glow-violet":
          "0 0 20px rgba(139, 92, 246, 0.15), inset 0 1px 0 rgba(139, 92, 246, 0.1)",
        "glow-teal":
          "0 0 20px rgba(20, 184, 166, 0.15), inset 0 1px 0 rgba(20, 184, 166, 0.1)",
      },
      transitionTimingFunction: {
        "anansi-ease": "cubic-bezier(0.16, 1, 0.3, 1)",
      },
      maxWidth: {
        sm: "640px",
        md: "768px",
        lg: "1024px",
        xl: "1280px",
        "2xl": "1536px",
      },
    },
  },
  plugins: [],
};

export default config;

import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        mc: {
          bg: "#0b1020",
          panel: "#121a2f",
          border: "#243056",
          accent: "#3dd6c6",
          warn: "#f0a202",
          text: "#e8eefc",
          muted: "#8b9bb8",
        },
      },
      fontFamily: {
        display: ["IBM Plex Sans", "Segoe UI", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;

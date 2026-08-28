/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "surface-container-highest": "#353437",
        "tertiary": "#cbccd5",
        "outline": "#a08e7a",
        "surface-container": "#201f22",
        "surface-dim": "#131316",
        "surface": "#131316",
        "error": "#ffb4ab",
        "surface-variant": "#353437",
        "secondary-fixed-dim": "#c7c6cb",
        "on-secondary": "#2f3035",
        "surface-container-lowest": "#0e0e10",
        "primary-fixed-dim": "#ffb95f",
        "inverse-surface": "#e5e1e5",
        "inverse-on-surface": "#313033",
        "secondary": "#c7c6cb",
        "on-surface-variant": "#d8c3ad",
        "on-tertiary": "#2e3038",
        "primary-fixed": "#ffddb8",
        "primary-container": "#f59e0b",
        "secondary-fixed": "#e3e2e7",
        "on-background": "#e5e1e5",
        "background": "#131316",
        "on-secondary-container": "#b5b4ba",
        "tertiary-fixed-dim": "#c5c6cf",
        "inverse-primary": "#855300",
        "on-tertiary-fixed": "#191b22",
        "surface-container-high": "#2a2a2c",
        "on-error": "#690005",
        "on-primary-fixed": "#2a1700",
        "primary": "#ffc174",
        "on-surface": "#e5e1e5",
        "on-primary": "#472a00",
        "surface-bright": "#3a393b",
        "on-primary-container": "#613b00",
        "surface-tint": "#ffb95f",
        "surface-container-low": "#1c1b1e",
        "tertiary-container": "#b0b0ba",
        "error-container": "#93000a",
        "on-tertiary-fixed-variant": "#45464e",
        "on-secondary-fixed": "#1a1b20",
        "on-tertiary-container": "#42434b",
        "tertiary-fixed": "#e2e2ec",
        "on-secondary-fixed-variant": "#46464b",
        "on-error-container": "#ffdad6",
        "outline-variant": "#534434",
        "on-primary-fixed-variant": "#653e00",
        "secondary-container": "#46464b"
      },
      borderRadius: {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "full": "9999px"
      },
      spacing: {
        "margin": "32px",
        "unit": "4px",
        "module-padding": "24px",
        "gutter": "16px"
      },
      fontFamily: {
        "headline-md": ["Space Grotesk", "sans-serif"],
        "body-base": ["Geist", "sans-serif"],
        "display-lg": ["Space Grotesk", "sans-serif"],
        "telemetry-data": ["JetBrains Mono", "monospace"],
        "headline-md-mobile": ["Space Grotesk", "sans-serif"],
        "label-xs": ["JetBrains Mono", "monospace"]
      },
      fontSize: {
        "headline-md": ["32px", { lineHeight: "1.2", fontWeight: "400" }],
        "body-base": ["16px", { lineHeight: "1.6", fontWeight: "400" }],
        "display-lg": ["48px", { lineHeight: "1.1", letterSpacing: "-0.02em", fontWeight: "300" }],
        "telemetry-data": ["14px", { lineHeight: "1.4", letterSpacing: "0.05em", fontWeight: "500" }],
        "headline-md-mobile": ["24px", { lineHeight: "1.2", fontWeight: "400" }],
        "label-xs": ["11px", { lineHeight: "1", fontWeight: "700" }]
      }
    }
  },
  plugins: [],
}

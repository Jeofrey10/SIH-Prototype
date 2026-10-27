/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f5fa",
          100: "#e1ecf5",
          200: "#c3daeb",
          300: "#96bfde",
          400: "#639ecd",
          500: "#3e81bd",
          600: "#2d67a1",
          700: "#255282",
          800: "#1a365d", // Deep navy primary
          900: "#0f2038",
          950: "#081324",
        },
        surface: {
          bg: "#f8fafc",
          muted: "#f1f5f9",
          border: "#e2e8f0",
          subtle: "#64748b",
          text: "#0f172a",
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#cbd5e1",
          400: "#94a3b8",
          500: "#64748b",
          600: "#475569",
          700: "#334155",
          800: "#1e293b",
          900: "#0f172a",
        },
      },
      boxShadow: {
        xs: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
}

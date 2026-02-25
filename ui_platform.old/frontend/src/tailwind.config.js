/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}", // Scan all TS/TSX files
  ],
  darkMode: "class", // html.dark enables dark mode
  theme: {
    extend: {
      colors: {
        primary: "var(--color-primary)",
        secondary: "var(--color-secondary)",
        background: "var(--color-background)",
        surface: "var(--color-surface)",
        textPrimary: "var(--color-textPrimary)",
        textSecondary: "var(--color-textSecondary)",
        accent: "var(--color-accent)",
        error: "var(--color-error)",
        success: "var(--color-success)",
        warning: "var(--color-warning)",
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography"),
  ],
}

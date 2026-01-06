// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/tailwind.config.js
//
// Description:
//   TailwindCSS configuration for the Agentic System frontend. Supports
//   dark mode, theme customization, JIT compilation, and purge for production.
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

/** @type {import('tailwindcss').Config} */
module.exports = {
  // Enable JIT mode (just-in-time compilation)
  mode: 'jit',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}', // Include all source files for purging
  ],
  darkMode: 'class', // Enable class-based dark mode
  theme: {
    extend: {
      colors: {
        primary: '#4f46e5',   // Indigo 600
        secondary: '#6366f1', // Indigo 500
        accent: '#facc15',    // Amber 400
        neutral: '#1f2937',   // Gray 800
        background: '#f9fafb',
        'background-dark': '#111827',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
        mono: ['Fira Code', 'monospace'],
      },
      spacing: {
        sidebar: '280px',  // Default sidebar width
      },
      borderRadius: {
        lg: '12px',
      },
      boxShadow: {
        panel: '0 4px 12px rgba(0,0,0,0.1)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),       // Better form styles
    require('@tailwindcss/typography'),  // Prose support for docs & prompts
    require('@tailwindcss/aspect-ratio') // Aspect ratio helper (e.g., for React Flow nodes)
  ],
}



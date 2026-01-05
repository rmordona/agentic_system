// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/postcss.config.js
//
// Description:
//   PostCSS configuration for the Agentic System frontend.
//   Integrates TailwindCSS with autoprefixer for cross-browser compatibility.
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {}, // Automatically adds vendor prefixes for CSS rules
  },
}


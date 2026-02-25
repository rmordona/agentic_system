// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/components/styles/theme.ts
//
// Description:
//   Centralized theme management for the UI Platform. Provides color palettes,
//   light/dark modes, and utility functions to dynamically switch and apply
//   themes across the application. Compatible with TailwindCSS or custom CSS-in-JS.
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

export type ThemeMode = 'light' | 'dark'

export interface ThemeColors {
  primary: string
  secondary: string
  background: string
  surface: string
  textPrimary: string
  textSecondary: string
  accent: string
  error: string
  success: string
  warning: string
}

// ------------------------------
// Base Theme Palettes
// ------------------------------

/** Light mode color palette */
export const lightTheme: ThemeColors = {
  primary: '#1D4ED8',         // Blue 700
  secondary: '#2563EB',       // Blue 600
  background: '#F9FAFB',      // Gray 50
  surface: '#FFFFFF',         // White
  textPrimary: '#111827',     // Gray 900
  textSecondary: '#6B7280',   // Gray 500
  accent: '#F59E0B',          // Amber 500
  error: '#DC2626',           // Red 600
  success: '#16A34A',         // Green 600
  warning: '#D97706',         // Amber 600
}

/** Dark mode color palette */
export const darkTheme: ThemeColors = {
  primary: '#3B82F6',         // Blue 500
  secondary: '#60A5FA',       // Blue 400
  background: '#111827',      // Gray 900
  surface: '#1F2937',         // Gray 800
  textPrimary: '#F9FAFB',     // Gray 50
  textSecondary: '#9CA3AF',   // Gray 400
  accent: '#FBBF24',          // Amber 400
  error: '#EF4444',           // Red 500
  success: '#22C55E',         // Green 500
  warning: '#F59E0B',         // Amber 500
}

// ------------------------------
// Theme Utility Functions
// ------------------------------

/**
 * Apply a theme mode by adding a class to the <html> element
 * @param mode - 'light' or 'dark'
 */
export function applyTheme(mode: ThemeMode) {
  const root = document.documentElement
  if (mode === 'dark') {
    root.classList.add('dark')
    root.classList.remove('light')
  } else {
    root.classList.add('light')
    root.classList.remove('dark')
  }
}

/**
 * Get the current theme mode from the HTML class or default to light
 * @returns ThemeMode - 'light' or 'dark'
 */
export function getCurrentTheme(): ThemeMode {
  const root = document.documentElement
  if (root.classList.contains('dark')) return 'dark'
  return 'light'
}

/**
 * Toggle between light and dark themes
 * @returns ThemeMode - the new theme mode after toggle
 */
export function toggleTheme(): ThemeMode {
  const current = getCurrentTheme()
  const next = current === 'light' ? 'dark' : 'light'
  applyTheme(next)
  return next
}

/**
 * Retrieve the active color palette based on current theme mode
 * @returns ThemeColors - the active color palette
 */
export function getActiveThemeColors(): ThemeColors {
  return getCurrentTheme() === 'dark' ? darkTheme : lightTheme
}

/**
 * Set a custom theme dynamically (merge overrides with existing palette)
 * @param overrides Partial<ThemeColors> - colors to override
 * @param mode Optional theme mode ('light' | 'dark'), default current
 */
export function setCustomTheme(overrides: Partial<ThemeColors>, mode?: ThemeMode) {
  const themeMode = mode || getCurrentTheme()
  const baseTheme = themeMode === 'dark' ? darkTheme : lightTheme
  const customTheme: ThemeColors = { ...baseTheme, ...overrides }

  // Apply custom properties to root CSS variables
  const root = document.documentElement
  Object.entries(customTheme).forEach(([key, value]) => {
    root.style.setProperty(`--color-${key}`, value)
  })
}


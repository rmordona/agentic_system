// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/auth.ts
//
// Description:
//   Centralized authentication and authorization utilities for the frontend.
//
//   Responsibilities:
//     - JWT token lifecycle management
//     - Auth state helpers
//     - Role / mode detection (developer vs user)
//     - Logout & session invalidation
//
//   This module is intentionally framework-agnostic so it can be reused
//   by React components, hooks, route guards, and API clients.
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

export type UserMode = 'developer' | 'user'

const ACCESS_TOKEN_KEY = 'access_token'
const USER_MODE_KEY = 'user_mode'

// -----------------------------------------------------------------------------
// Token Management
// -----------------------------------------------------------------------------

/**
 * Persist JWT access token securely.
 */
export function setAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token)
}

/**
 * Retrieve stored JWT access token.
 */
export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

/**
 * Remove JWT access token (logout).
 */
export function clearAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
}

// -----------------------------------------------------------------------------
// User Mode Management
// -----------------------------------------------------------------------------

/**
 * Persist current UI user mode.
 * Developer mode unlocks graph editing, observability, etc.
 */
export function setUserMode(mode: UserMode): void {
  localStorage.setItem(USER_MODE_KEY, mode)
}

/**
 * Retrieve current UI user mode.
 * Defaults to `user` for safety.
 */
export function getUserMode(): UserMode {
  return (localStorage.getItem(USER_MODE_KEY) as UserMode) || 'user'
}

/**
 * Check whether the UI is currently in developer mode.
 */
export function isDeveloperMode(): boolean {
  return getUserMode() === 'developer'
}

// -----------------------------------------------------------------------------
// Auth State Helpers
// -----------------------------------------------------------------------------

/**
 * Determine whether a user is authenticated.
 */
export function isAuthenticated(): boolean {
  return !!getAccessToken()
}

/**
 * Perform a full client-side logout.
 */
export function logout(): void {
  clearAccessToken()
  localStorage.removeItem(USER_MODE_KEY)
  window.location.href = '/login'
}


// src/app/auth.ts
export async function login(username: string, password: string): Promise<boolean> {
  // Implement actual login logic here
  return username === 'admin' && password === 'password'
}

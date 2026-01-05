// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/api/client.ts
//
// Description:
//   Centralized HTTP client for all REST API calls.
//
//   Responsibilities:
//     - JWT token attachment
//     - Automatic JSON handling
//     - Standardized error handling
//     - Request/response typing
//     - Auth-aware request lifecycle
//
//   This client is used by:
//     - workspace APIs
//     - graph APIs
//     - run execution APIs
//     - authentication APIs
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

/* eslint-disable @typescript-eslint/no-explicit-any */

export interface ApiError {
  status: number
  message: string
  details?: any
}

export interface ApiClientConfig {
  baseUrl: string
  getAccessToken?: () => string | null
  onUnauthorized?: () => void
}

/**
 * Production-grade API client abstraction
 */
export class ApiClient {
  private baseUrl: string
  private getAccessToken?: () => string | null
  private onUnauthorized?: () => void

  constructor(config: ApiClientConfig) {
    this.baseUrl = config.baseUrl
    this.getAccessToken = config.getAccessToken
    this.onUnauthorized = config.onUnauthorized
  }

  // ---------------------------------------------------------------------------
  // Core Request Method
  // ---------------------------------------------------------------------------

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    }

    const token = this.getAccessToken?.()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    })

    if (response.status === 401) {
      this.onUnauthorized?.()
      throw {
        status: 401,
        message: 'Unauthorized',
      } satisfies ApiError
    }

    if (!response.ok) {
      const errorBody = await response.json().catch(() => null)
      throw {
        status: response.status,
        message: errorBody?.detail || response.statusText,
        details: errorBody,
      } satisfies ApiError
    }

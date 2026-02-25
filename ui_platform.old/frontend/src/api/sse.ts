// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/api/sse.ts
//
// Description:
//   Production-grade Server-Sent Events (SSE) client.
//
//   Responsibilities:
//     - Connect to FastAPI SSE endpoints
//     - Handle agent run streams
//     - Stream node/edge execution events
//     - Provide clean lifecycle management
//
//   Used for:
//     - agent execution observability
//     - graph node highlighting
//     - real-time logs and outputs
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

export interface SSEMessage<T = any> {
  event?: string
  data: T
}

export interface SSEClientOptions {
  url: string
  accessToken?: string
  onMessage: (msg: SSEMessage) => void
  onError?: (err: Event) => void
  onOpen?: () => void
}

/**
 * Production-safe SSE client abstraction
 */
export class SSEClient {
  private eventSource?: EventSource
  private options: SSEClientOptions

  constructor(options: SSEClientOptions) {
    this.options = options
  }

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  connect() {
    if (this.eventSource) return

    const url = new URL(this.options.url, window.location.origin)

    if (this.options.accessToken) {
      url.searchParams.set('token', this.options.accessToken)
    }

    this.eventSource = new EventSource(url.toString(), {
      withCredentials: false,
    })

    this.eventSource.onopen = () => {
      this.options.onOpen?.()
    }

    this.eventSource.onerror = (err) => {
      this.options.onError?.(err)
      this.close()
    }

    this.eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        this.options.onMessage({
          event: event.type,
          data: parsed,
        })
      } catch {
        this.options.onMessage({
          event: event.type,
          data: event.data,
        })
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Cleanup
  // ---------------------------------------------------------------------------

  close() {
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = undefined
    }
  }

  isConnected(): boolean {
    return !!this.eventSource
  }
}

/**
 * Helper factory for agent run SSE streams
 */
export function createRunSSE(
  runId: string,
  onMessage: (msg: SSEMessage) => void
): SSEClient {
  return new SSEClient({
    url: `/api/runs/${runId}/events`,
    accessToken: localStorage.getItem('access_token') || undefined,
    onMessage,
  })
}

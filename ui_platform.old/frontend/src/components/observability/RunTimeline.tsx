// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/components/observability/RunTimeline.tsx
//
// Description:
//   Displays a chronological timeline of stages and events for a workflow run.
//   Useful for observability of workflows, debugging, and auditing.
//
// Features:
//   - Shows each stage with timestamp, status, and optional description
//   - Highlights current running stage
//   - Scrollable timeline for long workflows
//   - Can integrate with SSE to update in real-time
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

import React from 'react'

interface TimelineEvent {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  timestamp: string
  description?: string
}

interface RunTimelineProps {
  events: TimelineEvent[]
  currentStageId?: string
}

/**
 * RunTimeline renders a vertical chronological timeline of workflow stages/events.
 *
 * @param events - List of timeline events with status, timestamp, and optional description
 * @param currentStageId - ID of the currently active stage to highlight
 */
const RunTimeline: React.FC<RunTimelineProps> = ({ events, currentStageId }) => {
  return (
    <div className="run-timeline overflow-y-auto p-2 max-h-full">
      {events.map((event) => {
        const isActive = event.id === currentStageId
        return (
          <div
            key={event.id}
            className={`timeline-event flex items-start space-x-2 py-1 px-2 rounded ${
              isActive ? 'bg-blue-100 border-l-4 border-blue-500' : 'bg-gray-50'
            }`}
          >
            <div className="status-indicator w-3 h-3 mt-1 rounded-full flex-shrink-0"
                 style={{
                   backgroundColor:
                     event.status === 'completed'
                       ? 'green'
                       : event.status === 'running'
                       ? 'blue'
                       : event.status === 'failed'
                       ? 'red'
                       : 'gray',
                 }}
            />
            <div className="event-content flex-1">
              <div className="flex justify-between items-center">
                <span className="event-name font-medium">{event.name}</span>
                <span className="event-timestamp text-xs text-gray-500">{event.timestamp}</span>
              </div>
              {event.description && <p className="text-sm text-gray-600">{event.description}</p>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default RunTimeline

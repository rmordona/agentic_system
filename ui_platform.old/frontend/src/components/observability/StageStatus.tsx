// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/components/observability/StageStatus.tsx
//
// Description:
//   Displays a concise status view for a single stage within a workflow run.
//   Useful for highlighting completion, errors, and live progress.
//
// Features:
//   - Shows stage name and current status
//   - Optional progress bar for stages with measurable progress
//   - Color-coded statuses: pending, running, completed, failed
//   - Can integrate with SSE or polling for live updates
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

import React from 'react'

interface StageStatusProps {
  stageId: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress?: number // 0-100
}

/**
 * StageStatus component displays status and optional progress of a single workflow stage.
 *
 * @param stageId - Unique identifier for the stage
 * @param name - Display name of the stage
 * @param status - Current stage status (pending, running, completed, failed)
 * @param progress - Optional progress percentage
 */
const StageStatus: React.FC<StageStatusProps> = ({ stageId, name, status, progress }) => {
  const getColor = () => {
    switch (status) {
      case 'completed':
        return 'green'
      case 'running':
        return 'blue'
      case 'failed':
        return 'red'
      default:
        return 'gray'
    }
  }

  return (
    <div className="stage-status flex flex-col space-y-1 p-2 border rounded bg-white shadow-sm">
      <div className="flex justify-between items-center">
        <span className="stage-name font-medium">{name}</span>
        <span
          className="stage-badge px-2 py-0.5 text-xs rounded-full text-white"
          style={{ backgroundColor: getColor() }}
        >
          {status.toUpperCase()}
        </span>
      </div>
      {progress !== undefined && (
        <div className="progress-bar w-full h-2 bg-gray-200 rounded">
          <div
            className="progress-fill h-full rounded"
            style={{ width: `${progress}%`, backgroundColor: getColor() }}
          />
        </div>
      )}
    </div>
  )
}

export default StageStatus

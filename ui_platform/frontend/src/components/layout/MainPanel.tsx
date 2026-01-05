// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/components/layout/MainPanel.tsx
//
// Description:
//   Main content panel for the Agentic System UI platform.
//   Displays primary views such as workflow graphs, node/edge editors, 
//   prompt input/output panels, and other workspace content.
//
// Features:
//   - Responsive layout to occupy remaining space beside SideBar
//   - Scrollable content for large graphs or logs
//   - Accepts children components to render dynamic views
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

import React, { ReactNode } from 'react'

interface MainPanelProps {
  children: ReactNode
  className?: string
}

/**
 * MainPanel component wraps the main content area of the application.
 * 
 * @param children - React nodes to render inside the panel
 * @param className - Optional additional CSS classes
 */
const MainPanel: React.FC<MainPanelProps> = ({ children, className = '' }) => {
  return (
    <div
      className={`main-panel flex-1 overflow-auto p-4 bg-gray-50 ${className}`}
      style={{ minHeight: '100vh' }}
    >
      {children}
    </div>
  )
}

export default MainPanel

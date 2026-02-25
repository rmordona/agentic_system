// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/components/layout/SideBar.tsx
//
// Description:
//   Collapsible sidebar for navigation, workspace selection, and tools.
//   Supports developer and user modes with view-specific menus.
//
// Features:
//   - Collapsible panel with toggle button
//   - Navigation and tool sections
//   - Developer/User mode switching support
//   - Smooth transitions using CSS
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------
import React, { ReactNode, useState } from 'react'

interface SideBarProps {
  children: ReactNode
  initialCollapsed?: boolean
}

/**
 * SideBar component for navigation and tool panels.
 * Can collapse into a smaller vertical panel.
 *
 * @param children - React nodes to render inside the sidebar
 * @param initialCollapsed - Whether the sidebar is collapsed initially
 */

const SideBar: React.FC<SideBarProps> = ({ children, initialCollapsed = false }) => {
  const [collapsed, setCollapsed] = useState(initialCollapsed)

  const toggleCollapse = () => setCollapsed((prev) => !prev)

  return (
    <div
      className={`flex flex-col bg-white dark:bg-gray-800 border-r dark:border-gray-700 transition-all duration-300 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      <button
        onClick={toggleCollapse}
        className="p-2 border-b dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700"
        aria-label="Toggle sidebar"
      >
        {collapsed ? '➡️' : '⬅️'}
      </button>
      <div className="flex-1 overflow-auto">{children}</div>
    </div>
  )
}

export default SideBar

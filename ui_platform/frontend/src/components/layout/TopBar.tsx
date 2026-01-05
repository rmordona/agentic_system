// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/components/layout/TopBar.tsx
//
// Description:
//   Top bar panel for global navigation, view switching, authentication controls,
//   and user/developer mode toggling.
//
// Features:
//   - Switch between developer and user views
//   - Workspace or stage selection
//   - Displays user information and logout button
//   - Fixed top layout for consistent navigation
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

import React from 'react'

interface TopBarProps {
  userName?: string
  developerMode?: boolean
  onToggleMode?: () => void
  children?: React.ReactNode
}

/**
 * TopBar component renders the global navigation and controls.
 *
 * @param userName - Current logged-in user
 * @param developerMode - Whether developer mode is active
 * @param onToggleMode - Callback to toggle developer/user mode
 * @param children - Optional additional components (e.g., search bar)
 */
const TopBar: React.FC<TopBarProps> = ({ userName, developerMode = false, onToggleMode, children }) => {
  return (
    <header className="top-bar flex items-center justify-between bg-white border-b border-gray-200 px-4 h-16">
      <div className="left-section flex items-center space-x-4">
        <h1 className="text-lg font-semibold">Agentic System</h1>
        {onToggleMode && (
          <button
            className="mode-toggle px-2 py-1 bg-gray-100 border rounded hover:bg-gray-200"
            onClick={onToggleMode}
          >
            {developerMode ? 'Developer Mode' : 'User Mode'}
          </button>
        )}
      </div>
      <div className="right-section flex items-center space-x-4">
        {children}
        {userName && <span className="user-name font-medium">{userName}</span>}
        <button className="logout px-2 py-1 bg-red-100 border rounded hover:bg-red-200">Logout</button>
      </div>
    </header>
  )
}

export default TopBar

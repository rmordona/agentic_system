// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: src/components/layout/AuthLayout.tsx
//
// Description:
//   Layout for authenticated pages with TopBar, SideBar, and MainPanel.
// -----------------------------------------------------------------------------

import React from 'react'
import { Outlet } from 'react-router-dom'
import TopBar from './TopBar'
import SideBar from './SideBar'
import MainPanel from './MainPanel'

const AuthLayout: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-50">
      {/* Top Bar */}
      <TopBar />

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-white dark:bg-gray-800 border-r dark:border-gray-700 overflow-y-auto">
          <SideBar />
        </aside>

        {/* Main Content Panel */}
        <main className="flex-1 overflow-auto p-4">
          <MainPanel>
            {/* Render children if passed, otherwise render nested route */}
            {children || <Outlet />}
          </MainPanel>
        </main>
      </div>
    </div>
  )
}

export default AuthLayout

// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: src/components/layout/PublicLayout.tsx
//
// Description:
//   Layout for public (unauthenticated) pages.
// -----------------------------------------------------------------------------

import React from 'react'
import { Outlet } from 'react-router-dom'

const PublicLayout: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="w-full max-w-md p-6">
        {/* Render children if provided, otherwise render nested route */}
        {children || <Outlet />}
      </div>
    </div>
  )
}

export default PublicLayout

import React from 'react'
import { Outlet } from 'react-router-dom'

const PublicLayout: React.FC<{ children?: React.ReactNode }> = ({ children }) => (
  <div className="min-h-screen flex flex-col items-center justify-center bg-gray-800 text-white">
    <div className="w-full max-w-md p-6 bg-gray-900 rounded shadow">
      {children || <Outlet />}
    </div>
  </div>
)

export default PublicLayout

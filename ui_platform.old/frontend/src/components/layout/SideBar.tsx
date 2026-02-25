import React from 'react'

const SideBar: React.FC<{ className?: string }> = ({ className, children }) => (
  <aside className={`${className} w-64 bg-green-600 text-white p-4`}>
    SIDEBAR PLACEHOLDER
  </aside>
)

export default SideBar

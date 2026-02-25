import React from 'react'

const MainPanel: React.FC<{ className?: string; children?: React.ReactNode }> = ({ className, children }) => (
  <main className={`${className} flex-1 bg-orange-300 p-4`}>
    {children || 'MAINPANEL PLACEHOLDER'}
  </main>
)

export default MainPanel

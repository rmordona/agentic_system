import React, { Suspense } from 'react'
import { useRoutes } from 'react-router-dom'
import { routes } from './routes'

const App: React.FC = () => {
  const element = useRoutes(routes)

  return (
    <Suspense fallback={<div className="p-4">Loading…</div>}>
      {element}
    </Suspense>
  )
}

export default App

import { redirect } from 'react-router-dom'

/*
export const requireAuthLoader = () => {
  const bypassAuth = localStorage.getItem('bypassAuth') === 'true'
  if (!bypassAuth) return redirect('/login')
  return null
}
  */
export const requireAuthLoader = () => {
  // Temporarily bypass authentication for triage
  // Comment out the redirect for now
  // const bypassAuth = localStorage.getItem('bypassAuth') === 'true'
  // if (!bypassAuth) return redirect('/login')

  // Always allow access
  return null
}

// -----------------------------------------------------------------------------
// Temporary authentication service (bypass mode)
// Replace with real API calls later
// -----------------------------------------------------------------------------

const FAKE_TOKEN_KEY = 'accessToken'

export async function login(username: string, password: string): Promise<void> {
  // Simulate network latency
  await new Promise((resolve) => setTimeout(resolve, 600))

  if (!username || !password) {
    throw new Error('Username and password are required')
  }

  // TEMP: accept any credentials
  localStorage.setItem(FAKE_TOKEN_KEY, 'dev-bypass-token')
}

export function logout() {
  localStorage.removeItem(FAKE_TOKEN_KEY)
}

export function isAuthenticated(): boolean {
  return Boolean(localStorage.getItem(FAKE_TOKEN_KEY))
}


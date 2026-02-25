// src/services/api.ts
export const api = async (endpoint: string, options: RequestInit = {}, accessToken?: string) => {
  const baseUrl = "http://localhost:8000/api/v1"; // ✅ must match backend
  const res = await fetch(`${baseUrl}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) throw await res.json(); // keeps your error handling
  return res.json();
};
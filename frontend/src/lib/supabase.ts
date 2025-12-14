// API configuration for local backend
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Helper function for authenticated requests
export const apiRequest = async (endpoint: string, options: RequestInit = {}) => {
  const token = localStorage.getItem('auth_token')
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  }
  
  return fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  })
}

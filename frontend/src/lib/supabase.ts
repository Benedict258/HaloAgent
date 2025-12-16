import { createClient } from '@supabase/supabase-js'

// API configuration
export const API_URL = import.meta.env.VITE_API_URL || 'https://haloagent.onrender.com'

// Supabase client
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

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

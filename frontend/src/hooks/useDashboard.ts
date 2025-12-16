import { useState, useEffect } from 'react'
import { API_URL } from '@/lib/supabase'

const defaultStats = {
  total_orders: 0,
  total_contacts: 0,
  pending_orders: 0,
  total_revenue: 0
}

const authHeaders = () => {
  const token = localStorage.getItem('auth_token')
  if (!token) {
    return null
  }
  return {
    Authorization: `Bearer ${token}`
  }
}

export const useDashboardStats = () => {
  const [stats, setStats] = useState(defaultStats)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const headers = authHeaders()
    if (!headers) {
      setError('Missing authentication token')
      setLoading(false)
      return
    }

    const controller = new AbortController()

    fetch(`${API_URL}/api/dashboard/stats`, {
      headers,
      signal: controller.signal
    })
      .then(res => {
        if (!res.ok) {
          throw new Error(`Failed to load stats (${res.status})`)
        }
        return res.json()
      })
      .then(data => {
        setStats(prev => ({ ...prev, ...data }))
        setError(null)
      })
      .catch(err => {
        if (err.name === 'AbortError') return
        console.error('Failed to fetch stats:', err)
        setError(err.message)
      })
      .finally(() => setLoading(false))

    return () => controller.abort()
  }, [])

  return { stats, loading, error }
}

export const useRecentOrders = () => {
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const headers = authHeaders()
    if (!headers) {
      setError('Missing authentication token')
      setLoading(false)
      return
    }

    const controller = new AbortController()

    fetch(`${API_URL}/api/dashboard/recent-orders`, {
      headers,
      signal: controller.signal
    })
      .then(res => {
        if (!res.ok) {
          throw new Error(`Failed to load orders (${res.status})`)
        }
        return res.json()
      })
      .then(data => {
        setOrders(Array.isArray(data) ? data : [])
        setError(null)
      })
      .catch(err => {
        if (err.name === 'AbortError') return
        console.error('Failed to fetch orders:', err)
        setError(err.message)
      })
      .finally(() => setLoading(false))

    return () => controller.abort()
  }, [])

  return { orders, loading, error }
}

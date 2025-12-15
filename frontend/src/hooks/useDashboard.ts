import { useState, useEffect } from 'react'
import { API_URL } from '@/lib/supabase'

export const useDashboardStats = () => {
  const [stats, setStats] = useState({
    total_orders: 0,
    total_contacts: 0,
    pending_orders: 0,
    total_revenue: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/api/dashboard/stats`)
      .then(res => res.json())
      .then(data => {
        setStats(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch stats:', err)
        setLoading(false)
      })
  }, [])

  return { stats, loading }
}

export const useRecentOrders = () => {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/api/dashboard/recent-orders`)
      .then(res => res.json())
      .then(data => {
        setOrders(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch orders:', err)
        setLoading(false)
      })
  }, [])

  return { orders, loading }
}

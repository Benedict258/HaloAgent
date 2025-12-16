import { useState, useEffect } from 'react'
import { API_URL } from '@/lib/supabase'
import { BackButton } from '@/components/ui/back-button'

export default function RevenuePage() {
  const [stats, setStats] = useState({
    total_revenue: 0,
    orders_count: 0,
    avg_order_value: 0,
    pending_revenue: 0
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const authHeaders = () => {
    const token = localStorage.getItem('auth_token')
    if (!token) return null
    return { Authorization: `Bearer ${token}` }
  }

  useEffect(() => {
    fetchRevenue()
  }, [])

  const fetchRevenue = async () => {
    setLoading(true)
    try {
      const headers = authHeaders()
      if (!headers) {
        setError('Please sign in again to load revenue.')
        setStats({ total_revenue: 0, orders_count: 0, avg_order_value: 0, pending_revenue: 0 })
        return
      }
      const res = await fetch(`${API_URL}/api/orders?business_id=sweetcrumbs_001`, { headers })
      if (!res.ok) {
        throw new Error(`Failed to fetch revenue (${res.status})`)
      }
      const orders = await res.json()
      
      if (Array.isArray(orders)) {
        const total = orders.reduce((sum, order) => sum + (order.total_amount || 0), 0)
        const completed = orders.filter(o => o.status === 'completed')
        const completedRevenue = completed.reduce((sum, order) => sum + (order.total_amount || 0), 0)
        const pending = orders.filter(o => ['pending_payment', 'awaiting_confirmation'].includes(o.status))
        const pendingRevenue = pending.reduce((sum, order) => sum + (order.total_amount || 0), 0)
        
        setStats({
          total_revenue: completedRevenue,
          orders_count: completed.length,
          avg_order_value: completed.length > 0 ? completedRevenue / completed.length : 0,
          pending_revenue: pendingRevenue
        })
        setError(null)
      }
    } catch (err) {
      console.error('Failed to fetch revenue:', err)
      setError(err instanceof Error ? err.message : 'Unable to load revenue right now.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 bg-white min-h-screen">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold text-black">Revenue</h1>
            <p className="text-gray-600 mt-1">Track your business performance</p>
          </div>
          <BackButton label="Back to overview" className="text-sm" />
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-600">Loading revenue data...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <p className="text-sm text-gray-600 mb-2">Total Revenue</p>
              <p className="text-3xl font-bold text-black">₦{stats.total_revenue.toLocaleString()}</p>
              <p className="text-xs text-green-600 mt-2">From completed orders</p>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <p className="text-sm text-gray-600 mb-2">Completed Orders</p>
              <p className="text-3xl font-bold text-black">{stats.orders_count}</p>
              <p className="text-xs text-gray-500 mt-2">Successfully delivered</p>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <p className="text-sm text-gray-600 mb-2">Avg Order Value</p>
              <p className="text-3xl font-bold text-black">₦{Math.round(stats.avg_order_value).toLocaleString()}</p>
              <p className="text-xs text-gray-500 mt-2">Per completed order</p>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <p className="text-sm text-gray-600 mb-2">Pending Revenue</p>
              <p className="text-3xl font-bold text-yellow-600">₦{stats.pending_revenue.toLocaleString()}</p>
              <p className="text-xs text-gray-500 mt-2">Awaiting payment</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

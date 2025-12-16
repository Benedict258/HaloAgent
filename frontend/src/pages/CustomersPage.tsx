import { useState, useEffect } from 'react'
import { API_URL } from '@/lib/supabase'
import { BackButton } from '@/components/ui/back-button'

interface Customer {
  id: number
  phone_number: string
  name: string | null
  loyalty_points: number
  order_count: number
  created_at: string
  status: string
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const authHeaders = () => {
    const token = localStorage.getItem('auth_token')
    if (!token) return null
    return { Authorization: `Bearer ${token}` }
  }

  useEffect(() => {
    fetchCustomers()
  }, [])

  const fetchCustomers = async () => {
    setLoading(true)
    try {
      const headers = authHeaders()
      if (!headers) {
        setError('Please sign in again to load customers.')
        setCustomers([])
        return
      }
      const res = await fetch(`${API_URL}/api/contacts?business_id=sweetcrumbs_001`, { headers })
      if (!res.ok) {
        throw new Error(`Failed to load customers (${res.status})`)
      }
      const data = await res.json()
      setCustomers(Array.isArray(data) ? data : [])
      setError(null)
    } catch (err) {
      console.error('Failed to fetch customers:', err)
      setCustomers([])
      setError(err instanceof Error ? err.message : 'Unable to load customers right now.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 bg-white min-h-screen">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold text-black">Customers</h1>
            <p className="text-gray-600 mt-1">Manage your customer relationships</p>
          </div>
          <BackButton label="Back to overview" className="text-sm" />
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-600">Loading customers...</div>
        ) : error ? (
          <div className="text-center py-12 text-red-600">{error}</div>
        ) : customers.length === 0 ? (
          <div className="text-center py-12 text-gray-600">No customers yet</div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Phone</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Orders</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Loyalty Points</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Joined</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {customers.map((customer) => (
                  <tr key={customer.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-black">
                      {customer.name || 'Unknown'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{customer.phone_number}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{customer.order_count || 0}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{customer.loyalty_points || 0}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        customer.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {customer.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {new Date(customer.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

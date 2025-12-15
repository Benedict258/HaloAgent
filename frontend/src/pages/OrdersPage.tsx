import { useState, useEffect } from 'react'
import { API_URL } from '@/lib/supabase'

interface Order {
  id: number
  contact_id: number
  items: any[]
  total_amount: number
  status: string
  created_at: string
  payment_receipt_url?: string
  contacts: {
    name: string
    phone_number: string
  }
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    fetchOrders()
  }, [filter])

  const fetchOrders = async () => {
    try {
      const url = filter === 'all' 
        ? `${API_URL}/api/orders?business_id=sweetcrumbs_001`
        : `${API_URL}/api/orders?business_id=sweetcrumbs_001&status=${filter}`
      const res = await fetch(url)
      const data = await res.json()
      setOrders(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch orders:', err)
      setOrders([])
    } finally {
      setLoading(false)
    }
  }

  const approvePayment = async (orderId: string) => {
    try {
      await fetch(`${API_URL}/api/orders/${orderId}/approve-payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved: true })
      })
      fetchOrders()
    } catch (err) {
      console.error('Failed to approve payment:', err)
    }
  }

  const updateStatus = async (orderId: string, status: string) => {
    try {
      await fetch(`${API_URL}/api/orders/${orderId}/update-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      })
      fetchOrders()
    } catch (err) {
      console.error('Failed to update status:', err)
    }
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending_payment: 'bg-yellow-100 text-yellow-800',
      awaiting_confirmation: 'bg-blue-100 text-blue-800',
      paid: 'bg-green-100 text-green-800',
      preparing: 'bg-purple-100 text-purple-800',
      ready_for_pickup: 'bg-indigo-100 text-indigo-800',
      completed: 'bg-gray-100 text-gray-800',
      cancelled: 'bg-red-100 text-red-800'
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }

  return (
    <div className="p-6 bg-white min-h-screen">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-black">Orders</h1>
          <p className="text-gray-600 mt-1">Manage customer orders and payments</p>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-200">
          {['all', 'pending_payment', 'awaiting_confirmation', 'paid', 'preparing', 'ready_for_pickup', 'completed'].map(status => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                filter === status
                  ? 'border-brand text-brand'
                  : 'border-transparent text-gray-600 hover:text-black'
              }`}
            >
              {status.replace('_', ' ').toUpperCase()}
            </button>
          ))}
        </div>

        {/* Orders List */}
        {loading ? (
          <div className="text-center py-12 text-gray-600">Loading orders...</div>
        ) : orders.length === 0 ? (
          <div className="text-center py-12 text-gray-600">No orders found</div>
        ) : (
          <div className="space-y-4">
            {orders.map(order => (
              <div key={order.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-black">Order #{order.id}</h3>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(order.status)}`}>
                        {order.status.replace('_', ' ')}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-gray-600">Customer</p>
                        <p className="font-medium text-black">{order.contacts?.name || 'Unknown'}</p>
                        <p className="text-gray-500">{order.contacts?.phone_number}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Items</p>
                        <p className="font-medium text-black">
                          {Array.isArray(order.items) ? order.items.map((item: any) => item.name).join(', ') : 'N/A'}
                        </p>
                        <p className="text-gray-500">Qty: {Array.isArray(order.items) ? order.items.reduce((sum: number, item: any) => sum + (item.quantity || 1), 0) : 0}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Amount</p>
                        <p className="font-bold text-black">₦{order.total_amount.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Date</p>
                        <p className="text-black">{new Date(order.created_at).toLocaleDateString()}</p>
                      </div>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-col gap-2 ml-4">
                    {order.status === 'awaiting_confirmation' && (
                      <>
                        <button
                          onClick={() => approvePayment(order.id)}
                          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium"
                        >
                          Approve Payment
                        </button>
                        {order.payment_receipt_url && (
                          <a
                            href={order.payment_receipt_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium text-center"
                          >
                            View Receipt
                          </a>
                        )}
                      </>
                    )}
                    
                    {order.status === 'paid' && (
                      <button
                        onClick={() => updateStatus(order.id, 'preparing')}
                        className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium"
                      >
                        Start Preparing
                      </button>
                    )}
                    
                    {order.status === 'preparing' && (
                      <button
                        onClick={() => updateStatus(order.id, 'ready_for_pickup')}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium"
                      >
                        Mark Ready
                      </button>
                    )}
                    
                    {order.status === 'ready_for_pickup' && (
                      <button
                        onClick={() => updateStatus(order.id, 'completed')}
                        className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 text-sm font-medium"
                      >
                        Complete Order
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

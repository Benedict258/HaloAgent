import { useEffect, useMemo, useState } from 'react'
import { API_URL } from '@/lib/supabase'
import { BackButton } from '@/components/ui/back-button'

interface Contact {
  name: string
  phone_number: string
}

interface OrderItem {
  name: string
  quantity?: number
}

interface Order {
  id: number
  order_number?: string
  contact_id: number
  items: OrderItem[] | string | null
  total_amount: number
  status: string
  created_at: string
  updated_at?: string
  fulfillment_type?: string
  delivery_address?: string
  payment_receipt_url?: string
  payment_reference?: string
  contacts: Contact
}

interface ReceiptAnalysis {
  id: string
  order_id?: number
  analysis_type: string
  media_url?: string
  analysis: Record<string, any> | string | null
  created_at: string
}

interface PaymentReview extends Omit<Order, 'items'> {
  items?: OrderItem[] | string | null
  payment_receipt_uploaded_at?: string
  payment_receipt_analysis?: Record<string, any>
  latest_receipt_analysis?: ReceiptAnalysis & { analysis: Record<string, any> | string | null }
}

interface VisionInsight extends ReceiptAnalysis {
  contact_id?: number
  contacts?: Contact
  orders?: {
    order_number?: string
    payment_reference?: string
    total_amount?: number
  }
}

const STATUS_TABS = [
  'all',
  'payment_pending_review',
  'awaiting_confirmation',
  'pending_payment',
  'paid',
  'preparing',
  'ready_for_pickup',
  'completed',
]

const STATUS_COLORS: Record<string, string> = {
  payment_pending_review: 'bg-orange-100 text-orange-800',
  awaiting_confirmation: 'bg-blue-100 text-blue-800',
  pending_payment: 'bg-yellow-100 text-yellow-800',
  paid: 'bg-emerald-100 text-emerald-800',
  preparing: 'bg-purple-100 text-purple-800',
  ready_for_pickup: 'bg-indigo-100 text-indigo-800',
  completed: 'bg-gray-100 text-gray-800',
  cancelled: 'bg-red-100 text-red-800',
}

const formatCurrency = (value: number | string | undefined) => {
  if (typeof value === 'number') return `₦${value.toLocaleString()}`
  if (!value) return '₦0'
  const parsed = Number(value)
  return Number.isFinite(parsed) ? `₦${parsed.toLocaleString()}` : String(value)
}

const parseJson = (payload: unknown) => {
  if (!payload) return null
  if (typeof payload === 'object') return payload as Record<string, any>
  if (typeof payload === 'string') {
    try {
      return JSON.parse(payload)
    } catch {
      return { raw: payload }
    }
  }
  return null
}

const resolveItems = (items: Order['items']) => {
  if (!items) return []
  if (Array.isArray(items)) return items
  if (typeof items === 'string') {
    try {
      const parsed = JSON.parse(items)
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  }
  return []
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [ordersLoading, setOrdersLoading] = useState(true)
  const [ordersError, setOrdersError] = useState<string | null>(null)
  const [filter, setFilter] = useState('all')

  const [paymentReviews, setPaymentReviews] = useState<PaymentReview[]>([])
  const [reviewsLoading, setReviewsLoading] = useState(true)
  const [reviewsError, setReviewsError] = useState<string | null>(null)

  const [selectedReview, setSelectedReview] = useState<PaymentReview | null>(null)
  const [decisionNotes, setDecisionNotes] = useState('')
  const [submittingDecision, setSubmittingDecision] = useState(false)
  const [decisionError, setDecisionError] = useState<string | null>(null)

  const [visionEntries, setVisionEntries] = useState<VisionInsight[]>([])
  const [visionLoading, setVisionLoading] = useState(true)
  const [visionError, setVisionError] = useState<string | null>(null)

  const authHeaders = (extra: Record<string, string> = {}) => {
    const token = localStorage.getItem('auth_token')
    if (!token) return null
    return {
      Authorization: `Bearer ${token}`,
      ...extra,
    }
  }

  useEffect(() => {
    fetchOrders()
  }, [filter])

  useEffect(() => {
    fetchPaymentReviews()
    fetchVisionEntries()
  }, [])

  const fetchOrders = async () => {
    setOrdersLoading(true)
    try {
      const headers = authHeaders()
      if (!headers) {
        setOrdersError('Please sign in again to load orders.')
        setOrders([])
        return
      }
      const url = filter === 'all'
        ? `${API_URL}/api/orders`
        : `${API_URL}/api/orders?status=${filter}`
      const res = await fetch(url, { headers })
      if (!res.ok) {
        throw new Error(`Failed to load orders (${res.status})`)
      }
      const data = await res.json()
      setOrders(Array.isArray(data) ? data : [])
      setOrdersError(null)
    } catch (err) {
      console.error('Failed to fetch orders:', err)
      setOrders([])
      setOrdersError(err instanceof Error ? err.message : 'Unable to load orders right now.')
    } finally {
      setOrdersLoading(false)
    }
  }

  const fetchPaymentReviews = async () => {
    setReviewsLoading(true)
    try {
      const headers = authHeaders()
      if (!headers) {
        setReviewsError('Please sign in again to review payments.')
        setPaymentReviews([])
        return
      }
      const res = await fetch(`${API_URL}/api/orders/payment-reviews`, { headers })
      if (!res.ok) {
        throw new Error('Unable to load payment reviews.')
      }
      const data = await res.json()
      const normalized = (Array.isArray(data) ? data : []).map((review: PaymentReview) => ({
        ...review,
        latest_receipt_analysis: review.latest_receipt_analysis
          ? {
              ...review.latest_receipt_analysis,
              analysis: parseJson(review.latest_receipt_analysis.analysis),
            }
          : undefined,
      }))
      setPaymentReviews(normalized)
      setReviewsError(null)
    } catch (err) {
      console.error('Failed to fetch payment reviews:', err)
      setPaymentReviews([])
      setReviewsError(err instanceof Error ? err.message : 'Unable to load payment reviews right now.')
    } finally {
      setReviewsLoading(false)
    }
  }

  const fetchVisionEntries = async () => {
    setVisionLoading(true)
    try {
      const headers = authHeaders()
      if (!headers) {
        setVisionError('Please sign in again to view DINOV3 insights.')
        setVisionEntries([])
        return
      }
      const res = await fetch(`${API_URL}/api/vision/analyses?limit=25`, { headers })
      if (!res.ok) {
        throw new Error('Unable to load vision insights.')
      }
      const data = await res.json()
      const normalized = (Array.isArray(data) ? data : []).map(entry => ({
        ...entry,
        analysis: parseJson(entry.analysis),
      }))
      setVisionEntries(normalized)
      setVisionError(null)
    } catch (err) {
      console.error('Failed to fetch vision entries:', err)
      setVisionEntries([])
      setVisionError(err instanceof Error ? err.message : 'Unable to load DINOV3 insights right now.')
    } finally {
      setVisionLoading(false)
    }
  }

  const updateOrderStatus = async (orderId: number, status: string) => {
    try {
      const headers = authHeaders({ 'Content-Type': 'application/json' })
      if (!headers) {
        setOrdersError('Please sign in again before updating orders.')
        return
      }
      const res = await fetch(`${API_URL}/api/orders/${orderId}/update-status`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ status }),
      })
      if (!res.ok) throw new Error('Unable to update order status')
      fetchOrders()
    } catch (err) {
      console.error('Failed to update status:', err)
      setOrdersError('Unable to update order status right now.')
    }
  }

  const submitPaymentDecision = async (approved: boolean) => {
    if (!selectedReview) return
    setSubmittingDecision(true)
    setDecisionError(null)
    try {
      const headers = authHeaders({ 'Content-Type': 'application/json' })
      if (!headers) {
        setDecisionError('Please sign in again before taking an action.')
        return
      }
      const res = await fetch(`${API_URL}/api/orders/${selectedReview.id}/approve-payment`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ approved, notes: decisionNotes.trim() || undefined }),
      })
      if (!res.ok) {
        const detail = await res.text()
        throw new Error(detail || 'Unable to update payment status.')
      }
      await Promise.all([fetchPaymentReviews(), fetchOrders()])
      setSelectedReview(null)
      setDecisionNotes('')
    } catch (err) {
      console.error('Payment decision failed:', err)
      setDecisionError(err instanceof Error ? err.message : 'Unable to send decision right now.')
    } finally {
      setSubmittingDecision(false)
    }
  }

  const outstandingTotal = useMemo(() => {
    return paymentReviews.reduce((sum, review) => sum + (Number(review.total_amount) || 0), 0)
  }, [paymentReviews])

  const renderStatusBadge = (status: string) => {
    const color = STATUS_COLORS[status] || STATUS_COLORS.completed
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${color}`}>
        {status.replace(/_/g, ' ')}
      </span>
    )
  }

  const renderOrderItems = (items: Order['items']) => {
    const parsed = resolveItems(items)
    if (!parsed.length) return 'N/A'
    return parsed.map(item => `${item.name}${item.quantity ? ` x${item.quantity}` : ''}`).join(', ')
  }

  const renderAnalysisHints = (analysis: Record<string, any> | string | null | undefined) => {
    if (!analysis) return []
    if (typeof analysis === 'string') return [analysis]
    const hints: string[] = []
    if (Array.isArray(analysis.hints)) {
      analysis.hints.forEach((hint: unknown) => {
        if (typeof hint === 'string' && hint.trim()) {
          hints.push(hint.trim())
        }
      })
    }
    const summary = analysis.summary || analysis.description || analysis.note
    if (typeof summary === 'string') hints.push(summary)

    const amount = analysis.amount_detected || analysis.detected_amount || analysis.total || analysis.total_amount
    if (amount) hints.push(`Detected amount: ${formatCurrency(amount)}`)

    const reference = analysis.detected_reference || analysis.payment_reference || analysis.reference || analysis.ref
    if (reference) hints.push(`Reference: ${reference}`)

    const merchant = analysis.merchant || analysis.business_name
    if (merchant) hints.push(`Merchant: ${merchant}`)

    if (analysis.match_status && analysis.match_status !== 'needs_review') {
      hints.push(`Match status: ${analysis.match_status.replace(/_/g, ' ')}`)
    }

    if (!hints.length) {
      Object.entries(analysis).slice(0, 3).forEach(([key, value]) => {
        if (['summary', 'description', 'note'].includes(key)) return
        if (value === null || typeof value === 'object') return
        hints.push(`${key}: ${value}`)
      })
    }

    return hints
  }

  const closeModal = () => {
    setSelectedReview(null)
    setDecisionNotes('')
    setDecisionError(null)
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold text-black">Orders & Payments</h1>
            <p className="mt-1 text-gray-600">Review receipts, approve payments, and track fulfillment in one place.</p>
          </div>
          <BackButton label="Back to overview" className="text-sm" />
        </div>

        <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
          <div className="space-y-6">
            <section className="rounded-2xl border border-gray-200 bg-gray-50 p-5">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Payment review queue</p>
                  <h2 className="text-2xl font-semibold text-black">
                    {reviewsLoading ? 'Loading…' : `${paymentReviews.length} pending`}
                  </h2>
                  <p className="text-sm text-gray-600">{`Awaiting confirmation • ${formatCurrency(outstandingTotal)} outstanding`}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={fetchPaymentReviews}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:border-gray-400"
                  >
                    Refresh Queue
                  </button>
                  <button
                    onClick={fetchVisionEntries}
                    className="hidden rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:border-gray-400 md:block"
                  >
                    Refresh DINOV3
                  </button>
                </div>
              </div>

              {reviewsError && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{reviewsError}</p>}

              {reviewsLoading ? (
                <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-gray-500">
                  Fetching latest receipts…
                </div>
              ) : paymentReviews.length === 0 ? (
                <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-gray-500">
                  No payments waiting for review.
                </div>
              ) : (
                <div className="space-y-4">
                  {paymentReviews.map(review => (
                    <div key={review.id} className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-100">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-gray-800">
                            {review.order_number ? `Order #${review.order_number}` : `Order ${review.id}`}
                          </p>
                          <p className="text-xs text-gray-500">{new Date(review.updated_at || review.created_at).toLocaleString()}</p>
                        </div>
                        {renderStatusBadge(review.status)}
                      </div>

                      <div className="mt-4 grid gap-4 text-sm text-gray-700 md:grid-cols-4">
                        <div>
                          <p className="text-xs uppercase tracking-wide text-gray-500">Customer</p>
                          <p className="font-medium text-black">{review.contacts?.name || 'Unknown'}</p>
                          <p className="text-gray-500">{review.contacts?.phone_number || 'N/A'}</p>
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-wide text-gray-500">Reference</p>
                          <p className="font-medium text-black">{review.payment_reference || 'Not provided'}</p>
                          <p className="text-gray-500">Amount: {formatCurrency(review.total_amount)}</p>
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-wide text-gray-500">Receipt</p>
                          <p className="font-medium text-black">
                            {review.payment_receipt_uploaded_at
                              ? `Uploaded ${new Date(review.payment_receipt_uploaded_at).toLocaleDateString()}`
                              : 'Not uploaded'}
                          </p>
                          {review.payment_receipt_url && (
                            <a
                              href={review.payment_receipt_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-sm font-medium text-brand"
                            >
                              View file
                            </a>
                          )}
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-wide text-gray-500">AI hints</p>
                          {review.latest_receipt_analysis ? (
                            <ul className="list-disc space-y-1 pl-5 text-xs text-gray-600">
                              {renderAnalysisHints(review.latest_receipt_analysis.analysis).map((hint, idx) => (
                                <li key={idx}>{hint}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-gray-500">Awaiting DINOV3</p>
                          )}
                        </div>
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2">
                        <button
                          onClick={() => setSelectedReview(review)}
                          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-800 hover:border-gray-400"
                        >
                          Inspect & Decide
                        </button>
                        {review.payment_receipt_url && (
                          <a
                            href={review.payment_receipt_url}
                            target="_blank"
                            rel="noreferrer"
                            className="rounded-lg border border-transparent bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-black"
                          >
                            Open Receipt
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-gray-200 p-5">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">All orders</p>
                  <h2 className="text-xl font-semibold text-black">Fulfillment tracker</h2>
                </div>
                <div className="flex flex-wrap gap-2">
                  {STATUS_TABS.map(status => (
                    <button
                      key={status}
                      onClick={() => setFilter(status)}
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        filter === status
                          ? 'bg-black text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {status.replace(/_/g, ' ')}
                    </button>
                  ))}
                </div>
              </div>

              {ordersLoading ? (
                <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-gray-500">
                  Loading orders…
                </div>
              ) : ordersError ? (
                <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{ordersError}</div>
              ) : orders.length === 0 ? (
                <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-gray-500">
                  No orders in this state.
                </div>
              ) : (
                <div className="space-y-4">
                  {orders.map(order => (
                    <div key={order.id} className="rounded-xl border border-gray-200 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-gray-800">
                            {order.order_number ? `Order #${order.order_number}` : `Order ${order.id}`}
                          </p>
                          <p className="text-xs text-gray-500">{new Date(order.created_at).toLocaleString()}</p>
                        </div>
                        {renderStatusBadge(order.status)}
                      </div>

                      <div className="mt-3 grid gap-4 text-sm text-gray-700 md:grid-cols-4">
                        <div>
                          <p className="text-xs uppercase tracking-wide text-gray-500">Customer</p>
                          <p className="font-medium text-black">{order.contacts?.name || 'Unknown'}</p>
                          <p className="text-gray-500">{order.contacts?.phone_number || 'N/A'}</p>
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-wide text-gray-500">Items</p>
                          <p className="font-medium text-black">{renderOrderItems(order.items)}</p>
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-wide text-gray-500">Amount</p>
                          <p className="font-bold text-black">{formatCurrency(order.total_amount)}</p>
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-wide text-gray-500">Fulfillment</p>
                          <p className="font-medium text-black">{order.fulfillment_type || 'Pickup'}</p>
                          {order.delivery_address && (
                            <p className="text-xs text-gray-500">{order.delivery_address}</p>
                          )}
                        </div>
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        {order.status === 'awaiting_confirmation' && (
                          <button
                            onClick={() => {
                              setSelectedReview({
                                ...order,
                                contacts: order.contacts,
                              })
                            }}
                            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
                          >
                            Review Payment
                          </button>
                        )}
                        {order.status === 'paid' && (
                          <button
                            onClick={() => updateOrderStatus(order.id, 'preparing')}
                            className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white hover:bg-purple-700"
                          >
                            Start Preparing
                          </button>
                        )}
                        {order.status === 'preparing' && (
                          <button
                            onClick={() => updateOrderStatus(order.id, 'ready_for_pickup')}
                            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
                          >
                            Mark Ready
                          </button>
                        )}
                        {order.status === 'ready_for_pickup' && (
                          <button
                            onClick={() => updateOrderStatus(order.id, 'completed')}
                            className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-black"
                          >
                            Complete Order
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>

          <aside className="rounded-2xl border border-gray-200 p-5">
            <div className="mb-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">DINOV3 insights</p>
              <h2 className="text-xl font-semibold text-black">Vision signal center</h2>
              <p className="text-sm text-gray-600">Latest receipt + product detections flowing from the DINOV3 service.</p>
            </div>

            {visionError && <p className="mb-2 rounded-lg bg-red-50 p-3 text-sm text-red-600">{visionError}</p>}

            {visionLoading ? (
              <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-gray-500">
                Loading DINOV3 outputs…
              </div>
            ) : visionEntries.length === 0 ? (
              <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-gray-500">
                No recent analyses yet.
              </div>
            ) : (
              <div className="space-y-4">
                {visionEntries.map(entry => (
                  <div key={entry.id} className="rounded-xl border border-gray-100 p-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {entry.analysis_type}
                      </span>
                      <span className="text-xs text-gray-400">{new Date(entry.created_at).toLocaleTimeString()}</span>
                    </div>
                    <p className="mt-1 text-sm font-semibold text-gray-800">
                      {entry.orders?.order_number ? `Order #${entry.orders.order_number}` : 'Unlinked order'}
                    </p>
                    <p className="text-xs text-gray-500">
                      {entry.contacts?.name || 'Customer'} • {entry.contacts?.phone_number || 'N/A'}
                    </p>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-gray-600">
                      {renderAnalysisHints(entry.analysis).map((hint, idx) => (
                        <li key={`${entry.id}-${idx}`}>{hint}</li>
                      ))}
                    </ul>
                    {entry.media_url && (
                      <a
                        href={entry.media_url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-3 inline-flex text-xs font-semibold text-brand"
                      >
                        View media
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </aside>
        </div>
      </div>

      {selectedReview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-6">
          <div className="w-full max-w-3xl rounded-2xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Payment review</p>
                <h3 className="text-2xl font-semibold text-black">
                  {selectedReview.order_number ? `Order #${selectedReview.order_number}` : `Order ${selectedReview.id}`}
                </h3>
                <p className="text-sm text-gray-600">
                  {selectedReview.contacts?.name} • {selectedReview.contacts?.phone_number}
                </p>
              </div>
              <button
                onClick={closeModal}
                className="text-sm font-semibold text-gray-500 hover:text-gray-900"
              >
                Close
              </button>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-gray-200 p-4">
                <p className="text-xs uppercase tracking-wide text-gray-500">Payment details</p>
                <div className="mt-2 space-y-2 text-sm text-gray-700">
                  <p>Amount: <span className="font-semibold text-black">{formatCurrency(selectedReview.total_amount)}</span></p>
                  <p>Reference: <span className="font-semibold text-black">{selectedReview.payment_reference || 'Not provided'}</span></p>
                  <p>Status: {renderStatusBadge(selectedReview.status)}</p>
                  {selectedReview.payment_receipt_url && (
                    <a
                      href={selectedReview.payment_receipt_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex text-sm font-semibold text-brand"
                    >
                      Open receipt file
                    </a>
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-gray-200 p-4">
                <p className="text-xs uppercase tracking-wide text-gray-500">DINOV3 analysis</p>
                {selectedReview.latest_receipt_analysis ? (
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-gray-600">
                    {renderAnalysisHints(selectedReview.latest_receipt_analysis.analysis).map((hint, idx) => (
                      <li key={idx}>{hint}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-gray-500">No AI signal captured yet.</p>
                )}
              </div>
            </div>

            <div className="mt-4">
              <label className="text-xs font-semibold uppercase tracking-wide text-gray-500" htmlFor="decision-notes">
                Notes to customer (required for rejections)
              </label>
              <textarea
                id="decision-notes"
                value={decisionNotes}
                onChange={event => setDecisionNotes(event.target.value)}
                rows={3}
                className="mt-2 w-full rounded-xl border border-gray-300 p-3 text-sm focus:border-black focus:outline-none"
                placeholder="Add context about what you saw in the receipt…"
              />
              {decisionError && <p className="mt-2 text-sm text-red-600">{decisionError}</p>}
            </div>

            <div className="mt-4 flex flex-wrap justify-between gap-2">
              <button
                onClick={() => submitPaymentDecision(false)}
                disabled={submittingDecision || decisionNotes.trim().length === 0}
                className="rounded-xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:border-red-300 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submittingDecision ? 'Submitting…' : 'Reject payment'}
              </button>
              <button
                onClick={() => submitPaymentDecision(true)}
                disabled={submittingDecision}
                className="rounded-xl bg-emerald-600 px-6 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submittingDecision ? 'Approving…' : 'Approve payment'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

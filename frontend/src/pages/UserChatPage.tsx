import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatedAIChat } from '@/components/ui/animated-ai-chat'
import { UserOrdersPanel } from '@/components/ui/user-orders-panel'
import { UserNotificationsPanel } from '@/components/ui/user-notifications-panel'
import { API_URL } from '@/lib/supabase'
import { useAuth } from '@/contexts/AuthContext'
import { motion } from 'framer-motion'
import { ArrowLeft, Store, Package, Bell } from 'lucide-react'

interface ProductPreview {
  sku?: string
  name?: string
  price?: number
  currency?: string
  image_url?: string | null
  available_today?: boolean
}

interface Business {
  business_id: string
  business_name: string
  description?: string | null
  whatsapp_number?: string | null
  inventory_preview?: ProductPreview[]
}

interface Message {
  id: string | number
  direction: "IN" | "OUT"
  content: string
  created_at: string
}

export default function UserChatPage() {
  const [businesses, setBusinesses] = useState<Business[]>([])
  const [selectedBusiness, setSelectedBusiness] = useState<Business | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [userPhone, setUserPhone] = useState<string | null>(null)
  const [showOrders, setShowOrders] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [isBootstrappingPhone, setIsBootstrappingPhone] = useState(true)
  const [phoneError, setPhoneError] = useState<string | null>(null)
  const [businessesError, setBusinessesError] = useState<string | null>(null)
  const navigate = useNavigate()
  const { user } = useAuth()

  const normalizeMessage = useCallback((raw: any): Message => {
    return {
      id: raw?.id ?? raw?.message_id ?? `${raw?.direction || 'OUT'}-${raw?.created_at || Date.now()}`,
      direction: raw?.direction === 'OUT' ? 'OUT' : 'IN',
      content: raw?.content ?? '',
      created_at: raw?.created_at || new Date().toISOString()
    }
  }, [])

  const upsertMessages = useCallback((incoming: Message[] = [], options?: { reset?: boolean }) => {
    setMessages((prev) => {
      const reset = Boolean(options?.reset)
      if (reset && incoming.length === 0) {
        return prev.length ? [] : prev
      }

      const map = reset
        ? new Map<string, Message>()
        : new Map(prev.map((msg) => [String(msg.id), msg]))

      let changed = reset
      for (const message of incoming) {
        if (!message) continue
        const key = String(message.id)
        const existing = map.get(key)
        if (!existing || existing.content !== message.content || existing.direction !== message.direction || existing.created_at !== message.created_at) {
          map.set(key, message)
          changed = true
        }
      }

      if (!changed) {
        return prev
      }

      return Array.from(map.values()).sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      )
    })
  }, [])

  useEffect(() => {
    const storedPhone = localStorage.getItem('user_phone')
    const derivedPhone = storedPhone || user?.phone_number || ''

    if (derivedPhone) {
      setUserPhone(derivedPhone)
      setPhoneError(null)
    } else {
      setUserPhone(null)
      setPhoneError('Please log in as a user to start chatting with a business.')
    }

    setIsBootstrappingPhone(false)
  }, [user])

  useEffect(() => {
    fetchBusinesses()
  }, [])

  const fetchMessages = useCallback(async (options?: { reset?: boolean }) => {
    if (!selectedBusiness || !userPhone) return

    try {
      const res = await fetch(`${API_URL}/api/messages/${userPhone}?business_id=${selectedBusiness.business_id}`)
      const data = await res.json()

      if (!res.ok) {
        throw new Error(data?.detail || 'Failed to fetch messages')
      }

      const normalized = Array.isArray(data) ? data.map(normalizeMessage) : []
      upsertMessages(normalized, { reset: options?.reset })
    } catch (error) {
      console.error('Failed to fetch messages:', error)
      if (options?.reset) {
        upsertMessages([], { reset: true })
      }
    }
  }, [selectedBusiness?.business_id, userPhone, normalizeMessage, upsertMessages])

  useEffect(() => {
    if (!selectedBusiness || !userPhone) {
      return
    }

    upsertMessages([], { reset: true })
    let isCancelled = false
    let timeoutId: ReturnType<typeof setTimeout> | null = null

    const scheduleNext = () => {
      timeoutId = setTimeout(async () => {
        await fetchMessages()
        if (!isCancelled) {
          scheduleNext()
        }
      }, 4000)
    }

    const bootstrap = async () => {
      await fetchMessages({ reset: true })
      if (!isCancelled) {
        scheduleNext()
      }
    }

    bootstrap()

    return () => {
      isCancelled = true
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }
  }, [selectedBusiness, userPhone, fetchMessages, upsertMessages])

  const fetchBusinesses = async () => {
    try {
      const res = await fetch(`${API_URL}/api/public/businesses?limit=12`)
      if (!res.ok) {
        throw new Error('Failed to load businesses')
      }
      const data = await res.json()
      const payload = Array.isArray(data?.businesses)
        ? data.businesses
        : Array.isArray(data)
          ? data
          : []

      if (!payload.length) {
        setBusinesses([])
        return
      }

      const normalized = payload.map((biz: any) => ({
        business_id: biz?.business_id,
        business_name: biz?.business_name || 'Unnamed Business',
        description: biz?.description,
        whatsapp_number: biz?.whatsapp_number,
        inventory_preview: Array.isArray(biz?.inventory_preview) ? biz.inventory_preview : [],
      }))

      const filtered = normalized.filter((biz: Business) => Boolean(biz.business_id))
      setBusinesses(filtered)
      setBusinessesError(filtered.length ? null : 'No businesses are available yet. Please check back soon.')
    } catch (error) {
      console.error('Failed to fetch businesses:', error)
      setBusinesses([])
      setBusinessesError('Unable to load businesses right now. Please retry in a bit.')
    }
  }

  const handleSendMessage = async (message: string) => {
    if (!selectedBusiness || !userPhone) return

    const tempId = `temp-${Date.now()}`
    const optimisticMessage: Message = {
      id: tempId,
      direction: 'IN',
      content: message,
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, optimisticMessage])
    setIsLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/messages/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business_id: selectedBusiness.business_id,
          contact_phone: userPhone,
          channel: 'web',
          body: message,
          attachments: []
        })
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data?.detail || 'Failed to send message')
      }

      setMessages((prev) => prev.filter((msg) => msg.id !== tempId))

      const inbound = data?.message_logs?.inbound ? normalizeMessage(data.message_logs.inbound) : null
      const outbound = data?.message_logs?.outbound ? normalizeMessage(data.message_logs.outbound) : null
      const additions = [inbound, outbound].filter(Boolean) as Message[]

      if (additions.length) {
        upsertMessages(additions)
      } else {
        await fetchMessages()
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      setMessages((prev) => prev.filter((msg) => msg.id !== tempId))
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  if (isBootstrappingPhone) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <p className="text-gray-600">Loading chat...</p>
      </div>
    )
  }

  if (phoneError) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-white p-6 text-center space-y-4">
        <p className="text-lg font-semibold text-black">{phoneError}</p>
        <button
          onClick={() => navigate('/login')}
          className="px-4 py-2 rounded-lg bg-brand text-white font-medium"
        >
          Go to Login
        </button>
      </div>
    )
  }

  if (!userPhone) {
    return null
  }

  if (!selectedBusiness) {
    return (
      <div className="min-h-screen bg-white p-6">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-black mb-2">Choose a Business</h1>
            <p className="text-gray-600">Select a business to start chatting</p>
          </div>

          {businessesError && (
            <div className="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
              {businessesError}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {businesses.map((business, index) => (
              <motion.div
                key={business.business_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                onClick={() => setSelectedBusiness(business)}
                className="border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-all cursor-pointer hover:border-brand group"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-12 h-12 bg-brand/10 rounded-full flex items-center justify-center group-hover:bg-brand/20 transition-colors">
                    <Store className="w-6 h-6 text-brand" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-black">{business.business_name}</h3>
                    <p className="text-sm text-gray-500">Online</p>
                  </div>
                </div>
                <p className="text-sm text-gray-600">
                  Chat with us to place orders, track deliveries, and get support.
                </p>
                {business.inventory_preview?.length ? (
                  <p className="mt-3 text-xs text-gray-500">
                    Popular: {business.inventory_preview.slice(0, 2).map(item => item?.name).filter(Boolean).join(', ')}
                  </p>
                ) : null}
              </motion.div>
            ))}
          </div>

          {!businesses.length && !businessesError && (
            <p className="text-sm text-gray-500">There are no active businesses yet. Once a team sets up on HaloAgent, they will appear here automatically.</p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setSelectedBusiness(null)
              upsertMessages([], { reset: true })
            }}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-600" />
          </button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-brand/10 rounded-full flex items-center justify-center">
              <Store className="w-5 h-5 text-brand" />
            </div>
            <div>
              <h2 className="font-semibold text-black">{selectedBusiness.business_name}</h2>
              <p className="text-xs text-green-600">● Online</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowNotifications(true)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Notifications"
          >
            <Bell className="w-5 h-5 text-gray-600" />
          </button>
          <button
            onClick={() => setShowOrders(true)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="My Orders"
          >
            <Package className="w-5 h-5 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-hidden">
        <AnimatedAIChat
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
        />
      </div>

      {/* Orders Panel */}
      <UserOrdersPanel
        isOpen={showOrders}
        onClose={() => setShowOrders(false)}
        contactPhone={userPhone}
        businessId={selectedBusiness.business_id}
      />

      <UserNotificationsPanel
        isOpen={showNotifications}
        onClose={() => setShowNotifications(false)}
        contactPhone={userPhone}
        businessId={selectedBusiness.business_id}
      />
    </div>
  )
}

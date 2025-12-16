import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, X, Loader2, ArrowRight, RefreshCcw, Check } from "lucide-react";
import { Link } from "react-router-dom";
import { API_URL } from "@/lib/supabase";

interface Notification {
  id: string;
  entity_id: number;
  type: string;
  category: string;
  title: string;
  message: string;
  order_id?: number;
  amount?: number;
  receipt_url?: string;
  created_at: string;
  read: boolean;
}

interface NotificationsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  businessId: string;
}

export function NotificationsPanel({
  isOpen,
  onClose,
  businessId,
}: NotificationsPanelProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [marking, setMarking] = useState(false);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const url = new URL(`${API_URL}/api/notifications`);
      url.searchParams.append("business_id", businessId);
      const res = await fetch(url.toString());
      const data = await res.json();
      setNotifications(Array.isArray(data) ? data : []);
      setLastUpdated(new Date());
    } catch (error) {
      console.error("Failed to fetch notifications", error);
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    if (isOpen) {
      fetchNotifications();
      interval = setInterval(fetchNotifications, 15000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isOpen, fetchNotifications]);

  const markRead = async (items: Notification[]) => {
    const unread = items.filter((item) => !item.read);
    if (!unread.length) return;
    setMarking(true);
    try {
      await fetch(`${API_URL}/api/notifications/read`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          business_id: businessId,
          notifications: unread.map((item) => ({
            notification_type: item.type,
            entity_id: item.entity_id,
          })),
        }),
      });
      setNotifications((prev) =>
        prev.map((notif) =>
          unread.find((item) => item.id === notif.id)
            ? { ...notif, read: true }
            : notif
        )
      );
    } catch (error) {
      console.error("Failed to mark notification read", error);
    } finally {
      setMarking(false);
    }
  };

  const unreadCount = notifications.filter((item) => !item.read).length;

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div
            className="absolute inset-0 bg-black/40"
            onClick={onClose}
            aria-hidden="true"
          />
          <motion.div
            className="relative ml-auto flex h-full w-full max-w-lg flex-col bg-white shadow-2xl"
            initial={{ x: 480 }}
            animate={{ x: 0 }}
            exit={{ x: 480 }}
            transition={{ type: "spring", stiffness: 280, damping: 30 }}
          >
            <div className="flex items-center justify-between border-b border-gray-200 p-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-gray-500">Activity</p>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-semibold text-black">Notifications</h3>
                  {unreadCount > 0 && (
                    <span className="rounded-full bg-brand/10 px-2 py-0.5 text-xs font-semibold text-brand">
                      {unreadCount}
                    </span>
                  )}
                </div>
                {lastUpdated && (
                  <p className="text-xs text-gray-500">
                    Updated {lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => markRead(notifications)}
                  disabled={marking || unreadCount === 0}
                  className="rounded-full border border-gray-200 px-3 py-1 text-xs font-medium text-gray-600 transition-colors hover:border-brand hover:text-brand disabled:cursor-not-allowed disabled:border-gray-100 disabled:text-gray-300"
                >
                  {marking ? "Marking..." : "Mark all"}
                </button>
                <button
                  onClick={fetchNotifications}
                  className="rounded-full p-2 text-gray-500 transition-colors hover:bg-gray-100"
                  aria-label="Refresh notifications"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCcw className="h-4 w-4" />}
                </button>
                <button
                  onClick={onClose}
                  className="rounded-full p-2 text-gray-500 transition-colors hover:bg-gray-100"
                  aria-label="Close notifications"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="h-[calc(100%-88px)] overflow-y-auto p-4">
              {loading ? (
                <div className="flex flex-col items-center justify-center gap-3 py-20 text-gray-500">
                  <Loader2 className="h-6 w-6 animate-spin" />
                  <p>Checking for new activity...</p>
                </div>
              ) : notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center gap-3 py-20 text-center">
                  <Bell className="h-10 w-10 text-gray-300" />
                  <div>
                    <p className="text-base font-semibold text-black">All caught up</p>
                    <p className="text-sm text-gray-500">Payment confirmations will appear here.</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {notifications.map((notification) => (
                    <motion.div
                      key={notification.id}
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={"rounded-2xl border border-gray-100 p-4 shadow-sm"}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium text-black">{notification.title || notification.message}</p>
                            {!notification.read && <span className="h-2 w-2 rounded-full bg-brand" />}
                          </div>
                          <p className="text-xs text-gray-500">{notification.message}</p>
                          {notification.amount && (
                            <p className="text-xs text-gray-500 mt-1">
                              Order #{notification.order_id} · ₦{notification.amount.toLocaleString()}
                            </p>
                          )}
                          <p className="mt-1 text-xs text-gray-400">
                            {new Date(notification.created_at).toLocaleString()}
                          </p>
                        </div>
                        <button
                          onClick={() => markRead([notification])}
                          className="inline-flex items-center gap-1 rounded-full border border-gray-200 px-3 py-1 text-xs font-medium text-gray-600 transition-colors hover:border-brand hover:text-brand"
                          disabled={notification.read}
                        >
                          <Check className="h-3 w-3" />
                          {notification.read ? "Read" : "Mark read"}
                        </button>
                      </div>

                      {notification.receipt_url && (
                        <a
                          href={notification.receipt_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-3 inline-flex text-sm font-medium text-brand hover:text-brand/80"
                        >
                          View receipt
                        </a>
                      )}

                      <div className="mt-4 flex flex-wrap items-center gap-2">
                        {notification.order_id && (
                          <Link
                            to={`/orders?highlight=${notification.order_id}`}
                            className="inline-flex items-center gap-1 rounded-full border border-gray-200 px-3 py-1 text-xs font-medium text-gray-600 transition-colors hover:border-brand hover:text-brand"
                            onClick={onClose}
                          >
                            Review order
                            <ArrowRight className="h-3 w-3" />
                          </Link>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

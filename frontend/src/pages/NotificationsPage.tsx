import { useEffect, useMemo, useState } from "react";
import type { ElementType } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Bell,
  CheckCircle,
  Loader2,
  DollarSign,
  ShoppingBag,
  MessageSquare,
  ArrowRight,
  Check,
} from "lucide-react";
import { API_URL } from "@/lib/supabase";
import { cn } from "@/lib/utils";
import { BackButton } from "@/components/ui/back-button";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "payments", label: "Payments" },
  { key: "orders", label: "Orders" },
  { key: "feedback", label: "Feedback" },
];

const TYPE_META: Record<
  string,
  { icon: ElementType; badge: string; accent: string; description: string; category: string }
> = {
  payment_confirmation: {
    icon: DollarSign,
    badge: "bg-orange-50 text-orange-700",
    accent: "text-orange-600",
    description: "Customer payment awaiting approval",
    category: "payments",
  },
  new_order: {
    icon: ShoppingBag,
    badge: "bg-blue-50 text-blue-700",
    accent: "text-blue-600",
    description: "New order created",
    category: "orders",
  },
  feedback: {
    icon: MessageSquare,
    badge: "bg-purple-50 text-purple-700",
    accent: "text-purple-600",
    description: "Customer left feedback",
    category: "feedback",
  },
};

interface NotificationItem {
  id: string;
  entity_id: number;
  type: string;
  category: string;
  title: string;
  message: string;
  created_at: string;
  order_id?: number;
  amount?: number;
  receipt_url?: string;
  rating?: number;
  read: boolean;
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [businessId] = useState("sweetcrumbs_001");
  const [marking, setMarking] = useState(false);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const authHeaders = (extra: Record<string, string> = {}) => {
    const token = localStorage.getItem("auth_token");
    if (!token) return null;
    return {
      Authorization: `Bearer ${token}`,
      ...extra,
    };
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const headers = authHeaders();
      if (!headers) {
        setError("Please sign in again to load notifications.");
        setNotifications([]);
        return;
      }
      const res = await fetch(`${API_URL}/api/notifications?business_id=${businessId}`, { headers });
      if (!res.ok) {
        throw new Error(`Failed to load notifications (${res.status})`);
      }
      const data = await res.json();
      setNotifications(Array.isArray(data) ? data : []);
      setError(null);
    } catch (error) {
      console.error("Failed to load notifications", error);
      setNotifications([]);
      setError(error instanceof Error ? error.message : "Unable to load notifications right now.");
    } finally {
      setLoading(false);
    }
  };

  const visibleNotifications = useMemo(() => {
    if (filter === "all") return notifications;
    return notifications.filter((item) => item.category === filter);
  }, [notifications, filter]);

  const markAsRead = async (items: NotificationItem[]) => {
    const unread = items.filter((item) => !item.read);
    if (!unread.length) return;
    const headers = authHeaders({ "Content-Type": "application/json" });
    if (!headers) {
      setError("Please sign in again before updating notifications.");
      return;
    }
    setMarking(true);
    try {
      await fetch(`${API_URL}/api/notifications/read`, {
        method: "POST",
        headers,
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
      setError(null);
    } catch (error) {
      console.error("Failed to mark notifications read", error);
      setError("Failed to mark notifications as read.");
    } finally {
      setMarking(false);
    }
  };

  const approvePayment = async (item: NotificationItem) => {
    if (!item.order_id) return;
    const headers = authHeaders({ "Content-Type": "application/json" });
    if (!headers) {
      setError("Please sign in again before approving payments.");
      return;
    }
    setApprovingId(item.id);
    try {
      await fetch(`${API_URL}/api/orders/${item.order_id}/approve-payment`, {
        method: "POST",
        headers,
        body: JSON.stringify({ approved: true }),
      });
      await markAsRead([item]);
      fetchNotifications();
      setError(null);
    } catch (error) {
      console.error("Failed to approve payment", error);
      setError("Failed to approve payment. Please try again.");
    } finally {
      setApprovingId(null);
    }
  };

  const renderEmptyState = () => (
    <div className="text-center py-24">
      <Bell className="w-12 h-12 text-gray-300 mx-auto mb-4" />
      <h3 className="text-lg font-semibold text-black">You're all caught up</h3>
      <p className="text-sm text-gray-500">No notifications in this category right now.</p>
    </div>
  );

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
          <div>
            <BackButton label="Back to overview" className="mb-3 text-sm" />
            <p className="text-sm uppercase tracking-wide text-gray-500">Activity</p>
            <h1 className="text-3xl font-bold text-black">Notifications</h1>
            <p className="text-sm text-gray-500">Stay on top of payments, new orders, and customer feedback.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => markAsRead(notifications)}
              disabled={marking || !notifications.some((item) => !item.read)}
              className={cn(
                "rounded-full border px-4 py-2 text-sm font-medium transition-colors",
                notifications.some((item) => !item.read)
                  ? "border-brand text-brand hover:bg-brand/5"
                  : "border-gray-200 text-gray-400 cursor-not-allowed"
              )}
            >
              {marking ? "Marking..." : "Mark all read"}
            </button>
            <button
              onClick={fetchNotifications}
              className="rounded-full border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:border-brand hover:text-brand"
            >
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="flex flex-wrap gap-2 mb-6">
          {FILTERS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setFilter(tab.key)}
              className={cn(
                "rounded-full px-4 py-2 text-sm font-medium border",
                filter === tab.key
                  ? "border-brand bg-brand/5 text-brand"
                  : "border-gray-200 text-gray-600 hover:text-black"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-24 text-gray-500">
            <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading notifications...
          </div>
        ) : visibleNotifications.length === 0 ? (
          renderEmptyState()
        ) : (
          <div className="space-y-4">
            {visibleNotifications.map((item) => {
              const meta = TYPE_META[item.type] || TYPE_META.new_order;
              const Icon = meta.icon;
              return (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn(
                    "rounded-2xl border border-gray-100 bg-white p-5 shadow-sm",
                    !item.read && "ring-1 ring-brand/40"
                  )}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4">
                      <div className={cn("rounded-full p-3", `${meta.badge}`)}>
                        <Icon className={cn("h-5 w-5", meta.accent)} />
                      </div>
                      <div>
                        <div className="flex items-center gap-3">
                          <p className="text-sm font-medium uppercase tracking-wide text-gray-500">
                            {meta.description}
                          </p>
                          {!item.read && <span className="h-2 w-2 rounded-full bg-brand" />}
                        </div>
                        <h3 className="text-lg font-semibold text-black">{item.title}</h3>
                        <p className="text-sm text-gray-600 mt-1">{item.message}</p>
                        <p className="text-xs text-gray-400 mt-2">
                          {new Date(item.created_at).toLocaleString()}
                        </p>
                        {item.rating && (
                          <p className="text-sm font-semibold text-gray-700 mt-2">
                            Rating: {item.rating}/5
                          </p>
                        )}
                        {item.amount && (
                          <p className="text-sm font-semibold text-gray-700 mt-1">
                            Amount: ₦{item.amount.toLocaleString()}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col gap-2">
                      {!item.read && (
                        <button
                          onClick={() => markAsRead([item])}
                          className="inline-flex items-center gap-1 text-sm font-medium text-gray-600 hover:text-brand"
                        >
                          <Check className="h-4 w-4" />
                          Mark read
                        </button>
                      )}
                      {item.receipt_url && (
                        <a
                          href={item.receipt_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm font-medium text-brand hover:text-brand/80"
                        >
                          View receipt
                        </a>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap items-center gap-3">
                    {item.order_id && (
                      <Link
                        to={`/orders?highlight=${item.order_id}`}
                        className="inline-flex items-center gap-1 rounded-full border border-gray-200 px-3 py-1 text-xs font-medium text-gray-600 transition-colors hover:border-brand hover:text-brand"
                      >
                        Review order
                        <ArrowRight className="h-3 w-3" />
                      </Link>
                    )}
                    {item.type === "payment_confirmation" && (
                      <button
                        onClick={() => approvePayment(item)}
                        disabled={approvingId === item.id}
                        className="inline-flex items-center gap-2 rounded-full bg-green-600 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white hover:bg-green-700"
                      >
                        {approvingId === item.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <CheckCircle className="h-3 w-3" />
                        )}
                        Approve payment
                      </button>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

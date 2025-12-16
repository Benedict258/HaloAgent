import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { API_URL } from "@/lib/supabase";
import { Bell, CheckCircle2, Clock3, Loader2, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ContactNotification {
  id: string;
  order_id: number;
  order_number?: string;
  status: string;
  message: string;
  total_amount?: number;
  fulfillment_type?: string;
  created_at: string;
  type: "order_started" | "order_status" | string;
}

interface UserNotificationsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  contactPhone: string;
  businessId: string;
}

const statusStyles: Record<string, string> = {
  pending_payment: "bg-amber-50 border-amber-100 text-amber-700",
  awaiting_confirmation: "bg-sky-50 border-sky-100 text-sky-700",
  paid: "bg-emerald-50 border-emerald-100 text-emerald-700",
  preparing: "bg-purple-50 border-purple-100 text-purple-700",
  ready_for_pickup: "bg-indigo-50 border-indigo-100 text-indigo-700",
  out_for_delivery: "bg-orange-50 border-orange-100 text-orange-700",
  completed: "bg-gray-50 border-gray-100 text-gray-600",
  cancelled: "bg-rose-50 border-rose-100 text-rose-700",
};

export function UserNotificationsPanel({
  isOpen,
  onClose,
  contactPhone,
  businessId,
}: UserNotificationsPanelProps) {
  const [notifications, setNotifications] = useState<ContactNotification[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchNotifications = useCallback(async () => {
    if (!contactPhone) return;
    setLoading(true);
    try {
      const url = new URL(`${API_URL}/api/contacts/notifications`);
      url.searchParams.append("phone", contactPhone);
      url.searchParams.append("business_id", businessId);
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error("Failed to load notifications");
      const data = await res.json();
      setNotifications(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to fetch notifications", error);
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, [contactPhone, businessId]);

  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen, fetchNotifications]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />
          <motion.div
            className="relative ml-auto flex h-full w-full max-w-md flex-col bg-white shadow-2xl"
            initial={{ x: 400 }}
            animate={{ x: 0 }}
            exit={{ x: 400 }}
            transition={{ type: "spring", stiffness: 260, damping: 30 }}
          >
            <div className="flex items-center justify-between border-b border-gray-200 p-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-gray-500">Updates</p>
                <h3 className="text-lg font-semibold text-black">My notifications</h3>
                <p className="text-xs text-gray-500">Linked phone · {contactPhone}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={fetchNotifications}
                  className="rounded-full border border-gray-200 px-3 py-1 text-xs font-medium text-gray-600 transition-colors hover:border-brand hover:text-brand"
                >
                  {loading ? "Refreshing..." : "Refresh"}
                </button>
                <button
                  onClick={onClose}
                  className="rounded-full p-2 text-gray-500 transition-colors hover:bg-gray-100"
                  aria-label="Close notifications panel"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="h-[calc(100%-96px)] overflow-y-auto p-4 space-y-4">
              {loading ? (
                <div className="flex flex-col items-center justify-center gap-3 py-16 text-gray-500">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <p>Checking for new updates...</p>
                </div>
              ) : notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
                  <Bell className="h-10 w-10 text-gray-300" />
                  <div>
                    <p className="text-base font-semibold text-black">No notifications yet</p>
                    <p className="text-sm text-gray-500">Order updates will appear here in real time.</p>
                  </div>
                </div>
              ) : (
                notifications.map((notification) => {
                  const badgeStyles = statusStyles[notification.status] || "bg-gray-50 border-gray-100 text-gray-600";
                  const isComplete = notification.status === "completed";
                  const amountValue = typeof notification.total_amount === "number" ? notification.total_amount : null;
                  return (
                    <div
                      key={notification.id}
                      className="rounded-2xl border border-gray-100 p-4 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1">
                          <p className="text-xs uppercase tracking-wide text-gray-500">
                            Order #{notification.order_number || notification.order_id}
                          </p>
                          <p className="text-sm font-medium text-black">{notification.message}</p>
                          <p className="text-xs text-gray-400">
                            {new Date(notification.created_at).toLocaleString()}
                          </p>
                        </div>
                        <span
                          className={cn(
                            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium capitalize",
                            badgeStyles
                          )}
                        >
                          {isComplete ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Clock3 className="h-3.5 w-3.5" />}
                          {notification.status.replace(/_/g, " ")}
                        </span>
                      </div>

                      <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-gray-600">
                        {amountValue ? (
                          <span>
                            Total {" "}
                            <strong className="text-black">
                              ₦{amountValue.toLocaleString()}
                            </strong>
                          </span>
                        ) : null}
                        {notification.fulfillment_type ? (
                          <span>
                            Fulfillment: <strong className="text-black">{notification.fulfillment_type}</strong>
                          </span>
                        ) : null}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

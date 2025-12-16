import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Package, Clock, Loader2, AlertCircle } from "lucide-react";
import { API_URL } from "@/lib/supabase";
import { cn } from "@/lib/utils";

interface OrderItem {
  name: string;
  quantity?: number;
}

interface Order {
  id: number;
  status: string;
  total_amount: number;
  created_at: string;
  items?: OrderItem[];
}

interface UserOrdersPanelProps {
  isOpen: boolean;
  onClose: () => void;
  contactPhone: string;
  businessId: string;
}

const statusBadges: Record<string, string> = {
  pending_payment: "bg-yellow-100 text-yellow-800",
  awaiting_confirmation: "bg-blue-100 text-blue-800",
  paid: "bg-green-100 text-green-800",
  preparing: "bg-purple-100 text-purple-800",
  ready_for_pickup: "bg-indigo-100 text-indigo-800",
  completed: "bg-gray-100 text-gray-800",
  cancelled: "bg-red-100 text-red-800",
};

export function UserOrdersPanel({
  isOpen,
  onClose,
  contactPhone,
  businessId,
}: UserOrdersPanelProps) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOrders = useCallback(async () => {
    if (!contactPhone) return;
    setLoading(true);
    setError(null);
    try {
      const url = new URL(`${API_URL}/api/contacts/orders`);
      url.searchParams.append("phone", contactPhone);
      url.searchParams.append("business_id", businessId);

      const res = await fetch(url.toString());
      if (!res.ok) {
        throw new Error("Failed to load orders");
      }
      const data = await res.json();
      setOrders(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to fetch user orders", err);
      setError("Could not load your order history. Please try again.");
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }, [contactPhone, businessId]);

  useEffect(() => {
    if (isOpen) {
      fetchOrders();
    }
  }, [isOpen, fetchOrders]);

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
            className="relative ml-auto h-full w-full max-w-md bg-white shadow-2xl"
            initial={{ x: 400 }}
            animate={{ x: 0 }}
            exit={{ x: 400 }}
            transition={{ type: "spring", stiffness: 260, damping: 30 }}
          >
            <div className="flex items-center justify-between border-b border-gray-200 p-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-gray-500">
                  My Orders
                </p>
                <h3 className="text-lg font-semibold text-black">
                  Order history
                </h3>
              </div>
              <button
                onClick={onClose}
                className="rounded-full p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-black"
                aria-label="Close orders panel"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 text-sm">
              <span className="text-gray-500">Linked phone</span>
              <span className="font-medium text-black">{contactPhone}</span>
            </div>

            <div className="h-[calc(100%-140px)] overflow-y-auto p-4">
              {loading ? (
                <div className="flex flex-col items-center justify-center gap-3 py-16 text-gray-500">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <p>Loading your orders...</p>
                </div>
              ) : error ? (
                <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-red-100 bg-red-50/60 p-4 text-center text-sm text-red-700">
                  <AlertCircle className="h-5 w-5" />
                  <p>{error}</p>
                  <button
                    onClick={fetchOrders}
                    className="text-xs font-medium text-red-700 underline"
                  >
                    Try again
                  </button>
                </div>
              ) : orders.length === 0 ? (
                <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
                  <Package className="h-10 w-10 text-gray-300" />
                  <div>
                    <p className="text-base font-semibold text-black">
                      No orders yet
                    </p>
                    <p className="text-sm text-gray-500">
                      Start a chat to place your first order.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {orders.map((order) => (
                    <div
                      key={order.id}
                      className="rounded-xl border border-gray-100 p-4 shadow-sm"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="text-xs uppercase tracking-wide text-gray-500">
                            Order #{order.id}
                          </p>
                          <p className="text-sm text-gray-400">
                            {new Date(order.created_at).toLocaleDateString()} ·{" "}
                            {new Date(order.created_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </p>
                        </div>
                        <span
                          className={cn(
                            "rounded-full px-2 py-1 text-xs font-medium capitalize",
                            statusBadges[order.status] || "bg-gray-100 text-gray-800"
                          )}
                        >
                          {order.status.replace(/_/g, " ")}
                        </span>
                      </div>

                      <div className="mt-3 space-y-2 text-sm">
                        {Array.isArray(order.items) && order.items.length > 0 ? (
                          <div>
                            <p className="text-gray-500">Items</p>
                            <p className="font-medium text-black">
                              {order.items
                                .map((item) =>
                                  item.quantity && item.quantity > 1
                                    ? `${item.name} ×${item.quantity}`
                                    : item.name
                                )
                                .join(", ")}
                            </p>
                          </div>
                        ) : null}

                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-gray-500">Total</p>
                            <p className="text-lg font-semibold text-black">
                              ₦{order.total_amount.toLocaleString()}
                            </p>
                          </div>
                          <div className="flex items-center gap-2 text-gray-500">
                            <Clock className="h-4 w-4" />
                            <span>
                              {new Date(order.created_at).toLocaleDateString("en-NG", {
                                month: "short",
                                day: "numeric",
                              })}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
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

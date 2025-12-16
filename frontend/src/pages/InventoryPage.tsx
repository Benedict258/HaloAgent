import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { PackagePlus, PackageSearch, RefreshCw, Sparkles, Loader2, AlertTriangle, CheckCircle2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { API_URL } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { BackButton } from "@/components/ui/back-button";

interface InventoryItem {
    sku?: string | null;
    legacy_name_slug?: string | null;
    name: string;
    description?: string | null;
    price: number | string;
    currency?: string | null;
    category?: string | null;
    image_urls?: string[];
    image_url?: string | null;
    available_today?: boolean;
    available?: boolean;
    updated_at?: string | null;
}

interface NormalizedInventoryItem extends InventoryItem {
    clientId: string;
    image_urls: string[];
    available_today: boolean;
}

interface InventoryResponse {
    business_id: string;
    inventory: InventoryItem[];
}

interface InventoryFormState {
    name: string;
    description: string;
    price: string;
    category: string;
    imageUrls: string;
    available_today: boolean;
}

const initialFormState: InventoryFormState = {
    name: "",
    description: "",
    price: "",
    category: "",
    imageUrls: "",
    available_today: true,
};

const NGN_FORMATTER = new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN" });

const formatCurrency = (value: number | string | undefined) => {
    if (typeof value === "number" && Number.isFinite(value)) {
        return NGN_FORMATTER.format(value);
    }
    if (typeof value === "string" && value.trim()) {
        const parsed = Number(value);
        if (Number.isFinite(parsed)) {
            return NGN_FORMATTER.format(parsed);
        }
    }
    return NGN_FORMATTER.format(0);
};

const slugifyId = (value: string | undefined | null, fallback: string) => {
    if (!value) return fallback;
    const slug = value
        .toString()
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
    return (slug || fallback).toUpperCase();
};

const normalizeInventoryItems = (items: InventoryItem[] = []): NormalizedInventoryItem[] => {
    return items.map((item, index) => {
        const fallback = `ITEM-${index + 1}`;
        const clientId = slugifyId(item.sku || item.legacy_name_slug || item.name, fallback);
        const imageUrls = (item.image_urls && item.image_urls.length
            ? item.image_urls
            : item.image_url
                ? [item.image_url]
                : []) as string[];
        const available = typeof item.available_today === "boolean"
            ? item.available_today
            : typeof item.available === "boolean"
                ? item.available
                : true;
        return {
            ...item,
            sku: item.sku || clientId,
            clientId,
            image_urls: imageUrls,
            available_today: available,
        };
    });
};

const authHeaders = (extra: Record<string, string> = {}) => {
    const token = localStorage.getItem("auth_token");
    if (!token) return null;
    return {
        Authorization: `Bearer ${token}`,
        ...extra,
    };
};

export default function InventoryPage() {
    const { user } = useAuth();
    const businessId = user?.business_id || "";
    const [inventory, setInventory] = useState<NormalizedInventoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [updatingSku, setUpdatingSku] = useState<string | null>(null);
    const [editingSku, setEditingSku] = useState<string | null>(null);
    const [formState, setFormState] = useState<InventoryFormState>(initialFormState);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    const availableCount = useMemo(() => inventory.filter((item) => item.available_today).length, [inventory]);
    const mostRecentUpdate = useMemo(() => {
        const timestamps = inventory
            .map((item) => (item.updated_at ? Date.parse(item.updated_at) : NaN))
            .filter((stamp) => Number.isFinite(stamp)) as number[];
        if (!timestamps.length) return null;
        return new Date(Math.max(...timestamps)).toLocaleString();
    }, [inventory]);

    useEffect(() => {
        if (!businessId) {
            setLoading(false);
            return;
        }
        fetchInventory();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [businessId]);

    useEffect(() => {
        if (!success) return;
        const timeout = setTimeout(() => setSuccess(null), 4000);
        return () => clearTimeout(timeout);
    }, [success]);

    const fetchInventory = async () => {
        if (!businessId) return;
        setLoading(true);
        setError(null);
        try {
            const headers = authHeaders();
            if (!headers) {
                setError("Please sign in again to load your products.");
                setInventory([]);
                return;
            }
            const res = await fetch(`${API_URL}/api/businesses/${businessId}/inventory`, { headers });
            if (!res.ok) {
                throw new Error(`Unable to load inventory (${res.status})`);
            }
            const data: InventoryResponse = await res.json();
            const normalized = normalizeInventoryItems(Array.isArray(data.inventory) ? data.inventory : []);
            setInventory(normalized);
        } catch (err) {
            console.error("Failed to fetch inventory", err);
            setInventory([]);
            setError(err instanceof Error ? err.message : "Unable to load inventory right now.");
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setFormState(initialFormState);
        setEditingSku(null);
    };

    const startEditing = (item: NormalizedInventoryItem) => {
        setEditingSku(item.clientId);
        setFormState({
            name: item.name,
            description: item.description || "",
            price: typeof item.price === "number" ? String(item.price) : item.price ?? "",
            category: item.category || "",
            imageUrls: (item.image_urls || []).join("\n"),
            available_today: Boolean(item.available_today),
        });
        window.scrollTo({ top: 0, behavior: "smooth" });
    };

    const handleFormChange = (field: keyof InventoryFormState, value: string | boolean) => {
        setFormState((prev) => ({ ...prev, [field]: value }));
    };

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!businessId) {
            setError("Please finish business setup before managing products.");
            return;
        }
        const priceValue = Number(formState.price);
        if (!Number.isFinite(priceValue) || priceValue < 0) {
            setError("Enter a valid price (numbers only).");
            return;
        }
        if (!formState.name.trim()) {
            setError("Product name is required.");
            return;
        }

        const headers = authHeaders({ "Content-Type": "application/json" });
        if (!headers) {
            setError("Please sign in again to save changes.");
            return;
        }

        setSaving(true);
        setError(null);
        setSuccess(null);

        const imageList = formState.imageUrls
            .split(/\n|,/)
            .map((url) => url.trim())
            .filter(Boolean);

        const payload: Record<string, unknown> = {
            name: formState.name.trim(),
            price: priceValue,
            available_today: formState.available_today,
        };
        if (formState.description.trim()) {
            payload.description = formState.description.trim();
        }
        if (formState.category.trim()) {
            payload.category = formState.category.trim();
        }
        if (imageList.length) {
            payload.image_urls = imageList;
            payload.image_url = imageList[0];
        }

        const endpoint = editingSku
            ? `${API_URL}/api/businesses/${businessId}/inventory/${editingSku}`
            : `${API_URL}/api/businesses/${businessId}/inventory`;
        const method = editingSku ? "PUT" : "POST";

        try {
            const res = await fetch(endpoint, {
                method,
                headers,
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || "Unable to save inventory item.");
            }
            await fetchInventory();
            setSuccess(editingSku ? "Inventory item updated." : "Inventory item added.");
            resetForm();
        } catch (err) {
            console.error("Failed to save inventory", err);
            setError(err instanceof Error ? err.message : "Unable to save inventory item.");
        } finally {
            setSaving(false);
        }
    };

    const handleToggleAvailability = async (item: NormalizedInventoryItem) => {
        if (!businessId) return;
        const headers = authHeaders({ "Content-Type": "application/json" });
        if (!headers) {
            setError("Please sign in again to update availability.");
            return;
        }
        setUpdatingSku(item.clientId);
        setError(null);
        try {
            const res = await fetch(`${API_URL}/api/businesses/${businessId}/inventory/${item.clientId}`, {
                method: "PUT",
                headers,
                body: JSON.stringify({ available_today: !item.available_today }),
            });
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || "Unable to update availability");
            }
            await fetchInventory();
        } catch (err) {
            console.error("Failed to toggle availability", err);
            setError(err instanceof Error ? err.message : "Unable to update availability");
        } finally {
            setUpdatingSku(null);
        }
    };

    return (
        <div className="min-h-screen bg-linear-to-b from-white via-slate-50 to-white">
            <div className="mx-auto max-w-6xl px-4 py-10">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <BackButton label="Back to dashboard" to="/dashboard" />
                    <div className="rounded-full border border-gray-200 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-gray-500">
                        Inventory
                    </div>
                </div>

                <section className="mt-8 overflow-hidden rounded-3xl border border-amber-100 bg-linear-to-r from-amber-50 via-white to-rose-50 p-8 shadow-sm">
                    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                        <div className="space-y-3">
                            <div className="inline-flex items-center gap-2 rounded-full bg-white/80 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-600">
                                <PackageSearch className="h-4 w-4" /> Live catalog
                            </div>
                            <h1 className="text-4xl font-bold text-gray-900">Upload products once, let HaloAgent sell them everywhere.</h1>
                            <p className="text-gray-600">Each entry instantly syncs to WhatsApp replies, order flows, and the Halo web app. Keep your prices fresh, toggle seasonal availability, and attach imagery to boost conversions.</p>
                            {mostRecentUpdate && (
                                <p className="text-sm text-gray-500">Last updated {mostRecentUpdate}</p>
                            )}
                        </div>
                        <div className="rounded-2xl border border-white/50 bg-white/70 p-6 text-center shadow">
                            <p className="text-4xl font-bold text-gray-900">{inventory.length}</p>
                            <p className="text-sm uppercase tracking-widest text-gray-500">Catalog items</p>
                            <div className="mt-4 flex items-center justify-center gap-2 text-sm text-emerald-600">
                                <Sparkles className="h-4 w-4" /> {availableCount} available today
                            </div>
                            <Button variant="outline" className="mt-4 gap-2" onClick={fetchInventory} disabled={loading}>
                                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                                Refresh
                            </Button>
                        </div>
                    </div>
                </section>

                <div className="mt-10 grid gap-8 lg:grid-cols-[1.15fr_0.85fr]">
                    <section className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
                        <div className="mb-6 flex items-center justify-between">
                            <div>
                                <p className="text-sm font-semibold uppercase tracking-[0.3em] text-gray-500">Inventory</p>
                                <h2 className="text-2xl font-bold text-gray-900">Products synced to HaloAgent</h2>
                            </div>
                            {loading && <Loader2 className="h-5 w-5 animate-spin text-gray-500" />}
                        </div>

                        {error && (
                            <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                <div className="flex items-start gap-2">
                                    <AlertTriangle className="mt-0.5 h-4 w-4" />
                                    <span>{error}</span>
                                </div>
                            </div>
                        )}

                        {!loading && inventory.length === 0 && (
                            <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 p-10 text-center">
                                <PackagePlus className="mx-auto h-10 w-10 text-gray-400" />
                                <p className="mt-4 text-lg font-semibold text-gray-800">No products yet</p>
                                <p className="mt-2 text-sm text-gray-600">Add your first item using the form on the right. You can paste image URLs and toggle seasonal availability anytime.</p>
                            </div>
                        )}

                        <div className="space-y-4">
                            {inventory.map((item) => (
                                <article key={item.clientId} className="rounded-2xl border border-gray-100 p-5 shadow-sm">
                                    <div className="flex flex-wrap items-start justify-between gap-4">
                                        <div>
                                            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-gray-400">SKU {item.sku ?? item.clientId}</p>
                                            <h3 className="text-xl font-semibold text-gray-900">{item.name}</h3>
                                            {item.category && <p className="text-sm text-gray-500">{item.category}</p>}
                                        </div>
                                        <div className="flex flex-wrap items-center gap-2">
                                            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${item.available_today ? "bg-emerald-100 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>
                                                {item.available_today ? "Available today" : "Hidden"}
                                            </span>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="text-xs"
                                                onClick={() => handleToggleAvailability(item)}
                                                disabled={updatingSku === item.clientId}
                                            >
                                                {updatingSku === item.clientId ? (
                                                    <span className="flex items-center gap-2 text-gray-500"><Loader2 className="h-3 w-3 animate-spin" />Saving</span>
                                                ) : (
                                                    item.available_today ? "Mark unavailable" : "Mark available"
                                                )}
                                            </Button>
                                            <Button variant="outline" size="sm" onClick={() => startEditing(item)}>
                                                Edit
                                            </Button>
                                        </div>
                                    </div>
                                    <div className="mt-4 grid gap-4 text-sm text-gray-700 md:grid-cols-4">
                                        <div>
                                            <p className="text-xs uppercase text-gray-500">Price</p>
                                            <p className="font-semibold">{formatCurrency(item.price as number)}</p>
                                        </div>
                                        <div>
                                            <p className="text-xs uppercase text-gray-500">Images</p>
                                            <p>{item.image_urls?.length || 0} link(s)</p>
                                        </div>
                                        <div>
                                            <p className="text-xs uppercase text-gray-500">Updated</p>
                                            <p>{item.updated_at ? new Date(item.updated_at).toLocaleString() : "—"}</p>
                                        </div>
                                        <div>
                                            <p className="text-xs uppercase text-gray-500">Status</p>
                                            <p>{item.available_today ? "Live" : "Paused"}</p>
                                        </div>
                                    </div>
                                    {item.description && <p className="mt-4 text-sm text-gray-600">{item.description}</p>}
                                    {item.image_urls && item.image_urls.length > 0 && (
                                        <div className="mt-4 flex flex-wrap gap-2">
                                            {item.image_urls.map((url) => (
                                                <a
                                                    key={url}
                                                    href={url}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="inline-flex items-center gap-2 rounded-full border border-gray-200 px-3 py-1 text-xs text-gray-600 hover:border-brand hover:text-brand"
                                                >
                                                    <span className="truncate max-w-35">{url}</span>
                                                </a>
                                            ))}
                                        </div>
                                    )}
                                </article>
                            ))}
                        </div>
                    </section>

                    <section className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
                        <div className="mb-6">
                            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-gray-500">Add / Update item</p>
                            <h2 className="text-2xl font-bold text-gray-900">{editingSku ? "Edit product" : "Create product"}</h2>
                            <p className="text-sm text-gray-600">All changes sync instantly to Supabase and the AI agent.</p>
                        </div>

                        {success && (
                            <div className="mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                                <div className="flex items-start gap-2">
                                    <CheckCircle2 className="mt-0.5 h-4 w-4" />
                                    <span>{success}</span>
                                </div>
                            </div>
                        )}

                        <form className="space-y-4" onSubmit={handleSubmit}>
                            <div>
                                <label className="text-sm font-medium text-gray-900">Name</label>
                                <input
                                    type="text"
                                    value={formState.name}
                                    onChange={(e) => handleFormChange("name", e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand focus:outline-none"
                                    placeholder="Chocolate drip cake"
                                />
                            </div>

                            <div className="grid gap-4 md:grid-cols-2">
                                <div>
                                    <label className="text-sm font-medium text-gray-900">Price</label>
                                    <input
                                        type="number"
                                        min={0}
                                        step={100}
                                        value={formState.price}
                                        onChange={(e) => handleFormChange("price", e.target.value)}
                                        className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand focus:outline-none"
                                        placeholder="15000"
                                    />
                                </div>
                                <div>
                                    <label className="text-sm font-medium text-gray-900">Category</label>
                                    <input
                                        type="text"
                                        value={formState.category}
                                        onChange={(e) => handleFormChange("category", e.target.value)}
                                        className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand focus:outline-none"
                                        placeholder="Celebration Cakes"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="text-sm font-medium text-gray-900">Description</label>
                                <textarea
                                    value={formState.description}
                                    onChange={(e) => handleFormChange("description", e.target.value)}
                                    rows={4}
                                    className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand focus:outline-none"
                                    placeholder="Rich chocolate sponge layered with ganache."
                                />
                            </div>

                            <div>
                                <label className="text-sm font-medium text-gray-900">Image URLs</label>
                                <textarea
                                    value={formState.imageUrls}
                                    onChange={(e) => handleFormChange("imageUrls", e.target.value)}
                                    rows={3}
                                    className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand focus:outline-none"
                                    placeholder="https://cdn.haloagent.com/cakes/chocolate.jpg"
                                />
                                <p className="mt-1 text-xs text-gray-500">One URL per line. First image appears in chats by default.</p>
                            </div>

                            <label className="inline-flex items-center gap-3 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                                <input
                                    type="checkbox"
                                    checked={formState.available_today}
                                    onChange={(e) => handleFormChange("available_today", e.target.checked)}
                                />
                                Show this product in replies today
                            </label>

                            <div className="flex flex-wrap gap-3">
                                <Button type="submit" disabled={saving} className="gap-2 bg-brand text-white hover:bg-brand-600">
                                    {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <PackagePlus className="h-4 w-4" />}
                                    {editingSku ? "Update product" : "Add product"}
                                </Button>
                                <Button type="button" variant="outline" onClick={resetForm} disabled={saving}>
                                    Clear form
                                </Button>
                            </div>
                        </form>
                    </section>
                </div>
            </div>
        </div>
    );
}

import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { API_URL } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { BackButton } from "@/components/ui/back-button";
import { CheckCircle2, Globe, PhoneCall, Shield, Database, Server, Code } from "lucide-react";

const LANGUAGE_OPTIONS = [
    { value: "en", label: "English" },
    { value: "yo", label: "Yoruba" },
    { value: "ha", label: "Hausa" },
    { value: "ig", label: "Igbo" },
];

type HoursMap = Record<string, { open: string; close: string }>;

const DEFAULT_HOURS: HoursMap = {
    mon: { open: "09:00", close: "18:00" },
    tue: { open: "09:00", close: "18:00" },
    wed: { open: "09:00", close: "18:00" },
    thu: { open: "09:00", close: "18:00" },
    fri: { open: "09:00", close: "18:00" },
    sat: { open: "10:00", close: "16:00" },
    sun: { open: "", close: "" },
};

const cloneDefaultHours = (): HoursMap => JSON.parse(JSON.stringify(DEFAULT_HOURS));

interface BusinessResult {
    business_id: string;
    webhook_url: string;
    verify_token: string;
    sandbox_code?: string;
    supported_languages: string[];
    next_steps: string[];
    message: string;
}

interface MetaIntegration {
    enabled: boolean;
    phone_number_id: string;
    business_account_id: string;
    verify_token: string;
}

interface TwilioIntegration {
    enabled: boolean;
    from_number: string;
    join_code: string;
}

interface WebIntegration {
    enabled: boolean;
    subdomain: string;
    widget_url: string;
}

interface IntegrationsState {
    meta: MetaIntegration;
    twilio: TwilioIntegration;
    web: WebIntegration;
}

const DEFAULT_INTEGRATIONS: IntegrationsState = {
    meta: {
        enabled: false,
        phone_number_id: "",
        business_account_id: "",
        verify_token: "",
    },
    twilio: {
        enabled: false,
        from_number: "",
        join_code: "",
    },
    web: {
        enabled: true,
        subdomain: "",
        widget_url: "",
    },
};

const cloneIntegrations = (): IntegrationsState => JSON.parse(JSON.stringify(DEFAULT_INTEGRATIONS));

const mergeIntegrations = (current: IntegrationsState, saved?: Partial<IntegrationsState> | null): IntegrationsState => {
    if (!saved) return current;
    return {
        meta: { ...current.meta, ...(saved.meta || {}) },
        twilio: { ...current.twilio, ...(saved.twilio || {}) },
        web: { ...current.web, ...(saved.web || {}) },
    };
};

interface SettlementAccountForm {
    bank: string;
    account_name: string;
    account_number: string;
    notes: string;
}

const createBlankSettlementAccount = (): SettlementAccountForm => ({
    bank: "",
    account_name: "",
    account_number: "",
    notes: "",
});

const parseSettlementAccount = (raw: unknown): SettlementAccountForm => {
    const parsed = createBlankSettlementAccount();
    if (!raw) {
        return parsed;
    }
    let source: unknown = raw;
    if (typeof raw === "string") {
        try {
            source = JSON.parse(raw);
        } catch (err) {
            console.warn("Unable to parse settlement account JSON", err);
            return parsed;
        }
    }
    if (source && typeof source === "object") {
        const record = source as Record<string, unknown>;
        parsed.bank = typeof record.bank === "string" ? record.bank : parsed.bank;
        parsed.account_name = typeof record.account_name === "string" ? record.account_name : parsed.account_name;
        parsed.account_number = typeof record.account_number === "string" ? record.account_number : parsed.account_number;
        parsed.notes = typeof record.notes === "string" ? record.notes : parsed.notes;
    }
    return parsed;
};

const buildSettlementAccountPayload = (
    form: SettlementAccountForm
): { payload: SettlementAccountForm | null; error?: string } => {
    const bank = form.bank.trim();
    const accountName = form.account_name.trim();
    const accountNumber = form.account_number.trim();
    const notes = form.notes.trim();

    if (!bank && !accountName && !accountNumber && !notes) {
        return { payload: null };
    }

    if (!bank || !accountName || !accountNumber) {
        return {
            payload: null,
            error: "Please provide bank name, account name, and account number to save payment details.",
        };
    }

    return {
        payload: {
            bank,
            account_name: accountName,
            account_number: accountNumber,
            notes,
        },
    };
};

interface FormState {
    business_name: string;
    description: string;
    whatsapp_number: string;
    default_language: string;
    supported_languages: string[];
    tone: string;
    website: string;
    instagram: string;
    sample_messages: string[];
    business_hours: HoursMap;
    integrations: IntegrationsState;
    pickup_address: string;
    pickup_instructions: string;
    settlement_account: SettlementAccountForm;
}

function SetupPage() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [formState, setFormState] = useState<FormState>({
        business_name: "",
        description: "",
        whatsapp_number: "",
        default_language: "en",
        supported_languages: LANGUAGE_OPTIONS.map((opt) => opt.value),
        tone: "",
        website: "",
        instagram: "",
        sample_messages: ["Tell me what cakes you have", "Can I get delivery today?"],
        business_hours: cloneDefaultHours(),
        integrations: cloneIntegrations(),
        pickup_address: "",
        pickup_instructions: "",
        settlement_account: createBlankSettlementAccount(),
    });
    const [loadingProfile, setLoadingProfile] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<BusinessResult | null>(null);
    const [redirectAfterSave, setRedirectAfterSave] = useState(false);

    const authHeaders = () => {
        const token = localStorage.getItem("auth_token");
        if (!token) return null;
        return { Authorization: `Bearer ${token}` };
    };

    useEffect(() => {
        setFormState((prev) => ({
            ...prev,
            business_name: user?.business_name || prev.business_name,
            whatsapp_number: user?.phone_number || prev.whatsapp_number,
        }));
    }, [user?.business_name, user?.phone_number]);

    useEffect(() => {
        const fetchProfile = async () => {
            if (!user?.business_id) {
                setLoadingProfile(false);
                return;
            }
            try {
                const headers = authHeaders();
                const res = await fetch(`${API_URL}/onboarding/business/${user.business_id}`, { headers: headers || undefined });
                if (!res.ok) throw new Error("Unable to load business profile");
                const data = await res.json();
                setFormState((prev) => ({
                    ...prev,
                    business_name: data.business_name || prev.business_name,
                    description: data.description || prev.description,
                    whatsapp_number: data.whatsapp_number || prev.whatsapp_number,
                    default_language: data.default_language || prev.default_language,
                    supported_languages: Array.isArray(data.supported_languages) && data.supported_languages.length
                        ? data.supported_languages
                        : prev.supported_languages,
                    tone: data.brand_voice || prev.tone,
                    website: data.settings?.website || prev.website,
                    instagram: data.settings?.instagram || prev.instagram,
                    sample_messages: Array.isArray(data.settings?.sample_messages) && data.settings.sample_messages.length
                        ? data.settings.sample_messages
                        : prev.sample_messages,
                    business_hours: data.business_hours || prev.business_hours,
                    integrations: mergeIntegrations(prev.integrations, data.integration_preferences?.channels || null),
                    pickup_address: data.pickup_address || prev.pickup_address,
                    pickup_instructions: data.pickup_instructions || prev.pickup_instructions,
                    settlement_account: parseSettlementAccount(
                        data.settlement_account || data.payment_instructions || prev.settlement_account
                    ),
                }));
            } catch (err) {
                console.error(err);
            } finally {
                setLoadingProfile(false);
            }
        };
        fetchProfile();
    }, [user?.business_id]);

    const handleInputChange = (field: string, value: string) => {
        setFormState((prev) => ({ ...prev, [field]: value }));
    };

    const toggleLanguage = (value: string) => {
        setFormState((prev) => {
            const exists = prev.supported_languages.includes(value);
            const updated = exists
                ? prev.supported_languages.filter((lang) => lang !== value)
                : [...prev.supported_languages, value];
            return { ...prev, supported_languages: updated.length ? updated : [prev.default_language] };
        });
    };

    const updateHour = (day: keyof HoursMap, field: "open" | "close", value: string) => {
        setFormState((prev) => ({
            ...prev,
            business_hours: {
                ...prev.business_hours,
                [day]: {
                    ...prev.business_hours[day],
                    [field]: value,
                },
            },
        }));
    };

    const handleSampleChange = (index: number, value: string) => {
        setFormState((prev) => {
            const updated = [...prev.sample_messages];
            updated[index] = value;
            return { ...prev, sample_messages: updated };
        });
    };

    const addSample = () => {
        setFormState((prev) => ({ ...prev, sample_messages: [...prev.sample_messages, ""] }));
    };

    const handleSettlementChange = (field: keyof SettlementAccountForm, value: string) => {
        setFormState((prev) => ({
            ...prev,
            settlement_account: {
                ...prev.settlement_account,
                [field]: value,
            },
        }));
    };

    const handleFinishSetup = () => {
        setRedirectAfterSave(true);
        const form = document.getElementById("business-setup-form") as HTMLFormElement | null;
        form?.requestSubmit();
    };

    const toggleIntegrationChannel = (channel: keyof IntegrationsState) => {
        setFormState((prev) => ({
            ...prev,
            integrations: {
                ...prev.integrations,
                [channel]: {
                    ...prev.integrations[channel],
                    enabled: !prev.integrations[channel].enabled,
                },
            },
        }));
    };

    const handleIntegrationField = (channel: keyof IntegrationsState, field: string, value: string) => {
        setFormState((prev) => ({
            ...prev,
            integrations: {
                ...prev.integrations,
                [channel]: {
                    ...prev.integrations[channel],
                    [field]: value,
                },
            },
        }));
    };

    const handleSubmit = async (event?: React.FormEvent<HTMLFormElement>) => {
        event?.preventDefault();
        setSaving(true);
        setError(null);
        setResult(null);
        const headers = authHeaders();
        if (!headers) {
            setError("Please sign in again to save your setup.");
            setSaving(false);
            return;
        }
        try {
            const { payload: settlementAccountPayload, error: settlementError } = buildSettlementAccountPayload(formState.settlement_account);
            if (settlementError) {
                setError(settlementError);
                setSaving(false);
                return;
            }

            const payload = {
                ...formState,
                pickup_address: formState.pickup_address.trim() || null,
                pickup_instructions: formState.pickup_instructions.trim() || null,
                settlement_account: settlementAccountPayload,
            };

            const res = await fetch(`${API_URL}/api/businesses`, {
                method: "POST",
                headers: { ...headers, "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || "Unable to save business profile");
            }
            setResult(data);
            if (redirectAfterSave) {
                setRedirectAfterSave(false);
                navigate("/dashboard");
            }
        } catch (err) {
            console.error(err);
            setError(err instanceof Error ? err.message : "Something went wrong while saving.");
            setRedirectAfterSave(false);
        } finally {
            setSaving(false);
        }
    };

    const integrationOptions = useMemo(() => ([
        {
            title: "WhatsApp (Meta)",
            body: "Use your official WhatsApp Business number. Point Meta webhooks to HaloAgent, submit your verified number, and we reply on your own line.",
            icon: PhoneCall,
        },
        {
            title: "Twilio",
            body: "Attach a Twilio WhatsApp number. Paste our webhook URL and business_id in Twilio. Use sandbox join codes for quick tests, or map a production line.",
            icon: Server,
        },
        {
            title: "Halo Web App",
            body: "No external number required. Sign in, upload inventory, and let customers chat via the Halo web experience instantly.",
            icon: Globe,
        },
    ]), []);

    const howItWorks = [
        "One AI, every channel: WhatsApp, SMS, and web loop into the same assistant.",
        "Phone number = contact ID, so every chat stays continuous and personal.",
        "Data-driven responses: HaloAgent reads inventory and profile data before replying.",
    ];

    const developerSteps = [
        "Map incoming To numbers to business_id (WhatsApp/Twilio/web).",
        "Treat From numbers as contact_id, upsert contacts automatically.",
        "Webhook payloads follow Twilio/Meta schemas—dedupe via MessageSid.",
        "Backend owns DB writes; AI tools call intent/order/summary helpers only.",
        "Products live in POST /businesses/{id}/inventory with SKU, name, description, price, image_urls, available_today.",
        "Provide sandbox join codes so testers can link their WhatsApp to your Twilio sandbox.",
        "Respect deletion/opt-in—log consent and allow POST /contacts/delete for removals.",
    ];

    return (
        <div className="min-h-screen bg-white">
            <div className="mx-auto max-w-6xl px-4 py-10">
                <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
                    <BackButton label="Back to dashboard" className="text-sm" />
                    <span className="rounded-full border border-gray-200 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gray-600">
                        Integrations &amp; Setup
                    </span>
                </div>

                <section className="relative overflow-hidden rounded-3xl border border-brand/20 bg-linear-to-br from-white via-brand-50 to-white px-6 py-12">
                    <div className="absolute inset-y-0 right-0 w-1/2 bg-brand/10 blur-3xl" />
                    <div className="relative max-w-3xl space-y-6">
                        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-gray-500">Integration launchpad</p>
                        <h1 className="text-4xl font-bold text-black">
                            Connect HaloAgent to your shop in minutes — on WhatsApp, Twilio or the web.
                        </h1>
                        <p className="text-lg text-gray-700">
                            HaloAgent turns chats into orders, updates, and repeat business. Pick how you want to connect — your official WhatsApp Business number (Meta), a Twilio number, or your Halo web app — then upload your inventory and the AI takes it from there.
                        </p>
                        <div className="flex flex-wrap gap-3">
                            <Button size="lg" className="gap-3 bg-brand text-white hover:bg-brand-600" onClick={() => document.getElementById("business-profile-form")?.scrollIntoView({ behavior: "smooth" })}>
                                Get started — connect your business
                            </Button>
                            <Button size="lg" variant="outline" className="gap-3" onClick={() => document.getElementById("developer-notes")?.scrollIntoView({ behavior: "smooth" })}>
                                See setup docs / Live demo
                            </Button>
                        </div>
                        <p className="text-sm text-gray-500">
                            Use your WhatsApp Business number, Twilio, or simply the Halo web app — same AI, same history, double the reach.
                        </p>
                    </div>
                </section>

                <section className="mt-10 grid gap-6 rounded-3xl border border-gray-100 bg-white p-6 shadow-sm md:grid-cols-3">
                    {howItWorks.map((item, idx) => (
                        <div key={item} className="flex items-start gap-3">
                            <CheckCircle2 className="mt-1 h-5 w-5 text-brand" />
                            <p className="text-sm text-gray-700">
                                <span className="font-semibold text-black">Step {idx + 1}. </span>
                                {item}
                            </p>
                        </div>
                    ))}
                </section>

                <section className="mt-12 grid gap-6 md:grid-cols-3">
                    {integrationOptions.map(({ title, body, icon: Icon }) => (
                        <div key={title} className="rounded-2xl border border-gray-100 bg-white/80 p-5 shadow-sm">
                            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-brand/30 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-brand">
                                <Icon className="h-4 w-4" /> {title}
                            </div>
                            <p className="text-sm text-gray-700">{body}</p>
                        </div>
                    ))}
                </section>

                <section className="mt-12 rounded-3xl border border-gray-100 bg-white p-8 shadow-sm">
                    <div className="mb-6 space-y-2">
                        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-gray-500">Integration validation</p>
                        <h2 className="text-2xl font-bold text-black">Confirm channel credentials</h2>
                        <p className="text-gray-600">Store sandbox or production credentials here so HaloAgent keeps every reply on your trusted numbers.</p>
                    </div>
                    <div className="grid gap-6 md:grid-cols-3">
                        <div className="rounded-2xl border border-gray-100 p-5">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-semibold text-black">WhatsApp (Meta)</p>
                                    <p className="text-xs text-gray-500">Official Business API</p>
                                </div>
                                <label className="flex items-center gap-2 text-xs font-semibold text-gray-600">
                                    <input
                                        type="checkbox"
                                        checked={formState.integrations.meta.enabled}
                                        onChange={() => toggleIntegrationChannel("meta")}
                                    />
                                    Enabled
                                </label>
                            </div>
                            <div className="mt-4 space-y-3 text-sm">
                                <div>
                                    <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Phone number ID</label>
                                    <input
                                        type="text"
                                        value={formState.integrations.meta.phone_number_id}
                                        onChange={(e) => handleIntegrationField("meta", "phone_number_id", e.target.value)}
                                        disabled={!formState.integrations.meta.enabled}
                                        className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand focus:outline-none"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Business account ID</label>
                                    <input
                                        type="text"
                                        value={formState.integrations.meta.business_account_id}
                                        onChange={(e) => handleIntegrationField("meta", "business_account_id", e.target.value)}
                                        disabled={!formState.integrations.meta.enabled}
                                        className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand focus:outline-none"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Verify token</label>
                                    <input
                                        type="text"
                                        value={formState.integrations.meta.verify_token}
                                        onChange={(e) => handleIntegrationField("meta", "verify_token", e.target.value)}
                                        disabled={!formState.integrations.meta.enabled}
                                        className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand focus:outline-none"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="rounded-2xl border border-gray-100 p-5">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-semibold text-black">Twilio</p>
                                    <p className="text-xs text-gray-500">Paste the Twilio sandbox number + join code</p>
                                </div>
                                <label className="flex items-center gap-2 text-xs font-semibold text-gray-600">
                                    <input
                                        type="checkbox"
                                        checked={formState.integrations.twilio.enabled}
                                        onChange={() => toggleIntegrationChannel("twilio")}
                                    />
                                    Enabled
                                </label>
                            </div>
                            <div className="mt-4 space-y-3 text-sm">
                                <div>
                                    <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">From number</label>
                                    <input
                                        type="text"
                                        value={formState.integrations.twilio.from_number}
                                        onChange={(e) => handleIntegrationField("twilio", "from_number", e.target.value)}
                                        disabled={!formState.integrations.twilio.enabled}
                                        className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand focus:outline-none"
                                        placeholder="whatsapp:+1415XXXXXXX"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Sandbox join code</label>
                                    <input
                                        type="text"
                                        value={formState.integrations.twilio.join_code}
                                        onChange={(e) => handleIntegrationField("twilio", "join_code", e.target.value)}
                                        disabled={!formState.integrations.twilio.enabled}
                                        className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand focus:outline-none"
                                        placeholder="JOINHALO1234"
                                    />
                                    <p className="mt-1 text-xs text-gray-500">HaloAgent shares your webhook automatically after you save.</p>
                                </div>
                            </div>
                        </div>

                        <div className="rounded-2xl border border-gray-100 p-5">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-semibold text-black">Halo web chat</p>
                                    <p className="text-xs text-gray-500">Embedded widget</p>
                                </div>
                                <label className="flex items-center gap-2 text-xs font-semibold text-gray-600">
                                    <input
                                        type="checkbox"
                                        checked={formState.integrations.web.enabled}
                                        onChange={() => toggleIntegrationChannel("web")}
                                    />
                                    Enabled
                                </label>
                            </div>
                            <div className="mt-4 space-y-3 text-sm">
                                <div>
                                    <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Subdomain</label>
                                    <input
                                        type="text"
                                        value={formState.integrations.web.subdomain}
                                        onChange={(e) => handleIntegrationField("web", "subdomain", e.target.value)}
                                        disabled={!formState.integrations.web.enabled}
                                        className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand focus:outline-none"
                                        placeholder="shop-name"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Widget URL</label>
                                    <input
                                        type="url"
                                        value={formState.integrations.web.widget_url}
                                        onChange={(e) => handleIntegrationField("web", "widget_url", e.target.value)}
                                        disabled={!formState.integrations.web.enabled}
                                        className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand focus:outline-none"
                                        placeholder="https://chat.haloagent.com/embed/your-shop"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <section id="business-profile-form" className="mt-12 rounded-3xl border border-gray-100 bg-white p-8 shadow-sm">
                    <div className="mb-8 space-y-2">
                        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-gray-500">Business profile form</p>
                        <h2 className="text-2xl font-bold text-black">Tell HaloAgent how your business sounds</h2>
                        <p className="text-gray-600">Fill this once to auto-generate your webhook info, sandbox code, and smart replies.</p>
                    </div>

                    {error && (
                        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
                    )}

                    <form id="business-setup-form" className="space-y-6" onSubmit={(event) => handleSubmit(event)}>
                        <div className="grid gap-6 md:grid-cols-2">
                            <div>
                                <label className="text-sm font-medium text-black">Business name</label>
                                <input
                                    type="text"
                                    value={formState.business_name}
                                    onChange={(e) => handleInputChange("business_name", e.target.value)}
                                    required
                                    className="mt-2 w-full rounded-lg border border-gray-200 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-brand"
                                />
                            </div>
                            <div>
                                <label className="text-sm font-medium text-black">WhatsApp business number</label>
                                <input
                                    type="tel"
                                    value={formState.whatsapp_number}
                                    onChange={(e) => handleInputChange("whatsapp_number", e.target.value)}
                                    required
                                    className="mt-2 w-full rounded-lg border border-gray-200 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-brand"
                                    placeholder="+2348012345678"
                                />
                            </div>
                            <div className="md:col-span-2">
                                <label className="text-sm font-medium text-black">Business description</label>
                                <textarea
                                    value={formState.description}
                                    onChange={(e) => handleInputChange("description", e.target.value)}
                                    rows={3}
                                    className="mt-2 w-full rounded-lg border border-gray-200 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-brand"
                                    placeholder="We bake bespoke celebration cakes, deliver same-day in Lagos, and keep it fun and friendly."
                                />
                            </div>
                        </div>

                        <div className="grid gap-6 md:grid-cols-2">
                            <div>
                                <label className="text-sm font-medium text-black">Default language</label>
                                <select
                                    value={formState.default_language}
                                    onChange={(e) => handleInputChange("default_language", e.target.value)}
                                    className="mt-2 w-full rounded-lg border border-gray-200 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-brand"
                                >
                                    {LANGUAGE_OPTIONS.map((option) => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="text-sm font-medium text-black">Supported languages</label>
                                <div className="mt-3 flex flex-wrap gap-2">
                                    {LANGUAGE_OPTIONS.map((option) => (
                                        <button
                                            type="button"
                                            key={option.value}
                                            onClick={() => toggleLanguage(option.value)}
                                            className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                                                formState.supported_languages.includes(option.value)
                                                    ? "border-brand bg-brand/10 text-brand"
                                                    : "border-gray-200 text-gray-600"
                                            }`}
                                        >
                                            {option.label}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="grid gap-6 md:grid-cols-2">
                            <div>
                                <label className="text-sm font-medium text-black">Brand tone</label>
                                <input
                                    type="text"
                                    value={formState.tone}
                                    onChange={(e) => handleInputChange("tone", e.target.value)}
                                    className="mt-2 w-full rounded-lg border border-gray-200 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-brand"
                                    placeholder="Warm, upbeat, Lagos market energy"
                                />
                            </div>
                            <div className="grid gap-4 md:grid-cols-2">
                                <div>
                                    <label className="text-sm font-medium text-black">Website</label>
                                    <input
                                        type="url"
                                        value={formState.website}
                                        onChange={(e) => handleInputChange("website", e.target.value)}
                                        className="mt-2 w-full rounded-lg border border-gray-200 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-brand"
                                    />
                                </div>
                                <div>
                                    <label className="text-sm font-medium text-black">Instagram</label>
                                    <input
                                        type="text"
                                        value={formState.instagram}
                                        onChange={(e) => handleInputChange("instagram", e.target.value)}
                                        className="mt-2 w-full rounded-lg border border-gray-200 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-brand"
                                        placeholder="@sweetcrumbs"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="grid gap-6 md:grid-cols-2">
                            <div>
                                <label className="text-sm font-medium text-black">Sample messages (AI uses these examples)</label>
                                <div className="mt-2 space-y-3">
                                    {formState.sample_messages.map((sample, index) => (
                                        <input
                                            key={`sample-${index}`}
                                            type="text"
                                            value={sample}
                                            onChange={(e) => handleSampleChange(index, e.target.value)}
                                            className="w-full rounded-lg border border-gray-200 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-brand"
                                        />
                                    ))}
                                    <button type="button" onClick={addSample} className="text-sm font-medium text-brand">
                                        + Add another sample
                                    </button>
                                </div>
                            </div>
                            <div>
                                <label className="text-sm font-medium text-black">Business hours</label>
                                <div className="mt-2 grid gap-2">
                                    {Object.keys(formState.business_hours).map((day) => (
                                        <div key={day} className="flex items-center gap-3 text-sm text-gray-600">
                                            <span className="w-10 uppercase text-gray-500">{day}</span>
                                            <input
                                                type="time"
                                                value={(formState.business_hours as any)[day]?.open || ""}
                                                onChange={(e) => updateHour(day as keyof HoursMap, "open", e.target.value)}
                                                className="flex-1 rounded-lg border border-gray-200 px-2 py-1"
                                            />
                                            <span>to</span>
                                            <input
                                                type="time"
                                                value={(formState.business_hours as any)[day]?.close || ""}
                                                onChange={(e) => updateHour(day as keyof HoursMap, "close", e.target.value)}
                                                className="flex-1 rounded-lg border border-gray-200 px-2 py-1"
                                            />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="grid gap-6 rounded-3xl border border-gray-100 p-6 md:grid-cols-2">
                            <div>
                                <p className="text-sm font-semibold uppercase tracking-[0.3em] text-gray-500">Pickup logistics</p>
                                <h3 className="mt-2 text-lg font-semibold text-black">Share your pickup spot</h3>
                                <label className="mt-4 block text-sm font-medium text-black">Pickup address</label>
                                <textarea
                                    value={formState.pickup_address}
                                    onChange={(e) => handleInputChange("pickup_address", e.target.value)}
                                    rows={3}
                                    className="mt-2 w-full rounded-lg border border-gray-200 px-4 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-brand"
                                    placeholder="12 Adebisi Street, Lekki Phase 1, Lagos"
                                />
                                <label className="mt-4 block text-sm font-medium text-black">Pickup instructions</label>
                                <textarea
                                    value={formState.pickup_instructions}
                                    onChange={(e) => handleInputChange("pickup_instructions", e.target.value)}
                                    rows={3}
                                    className="mt-2 w-full rounded-lg border border-gray-200 px-4 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-brand"
                                    placeholder="Open Tue-Sun, 10am-6pm. Call ahead for rush orders."
                                />
                            </div>
                            <div>
                                <p className="text-sm font-semibold uppercase tracking-[0.3em] text-gray-500">Bank details</p>
                                <h3 className="mt-2 text-lg font-semibold text-black">Tell HaloAgent where money lands</h3>
                                <div className="mt-4 space-y-4">
                                    <div>
                                        <label className="text-sm font-medium text-black">Bank name</label>
                                        <input
                                            type="text"
                                            value={formState.settlement_account.bank}
                                            onChange={(e) => handleSettlementChange("bank", e.target.value)}
                                            className="mt-2 w-full rounded-lg border border-gray-200 px-4 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-brand"
                                            placeholder="GTBank"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-sm font-medium text-black">Account name</label>
                                        <input
                                            type="text"
                                            value={formState.settlement_account.account_name}
                                            onChange={(e) => handleSettlementChange("account_name", e.target.value)}
                                            className="mt-2 w-full rounded-lg border border-gray-200 px-4 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-brand"
                                            placeholder="SweetCrumbs Cakes"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-sm font-medium text-black">Account number</label>
                                        <input
                                            type="text"
                                            value={formState.settlement_account.account_number}
                                            onChange={(e) => handleSettlementChange("account_number", e.target.value)}
                                            className="mt-2 w-full rounded-lg border border-gray-200 px-4 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-brand"
                                            placeholder="0123456789"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-sm font-medium text-black">Payment notes</label>
                                        <textarea
                                            value={formState.settlement_account.notes}
                                            onChange={(e) => handleSettlementChange("notes", e.target.value)}
                                            rows={2}
                                            className="mt-2 w-full rounded-lg border border-gray-200 px-4 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-brand"
                                            placeholder="Send a WhatsApp message once you transfer so we can confirm."
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-4">
                            <Button type="submit" size="lg" disabled={saving} className="bg-brand text-white hover:bg-brand-600">
                                {saving ? "Saving setup..." : "Save & generate webhook info"}
                            </Button>
                            <p className="text-sm text-gray-500">You’ll see your business ID, webhook URL, and sandbox code immediately.</p>
                        </div>
                    </form>

                    {loadingProfile && <p className="mt-6 text-sm text-gray-500">Loading existing profile...</p>}

                    {result && (
                        <div className="mt-8 rounded-2xl border border-green-200 bg-green-50 p-6">
                            <p className="text-base font-semibold text-green-800">{result.message}</p>
                            <div className="mt-4 grid gap-4 md:grid-cols-2">
                                <div>
                                    <p className="text-xs uppercase text-gray-500">Business ID</p>
                                    <p className="text-lg font-semibold text-black">{result.business_id}</p>
                                </div>
                                <div>
                                    <p className="text-xs uppercase text-gray-500">Sandbox join code</p>
                                    <p className="text-lg font-semibold text-black">{result.sandbox_code}</p>
                                </div>
                                <div>
                                    <p className="text-xs uppercase text-gray-500">Webhook URL</p>
                                    <p className="text-sm text-gray-700">{result.webhook_url}</p>
                                </div>
                                <div>
                                    <p className="text-xs uppercase text-gray-500">Verify token</p>
                                    <p className="text-sm text-gray-700">{result.verify_token}</p>
                                </div>
                            </div>
                            <div className="mt-4">
                                <p className="text-xs uppercase text-gray-500">Next steps</p>
                                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-gray-700">
                                    {result.next_steps.map((step) => (
                                        <li key={step}>{step}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    )}
                </section>

                <section className="mt-12 grid gap-6 md:grid-cols-2">
                    <div className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
                        <h3 className="text-xl font-semibold text-black">Product setup</h3>
                        <p className="mt-2 text-sm text-gray-600">Before going live, add categories and sample products so HaloAgent can sell accurately.</p>
                        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-gray-700">
                            <li>Categories: name them clearly (Cakes, Special Orders, Packages).</li>
                            <li>Product fields: name, description, price, image URL, available_today toggle.</li>
                            <li>HaloAgent reads these fields live in chat, sends images, and suggests reorders.</li>
                        </ul>
                    </div>
                    <div className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
                        <h3 className="text-xl font-semibold text-black">What happens next</h3>
                        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-gray-700">
                            <li>AI syncs your inventory + business profile automatically.</li>
                            <li>Customers message WhatsApp or the web chat; everything routes to one inbox.</li>
                            <li>AI executes order flows, sends confirmations, collects feedback, and alerts you.</li>
                        </ul>
                    </div>
                </section>

                <section className="mt-12 rounded-3xl border border-gray-100 bg-white p-8 shadow-sm" id="developer-notes">
                    <div className="mb-6 flex items-center gap-3">
                        <Shield className="h-6 w-6 text-brand" />
                        <h3 className="text-2xl font-bold text-black">Developer mode — exact contracts</h3>
                    </div>
                    <div className="mb-6">
                        <p className="text-sm font-semibold text-black">Implementation checklist</p>
                        <ol className="mt-2 list-decimal space-y-2 pl-5 text-sm text-gray-700">
                            {developerSteps.map((step) => (
                                <li key={step}>{step}</li>
                            ))}
                        </ol>
                    </div>
                    <div className="grid gap-6 md:grid-cols-2">
                        <div className="space-y-4 text-sm text-gray-700">
                            <p className="font-semibold text-black">Webhook payloads</p>
                            <pre className="rounded-xl bg-gray-50 p-4 text-xs text-gray-800">
{`Twilio → POST /webhook/twilio
From: +2348012345678
To: +1415XXXXXXX
Body: I want a chocolate cake
MessageSid: SMxxxx`}
                            </pre>
                            <p>Validate signatures, dedupe via MessageSid, resolve business via To, upsert contacts via From. Route intents (order/status/feedback/help).</p>
                        </div>
                        <div className="space-y-4 text-sm text-gray-700">
                            <p className="font-semibold text-black">Meta Cloud / Web chat</p>
                            <p>Meta webhooks use <code>entry[0].changes[0].value.messages[0]</code>. Web chat posts to <code>/api/messages/send</code> with <code>business_id</code>, <code>contact_id</code>, <code>channel</code>, <code>body</code>.</p>
                            <p>LLM tools: intent_classifier, extract_order_details, generate_reply, summarize_report, trend_research — always JSON for classifiers, single reply rule enforced server-side.</p>
                        </div>
                    </div>
                    <div className="mt-6 grid gap-4 md:grid-cols-2">
                        {[{ title: "Inventory API", body: "POST /businesses/{id}/inventory with SKU, name, description, price, image_urls[], available_today.", Icon: Database }, { title: "Sandbox join codes", body: "Auto-generate codes like JOIN-HALO-123 so testers can link WhatsApp to Twilio sandbox numbers.", Icon: Code }, { title: "Routing", body: "Inbound To → business_id (WhatsApp or Twilio). From becomes contact phone. Store opt-ins + deletions.", Icon: Server }, { title: "Security", body: "Log opt-in timestamps, offer POST /contacts/delete, purge PII after 90 days unless configured otherwise.", Icon: Shield }].map(({ title, body, Icon }) => (
                            <div key={title} className="flex items-start gap-3 rounded-2xl border border-gray-100 bg-gray-50 p-4">
                                <Icon className="mt-1 h-5 w-5 text-brand" />
                                <div>
                                    <p className="font-semibold text-black">{title}</p>
                                    <p className="text-sm text-gray-600">{body}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                    <p className="mt-6 text-sm text-gray-600">Need help? Ping the Halo team — we’ll review your webhook payloads and keep routing healthy.</p>
                </section>

                <section className="mt-12 rounded-3xl border border-brand/20 bg-brand/5 p-8 text-center">
                    <h3 className="text-2xl font-bold text-black">Finish setup &amp; start a live demo</h3>
                    <p className="mt-2 text-gray-700">Run the quick health-check to send a sample WhatsApp reply, preview product cards, and see the dashboard update in real time.</p>
                    <div className="mt-6 flex flex-wrap justify-center gap-3">
                        <Button className="bg-brand text-white hover:bg-brand-600" onClick={handleFinishSetup}>
                            Finish setup now
                        </Button>
                        <Button variant="outline" onClick={() => navigate("/dashboard")}>Jump to Dashboard</Button>
                    </div>
                </section>
            </div>
        </div>
    );
}

export default SetupPage;

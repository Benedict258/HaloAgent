"use client";
import { useState } from "react";
import { useDashboardStats } from "@/hooks/useDashboard";
import { Sidebar, SidebarBody, SidebarLink } from "@/components/ui/sidebar";
import { LayoutDashboard, UserCog, Settings, LogOut, MessageSquare, Bell } from "lucide-react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import {
    BellIcon,
    CalendarIcon,
    FileTextIcon,
    GlobeIcon,
    InputIcon,
} from "@radix-ui/react-icons";
import { BentoCard, BentoGrid } from "@/components/ui/bento-grid";
import { NotificationsPanel } from "@/components/ui/notifications-panel";

export function Dashboard() {
    const links = [
        {
            label: "Dashboard",
            href: "/dashboard",
            icon: (
                <LayoutDashboard className="text-black h-5 w-5 shrink-0" />
            ),
        },
        {
            label: "Orders",
            href: "/orders",
            icon: (
                <FileTextIcon className="text-black h-5 w-5 shrink-0" />
            ),
        },
        {
            label: "Customers",
            href: "/customers",
            icon: (
                <InputIcon className="text-black h-5 w-5 shrink-0" />
            ),
        },
        {
            label: "Revenue",
            href: "/revenue",
            icon: (
                <GlobeIcon className="text-black h-5 w-5 shrink-0" />
            ),
        },
        {
            label: "Chat",
            href: "/chat",
            icon: (
                <MessageSquare className="text-black h-5 w-5 shrink-0" />
            ),
        },
        {
            label: "Notifications",
            href: "/notifications",
            icon: (
                <Bell className="text-black h-5 w-5 shrink-0" />
            ),
        },
        {
            label: "Settings",
            href: "#",
            icon: (
                <Settings className="text-black h-5 w-5 shrink-0" />
            ),
        },
        {
            label: "Logout",
            href: "/",
            icon: (
                <LogOut className="text-black h-5 w-5 shrink-0" />
            ),
        },
    ];
    const [open, setOpen] = useState(false);
    const [notificationsOpen, setNotificationsOpen] = useState(false);
    const businessId = "sweetcrumbs_001";

    return (
        <div
            className={cn(
                "flex flex-col md:flex-row bg-white w-full flex-1 mx-auto overflow-hidden",
                "h-screen"
            )}
        >
            <Sidebar open={open} setOpen={setOpen}>
                <SidebarBody className="justify-between gap-10">
                    <div className="flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
                        {open ? <Logo /> : <LogoIcon />}
                        <div className="mt-8 flex flex-col gap-2">
                            {links.map((link, idx) => (
                                <SidebarLink key={idx} link={link} />
                            ))}
                        </div>
                    </div>
                    <div>
                        <SidebarLink
                            link={{
                                label: "Admin User",
                                href: "#",
                                icon: (
                                    <div className="h-7 w-7 rounded-full bg-gray-300 flex items-center justify-center font-bold text-xs">A</div>
                                ),
                            }}
                        />
                    </div>
                </SidebarBody>
            </Sidebar>
            <DashboardContent onOpenNotifications={() => setNotificationsOpen(true)} />
            <NotificationsPanel
                isOpen={notificationsOpen}
                onClose={() => setNotificationsOpen(false)}
                businessId={businessId}
            />
        </div>
    );
}

export const Logo = () => {
    return (
        <Link
            to="#"
            className="font-normal flex space-x-2 items-center text-sm text-black py-1 relative z-20"
        >
            <div className="h-5 w-6 bg-brand rounded-br-lg rounded-tr-sm rounded-tl-lg rounded-bl-sm shrink-0" />
            <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="font-medium text-black whitespace-pre"
            >
                HaloAgent
            </motion.span>
        </Link>
    );
};

export const LogoIcon = () => {
    return (
        <Link
            to="#"
            className="font-normal flex space-x-2 items-center text-sm text-black py-1 relative z-20"
        >
            <div className="h-5 w-6 bg-brand rounded-br-lg rounded-tr-sm rounded-tl-lg rounded-bl-sm shrink-0" />
        </Link>
    );
};

// Content using Bento Grid
const DashboardContent = ({ onOpenNotifications }: { onOpenNotifications: () => void }) => {
    const { stats, loading, error } = useDashboardStats();
    const totalRevenue = Number(stats.total_revenue ?? 0)

    const features = [
        {
            Icon: FileTextIcon,
            name: "Orders",
            description: loading ? "Loading..." : `${stats.total_orders} total orders, ${stats.pending_orders} pending`,
            href: "/orders",
            cta: "View Orders",
            background: <div className="absolute inset-0 bg-blue-50 opacity-10" />,
            className: "lg:row-start-1 lg:row-end-4 lg:col-start-2 lg:col-end-3",
        },
        {
            Icon: InputIcon,
            name: "Contacts",
            description: loading ? "Loading..." : `${stats.total_contacts} customers`,
            href: "/customers",
            cta: "View Contacts",
            background: <div className="absolute inset-0 bg-green-50 opacity-10" />,
            className: "lg:col-start-1 lg:col-end-2 lg:row-start-1 lg:row-end-3",
        },
        {
            Icon: GlobeIcon,
            name: "Revenue",
            description: loading ? "Loading..." : error ? "Access restricted" : `₦${totalRevenue.toLocaleString()} total`,
            href: "/revenue",
            cta: "View Report",
            background: <div className="absolute inset-0 bg-purple-50 opacity-10" />,
            className: "lg:col-start-1 lg:col-end-2 lg:row-start-3 lg:row-end-4",
        },
        {
            Icon: CalendarIcon,
            name: "Integrations & Setup",
            description: "Connect your business with Halo AI Agent across WhatsApp, Twilio, and the web — one AI, every channel.",
            href: "/setup",
            cta: "Start setup",
            background: <div className="absolute inset-0 bg-orange-50 opacity-10" />,
            className: "lg:col-start-3 lg:col-end-3 lg:row-start-1 lg:row-end-2",
        },
        {
            Icon: BellIcon,
            name: "Notifications",
            description: "Real-time alerts.",
            href: "/notifications",
            cta: "Open",
            background: <div className="absolute inset-0 bg-red-50 opacity-10" />,
            className: "lg:col-start-3 lg:col-end-3 lg:row-start-2 lg:row-end-4",
        },
    ];

    return (
        <div className="flex flex-1 p-4 md:p-8 bg-white overflow-y-auto">
            <div className="w-full max-w-5xl mx-auto">
                <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-3xl font-bold text-black">Overview</h2>
                    <button
                        onClick={onOpenNotifications}
                        className="inline-flex items-center gap-2 rounded-full border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:border-brand hover:text-brand"
                    >
                        <Bell className="h-4 w-4" />
                        Notifications
                    </button>
                </div>
                {error && (
                    <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        {error.includes('403') || error.toLowerCase().includes('failed')
                            ? 'You must be signed in with a business account to view dashboard metrics.'
                            : error}
                    </div>
                )}
                <BentoGrid className="lg:grid-rows-3">
                    {features.map((feature) => (
                        <BentoCard key={feature.name} {...feature} />
                    ))}
                </BentoGrid>
            </div>
        </div>
    );
};

export default Dashboard;

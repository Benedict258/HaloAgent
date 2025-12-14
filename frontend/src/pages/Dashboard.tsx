"use client";
import { useState } from "react";
import { Sidebar, SidebarBody, SidebarLink } from "@/components/ui/sidebar";
import { LayoutDashboard, UserCog, Settings, LogOut } from "lucide-react";
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

export function Dashboard() {
    const links = [
        {
            label: "Dashboard",
            href: "#",
            icon: (
                <LayoutDashboard className="text-black h-5 w-5 flex-shrink-0" />
            ),
        },
        {
            label: "Profile",
            href: "#",
            icon: (
                <UserCog className="text-black h-5 w-5 flex-shrink-0" />
            ),
        },
        {
            label: "Settings",
            href: "#",
            icon: (
                <Settings className="text-black h-5 w-5 flex-shrink-0" />
            ),
        },
        {
            label: "Logout",
            href: "/",
            icon: (
                <LogOut className="text-black h-5 w-5 flex-shrink-0" />
            ),
        },
    ];
    const [open, setOpen] = useState(false);

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
            <DashboardContent />
        </div>
    );
}

export const Logo = () => {
    return (
        <Link
            to="#"
            className="font-normal flex space-x-2 items-center text-sm text-black py-1 relative z-20"
        >
            <div className="h-5 w-6 bg-brand rounded-br-lg rounded-tr-sm rounded-tl-lg rounded-bl-sm flex-shrink-0" />
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
            <div className="h-5 w-6 bg-brand rounded-br-lg rounded-tr-sm rounded-tl-lg rounded-bl-sm flex-shrink-0" />
        </Link>
    );
};

// Content using Bento Grid
const DashboardContent = () => {

    const features = [
        {
            Icon: FileTextIcon,
            name: "Orders",
            description: "View and manage all incoming orders.",
            href: "#",
            cta: "View Orders",
            background: <div className="absolute inset-0 bg-blue-50 opacity-10" />,
            className: "lg:row-start-1 lg:row-end-4 lg:col-start-2 lg:col-end-3",
        },
        {
            Icon: InputIcon,
            name: "Inventory",
            description: "Update products, prices, and stock.",
            href: "#",
            cta: "Manage Inventory",
            background: <div className="absolute inset-0 bg-green-50 opacity-10" />,
            className: "lg:col-start-1 lg:col-end-2 lg:row-start-1 lg:row-end-3",
        },
        {
            Icon: GlobeIcon,
            name: "Analytics",
            description: "See sales trends and customer insights.",
            href: "#",
            cta: "View Report",
            background: <div className="absolute inset-0 bg-purple-50 opacity-10" />,
            className: "lg:col-start-1 lg:col-end-2 lg:row-start-3 lg:row-end-4",
        },
        {
            Icon: CalendarIcon,
            name: "Integrations",
            description: "Connect WhatsApp, Twilio, Meta.",
            href: "#",
            cta: "Configure",
            background: <div className="absolute inset-0 bg-orange-50 opacity-10" />,
            className: "lg:col-start-3 lg:col-end-3 lg:row-start-1 lg:row-end-2",
        },
        {
            Icon: BellIcon,
            name: "Notifications",
            description: "Real-time alerts.",
            href: "#",
            cta: "Check",
            background: <div className="absolute inset-0 bg-red-50 opacity-10" />,
            className: "lg:col-start-3 lg:col-end-3 lg:row-start-2 lg:row-end-4",
        },
    ];

    return (
        <div className="flex flex-1 p-4 md:p-8 bg-white overflow-y-auto">
            <div className="w-full max-w-5xl mx-auto">
                <h2 className="text-3xl font-bold mb-6 text-black">Overview</h2>
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

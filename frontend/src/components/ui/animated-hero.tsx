import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { MoveRight, PhoneCall } from "lucide-react";
import { Button } from "@/components/ui/button";

function Hero() {
    const highlights = useMemo(
        () => ["WhatsApp-first ops", "agentic follow-ups", "human-friendly AI", "data-smart insights", "growth-ready playbooks"],
        []
    );
    const [highlightIndex, setHighlightIndex] = useState(0);

    useEffect(() => {
        const id = setInterval(() => {
            setHighlightIndex((prev) => (prev + 1) % highlights.length);
        }, 2200);
        return () => clearInterval(id);
    }, [highlights.length]);

    return (
        <div className="relative isolate w-full overflow-hidden bg-gradient-to-b from-white via-brand-50/60 to-white">
            <div className="pointer-events-none absolute -top-24 left-1/2 h-96 w-[48rem] -translate-x-1/2 rounded-full bg-brand/15 blur-3xl" />
            <div className="pointer-events-none absolute top-32 right-0 h-64 w-64 translate-x-1/3 rounded-full bg-brand/10 blur-2xl" />
            <div className="container mx-auto px-4">
                <div className="flex gap-8 py-20 lg:py-40 items-center justify-center flex-col">
                    <div>
                        <Button variant="secondary" size="sm" className="gap-4">
                            Why HaloAgent exists <MoveRight className="w-4 h-4" />
                        </Button>
                    </div>
                    <div className="flex gap-6 flex-col items-center">
                        <h1 className="text-4xl md:text-6xl max-w-3xl tracking-tight text-center font-semibold text-black">
                            Sell faster. Delight customers. Repeat more. On WhatsApp and on the Web.
                        </h1>
                        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-gray-500">
                            Built for
                            <div className="relative h-6 w-48 overflow-hidden text-brand-500">
                                <AnimatePresence mode="wait" initial={false}>
                                    <motion.span
                                        key={highlightIndex}
                                        initial={{ y: "100%", opacity: 0 }}
                                        animate={{ y: "0%", opacity: 1 }}
                                        exit={{ y: "-100%", opacity: 0 }}
                                        transition={{ duration: 0.45, ease: "easeOut" }}
                                        className="absolute inset-0 flex items-center justify-center text-xs md:text-sm"
                                    >
                                        {highlights[highlightIndex]}
                                    </motion.span>
                                </AnimatePresence>
                            </div>
                        </div>
                        <p className="text-base md:text-xl leading-relaxed tracking-tight text-gray-600 max-w-3xl text-center">
                            HaloAgent is your pocket-sized CRM and AI assistant built for vendors and MSMEs: take orders, send updates, collect feedback, and grow repeat sales, all from the chat your customers already use.
                        </p>
                        <ul className="grid gap-3 text-sm md:text-base text-gray-700 md:grid-cols-3 w-full max-w-4xl">
                            <li className="rounded-lg border border-brand/20 px-4 py-3 bg-white/80">
                                • Works where your customers are. WhatsApp-first, plus a full web app.
                            </li>
                            <li className="rounded-lg border border-brand/20 px-4 py-3 bg-white/80">
                                • Turn chats into reliable orders, automated updates, and loyalty without extra tech headaches.
                            </li>
                            <li className="rounded-lg border border-brand/20 px-4 py-3 bg-white/80">
                                • Smart suggestions and simple reports that help you sell more and stress less.
                            </li>
                        </ul>
                    </div>
                    <div className="flex flex-col items-center gap-3">
                        <div className="flex flex-col md:flex-row gap-3">
                            <Button size="lg" className="gap-4 bg-brand hover:bg-brand-600 text-white">
                                Get started <MoveRight className="w-4 h-4" />
                            </Button>
                            <Button size="lg" className="gap-4" variant="outline">
                                See Docs <PhoneCall className="w-4 h-4" />
                            </Button>
                        </div>
                        <p className="text-sm text-gray-500 text-center">
                            Works instantly with your WhatsApp number or from our web app. Same agent, same history, double the reach.
                        </p>
                    </div>
                    <p className="text-base md:text-lg text-gray-700 max-w-3xl text-center">
                        HaloAgent helps market vendors, bakers, tailors and small shops act like the big players with fast replies, fewer mistakes, happier customers. No complicated setup, just connect your number, upload your menu, and let the agent do the heavy lifting.
                    </p>
                    <div className="flex flex-col items-center gap-4 w-full">
                        <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">Trusted by local vendors across Nigeria.</p>
                        <div className="flex flex-wrap justify-center gap-2 text-xs uppercase tracking-wide">
                            {["Inventory images", "Order tracking", "One-tap reorder", "Multilingual messages"].map((chip) => (
                                <span key={chip} className="px-3 py-1 rounded-full border border-brand/30 text-brand-700 bg-white/70">
                                    {chip}
                                </span>
                            ))}
                        </div>
                    </div>
                    <div className="w-full rounded-2xl border border-dashed border-gray-300 p-4 bg-white/60 md:hidden">
                        <p className="text-lg font-semibold text-black">
                            Bring your shop to chat for orders, updates, and loyalty on WhatsApp plus web.
                        </p>
                        <p className="text-sm text-gray-600 mt-1">
                            Local-first CRM powered by AI. Built for vendors. Designed to grow repeat sales.
                        </p>
                        <div className="mt-3 flex flex-wrap gap-2 text-sm font-medium text-brand">
                            <span>Try HaloAgent free</span>
                            <span className="text-gray-400">•</span>
                            <span>Watch demo</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export { Hero };

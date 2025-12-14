import { Hero } from "@/components/ui/animated-hero";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

function LandingPage() {
    return (
        <div className="min-h-screen bg-background text-foreground flex flex-col">
            <nav className="p-4 flex justify-between items-center container mx-auto">
                <div className="font-bold text-xl">HaloAgent</div>
                <div className="flex gap-4">
                    <Link to="/dashboard">
                        <Button className="bg-brand hover:bg-brand-600 text-white">Go to Dashboard</Button>
                    </Link>
                </div>
            </nav>
            <Hero />
        </div>
    );
}

export default LandingPage;

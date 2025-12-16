from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.webhooks import router as webhook_router
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.business_setup import router as business_router
from app.api.businesses import router as businesses_router
from app.api.onboarding import router as onboarding_router
from app.api.debug import router as debug_router
from app.api.dashboard import router as dashboard_router
from app.api.orders import router as orders_router
from app.api.contacts import router as contacts_router
from app.api.messages import router as messages_router
from app.api.notifications import router as notifications_router

app = FastAPI(
    title="HaloAgent API",
    description="WhatsApp-first CRM for Nigerian MSMEs",
    version="0.1.0",
    debug=(settings.DEBUG.lower() == "true")
)

# CORS
allowed_origins = settings.CORS_ALLOW_ORIGINS or ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "HaloAgent API",
        "version": "0.1.0",
        "status": "running"
    }

app.include_router(webhook_router, tags=["webhooks"])
app.include_router(admin_router, tags=["admin"])
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(business_router, prefix="/business", tags=["business-setup"])
app.include_router(businesses_router, prefix="/api", tags=["businesses"])
app.include_router(onboarding_router, prefix="/onboarding", tags=["onboarding"])
app.include_router(debug_router, prefix="/debug", tags=["debug"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
app.include_router(orders_router, prefix="/api", tags=["orders"])
app.include_router(contacts_router, prefix="/api", tags=["contacts"])
app.include_router(messages_router, prefix="/api", tags=["messages"])
app.include_router(notifications_router, prefix="/api", tags=["notifications"])

@app.get("/health")
async def health():
    return {"status": "healthy"}

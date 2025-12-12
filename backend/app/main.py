from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.webhooks import router as webhook_router
from app.api.admin import router as admin_router

app = FastAPI(
    title="HaloAgent API",
    description="WhatsApp-first CRM for Nigerian MSMEs",
    version="0.1.0",
    debug=(settings.DEBUG.lower() == "true")
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

@app.get("/health")
async def health():
    return {"status": "healthy"}

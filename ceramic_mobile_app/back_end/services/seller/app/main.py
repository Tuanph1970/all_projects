# Seller Service - Main Application
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import dashboard, analytics, profile

app = FastAPI(
    title="Seller Service",
    description="Seller dashboard, analytics, and profile management service",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dashboard.router, prefix="/api/v1/seller", tags=["seller-dashboard"])
app.include_router(analytics.router, prefix="/api/v1/seller", tags=["seller-analytics"])
app.include_router(profile.router, prefix="/api/v1/seller", tags=["seller-profile"])

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "seller"}

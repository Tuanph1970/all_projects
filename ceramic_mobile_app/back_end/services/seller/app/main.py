# Seller Service - Main Application
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers import dashboard, analytics, profile, order_fulfillment, bulk_operations, categories

app = FastAPI(
    title="Seller Service",
    description="Seller dashboard, analytics, profile management, and order fulfillment service",
    version="1.0.0"
)

# Add validation error handler to see actual errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    print(f"[VALIDATION ERROR] URL: {request.url}")
    print(f"[VALIDATION ERROR] Body: {body}")
    print(f"[VALIDATION ERROR] Errors: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": body.decode() if body else None}
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
app.include_router(order_fulfillment.router, prefix="/api/v1/seller/fulfillment", tags=["order-fulfillment"])
app.include_router(bulk_operations.router, prefix="/api/v1/seller", tags=["bulk-operations"])
app.include_router(categories.router, prefix="/api/v1/seller", tags=["seller-categories"])

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "seller"}

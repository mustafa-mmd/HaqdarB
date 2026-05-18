# app/main.py
"""
HaqDar AI Backend — FastAPI Application Entry Point v2.0
Production-grade configuration with security, logging, and health monitoring.
"""
import logging
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.endpoints import query
from app.core.config import settings

# ── Structured Logging Setup ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("haqdar")

# ── FastAPI Application ──
app = FastAPI(
    title="HaqDar AI",
    version=settings.APP_VERSION,
    description=(
        "Pakistan's most comprehensive AI-powered legal rights platform. "
        "Multilingual legal Q&A, document drafting, case analysis, and legal aid referral."
    ),
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ── CORS Middleware (Production Secure) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://haqdar.pk",
        "https://haqdar-app.web.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Timing & Logging Middleware ──
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000)
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} [{duration_ms}ms]"
    )
    return response


# ── Global Exception Handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "An internal server error occurred. Please try again.",
            "code": "INTERNAL_ERROR",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": f"HTTP_{exc.status_code}",
        },
    )


# ── Routes ──
from app.api.v1.endpoints import query, whatsapp, lawyers, forum, admin, firm

app.include_router(query.router, prefix="/api/v1", tags=["HaqDar Legal API"])
app.include_router(whatsapp.router, prefix="/api/v1/whatsapp", tags=["WhatsApp Bot"])
app.include_router(lawyers.router, prefix="/api/v1/lawyers", tags=["Lawyer Marketplace"])
app.include_router(forum.router, prefix="/api/v1/forum", tags=["Community Forum"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin Control"])
app.include_router(firm.router, prefix="/api/v1/firm", tags=["Firm Management"])


# ── Root ──
@app.get("/", tags=["System"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else "disabled in production",
        "health": "/api/v1/health",
    }
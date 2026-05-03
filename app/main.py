from fastapi import FastAPI,Request
import logging
from logging.config import dictConfig
from app.core.logging_config import LOGGING_CONFIG
from app.routers import rooms_router, booking_routers, user_router, auth
from contextlib import asynccontextmanager
import time
dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)




@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log incoming request
    logger.info(
        "Incoming request",
        extra={
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent")
        }
    )

    response = await call_next(request)
    end_time = time.time()
    process_time = (end_time - start_time) * 1000

    # Log response
    logger.info(
        "Request completed",
        extra={
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "duration_ms": round(process_time, 2)
        }
    )

    return response








@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(user_router.router, prefix="/users", tags=["Users"])
app.include_router(rooms_router.router, prefix="/rooms", tags=["Rooms"])
app.include_router(booking_routers.router, prefix="/bookings", tags=["Bookings"])

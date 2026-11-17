import asyncio
import json
import os
import random
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

from app.api.v1.api import api_router
from app.core.config import settings

FAIL_RATE = float(os.getenv("FAIL_RATE", "0.1"))
if not 0 <= FAIL_RATE <= 1:
    raise ValueError("FAIL_RATE must be between 0 and 1")

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.DEBUG:
        print("\n" + "=" * 50)
        print(f"🚀 Swagger UI: http://localhost:8000{app.docs_url}")
        print("🔗 API Base:   http://localhost:8000/api/v1")
        print("=" * 50 + "\n")
    yield


app = FastAPI(
    title="LogiFlow",
    openapi_url="/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "Accept",
            "X-Requested-With",
        ],
    )

app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    start_time = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        if (
            request.url.path not in {"/metrics", "/health", "/fail"}
            and random.random() < FAIL_RATE
        ):
            response = JSONResponse(
                {"error": "injected failure"},
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            status_code = response.status_code
        return response
    finally:
        duration = time.perf_counter() - start_time
        route = request.scope.get("route")
        endpoint = getattr(route, "path", request.url.path)
        HTTP_REQUESTS.labels(request.method, endpoint, str(status_code)).inc()
        HTTP_REQUEST_DURATION.labels(request.method, endpoint).observe(
            duration
        )
        print(
            json.dumps(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": (
                        "error"
                        if status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
                        else "info"
                    ),
                    "message": "HTTP request",
                    "method": request.method,
                    "route": endpoint,
                    "status": status_code,
                    "duration_ms": round(duration * 1000, 1),
                }
            ),
            flush=True,
        )


@app.get("/metrics")
async def get_metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/fail")
async def fail_sometimes():
    raise HTTPException(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        detail="Intentional failure",
    )


@app.get("/slow")
async def slow_response():
    await asyncio.sleep(1)
    return {"status": "ok"}


@app.get("/version")
async def get_version():
    return {"version": os.getenv("APP_VERSION", "dev")}

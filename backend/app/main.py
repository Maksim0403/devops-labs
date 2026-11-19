import asyncio
import json
import logging
import os
import random
import time
from contextlib import asynccontextmanager
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

REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests",
    ["method", "route", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "Request latency",
    ["route"],
)
FAIL_RATE = float(os.getenv("FAIL_RATE", "0"))
if not 0 <= FAIL_RATE <= 1:
    raise ValueError("FAIL_RATE must be between 0 and 1")
SKIP_PATHS = {"/metrics", "/health"}

access_log = logging.getLogger("access")
if not access_log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    access_log.addHandler(handler)
access_log.setLevel(logging.INFO)
access_log.propagate = False


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
async def observe(request: Request, call_next):
    start = time.perf_counter()
    route_path = "unknown"
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    try:
        response = await call_next(request)
        route = request.scope.get("route")
        route_path = route.path if route else "unknown"
        if (
            request.url.path not in SKIP_PATHS
            and random.random() < FAIL_RATE
        ):
            response = JSONResponse(
                {"error": "injected failure"},
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
        status_code = response.status_code
        return response
    finally:
        if request.url.path not in SKIP_PATHS:
            route = request.scope.get("route")
            route_path = route.path if route else route_path
            duration = time.perf_counter() - start
            REQUESTS.labels(
                request.method, route_path, str(status_code)
            ).inc()
            LATENCY.labels(route_path).observe(duration)
            access_log.info(
                json.dumps(
                    {
                        "level": (
                            "error"
                            if status_code
                            >= HTTPStatus.INTERNAL_SERVER_ERROR
                            else "info"
                        ),
                        "msg": "request",
                        "method": request.method,
                        "route": route_path,
                        "status": int(status_code),
                        "duration_ms": round(duration * 1000, 1),
                        "version": os.getenv("APP_VERSION", "dev"),
                    }
                )
            )


@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/fail")
def fail():
    raise HTTPException(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        detail="intentional",
    )


@app.get("/slow")
async def slow():
    await asyncio.sleep(random.random())
    return {"status": "slow"}


@app.get("/version")
async def get_version():
    return {"version": os.getenv("APP_VERSION", "dev")}

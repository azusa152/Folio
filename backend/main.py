"""
Folio — FastAPI 應用程式進入點。
負責建立 App、註冊路由、管理生命週期。
所有業務邏輯已移至 application/services.py。
"""

import os
import threading
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlmodel import Session
from starlette.middleware.base import BaseHTTPMiddleware

from api.dependencies import require_api_key
from api.rate_limit import limiter
from api.routes.account_routes import router as account_router
from api.routes.analytics_routes import router as analytics_router
from api.routes.backtest_routes import router as backtest_router
from api.routes.crypto_routes import router as crypto_router
from api.routes.dividend_routes import router as dividend_router
from api.routes.forex_routes import router as forex_router
from api.routes.fx_watch_routes import router as fx_watch_router
from api.routes.guru_routes import resonance_router
from api.routes.guru_routes import router as guru_router
from api.routes.holding_routes import router as holding_router
from api.routes.persona_routes import router as persona_router
from api.routes.preferences_routes import router as preferences_router
from api.routes.scan_routes import router as scan_router
from api.routes.snapshot_routes import router as snapshot_router
from api.routes.stock_routes import router as stock_router
from api.routes.stock_split_routes import router as stock_split_router
from api.routes.telegram_routes import router as telegram_router
from api.routes.thesis_routes import router as thesis_router
from api.routes.transaction_routes import router as transaction_router
from api.routes.wrapper_routes import router as wrapper_router
from api.schemas import HealthResponse
from infrastructure.common.config import init_settings
from infrastructure.database import create_db_and_tables
from logging_config import (
    get_logger,
    http_latency_ms_var,
    http_method_var,
    http_path_var,
    http_status_var,
    request_id_var,
)

# Load environment variables from .env file
load_dotenv()
init_settings()

logger = get_logger(__name__)
_access_logger = get_logger("folio.access")

# ---------------------------------------------------------------------------
# Optional Sentry integration — set SENTRY_DSN in .env to enable.
# Install: uv add "sentry-sdk[fastapi]"
# Docs:    docs/adr/ and README 安全性 section
# ---------------------------------------------------------------------------
_SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if _SENTRY_DSN:
    try:
        import sentry_sdk  # type: ignore[import-not-found]
        from sentry_sdk.integrations.fastapi import (  # type: ignore[import-not-found]
            FastApiIntegration,
        )
        from sentry_sdk.integrations.sqlalchemy import (  # type: ignore[import-not-found]
            SqlalchemyIntegration,
        )

        _trace_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05"))
        sentry_sdk.init(
            dsn=_SENTRY_DSN,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=_trace_rate,
            send_default_pii=False,
        )
        logger.info("Sentry enabled (traces_sample_rate=%.2f)", _trace_rate)
    except ImportError:
        logger.warning(
            "SENTRY_DSN is set but sentry-sdk is not installed. "
            "Run `uv add 'sentry-sdk[fastapi]'` inside the backend to enable error tracking."
        )


# ---------------------------------------------------------------------------
# Lifespan: 啟動時建立資料表
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Folio 後端啟動中 — 初始化資料庫...")
    create_db_and_tables()
    logger.info("資料庫初始化完成，服務就緒。")

    # 種入系統預設大師（冪等）
    from application.guru.guru_service import seed_default_gurus
    from application.portfolio.account_service import ensure_default_account
    from application.portfolio.eligibility_service import (
        seed_default_eligible_assets_if_empty,
    )
    from application.portfolio.eligible_sync_service import start_eligible_sync_loop
    from application.portfolio.nav_sync_service import start_nav_sync_loop
    from application.portfolio.settlement_service import (
        reclassify_mutual_fund_holdings,
    )
    from application.stock.stock_service import reclassify_mutual_fund_stocks
    from infrastructure.database import engine

    with Session(engine) as _session:
        seed_default_gurus(_session)
        ensure_default_account(_session)
        seeded = seed_default_eligible_assets_if_empty(_session)
        if seeded:
            logger.info("NISA eligible asset snapshots seeded: %s", seeded)
        reclassified = reclassify_mutual_fund_stocks(_session)
        if reclassified:
            logger.info(
                "Reclassified %d active stocks to Mutual_Fund.",
                reclassified,
            )
        reclassified_h = reclassify_mutual_fund_holdings(_session)
        if reclassified_h:
            logger.info(
                "Reclassified %d holdings to Mutual_Fund.",
                reclassified_h,
            )

    # 背景快取預熱（非阻塞，daemon=True 確保不影響關閉）
    from application.scan.prewarm_service import prewarm_all_caches

    threading.Thread(target=prewarm_all_caches, daemon=True).start()
    logger.info("背景快取預熱已啟動。")
    start_eligible_sync_loop()
    logger.info("NISA eligible-list 週期同步已啟動。")
    start_nav_sync_loop()
    logger.info("投資信託 NAV 週期同步已啟動。")

    yield
    logger.info("Folio 後端關閉中...")


# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Folio API",
    description="Folio — 智能資產配置",
    version="2.0.0",
    lifespan=lifespan,
    # Auth applied per-router, NOT globally (health must be exempt)
)

# Register rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class _RequestIdMiddleware(BaseHTTPMiddleware):
    """Injects per-request context into the logging system.

    Sets request ID, HTTP method, path, response status, and latency into
    context variables so every log line emitted during a request automatically
    carries those fields — especially useful with ``LOG_FORMAT=json``.

    Access log entries are emitted at INFO level on the ``folio.access`` logger,
    providing RED metrics (rate, errors, duration) without requiring DEBUG level.

    On unhandled exceptions the access log still records status 500 and
    latency.  The ``X-Request-ID`` response header cannot be attached
    when Starlette's internal error handler generates the 500 response,
    but the correlation ID is captured in the structured log output.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("X-Request-ID") or str(uuid4())[:8]
        t_rid = request_id_var.set(rid)
        t_method = http_method_var.set(request.method)
        t_path = http_path_var.set(request.url.path)
        t_status = http_status_var.set(0)
        t_latency = http_latency_ms_var.set(0.0)
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            http_status_var.set(response.status_code)
            http_latency_ms_var.set(elapsed_ms)
            _access_logger.info(
                "%s %s %d %.1fms",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
            response.headers["X-Request-ID"] = rid
            return response
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            http_status_var.set(500)
            http_latency_ms_var.set(elapsed_ms)
            _access_logger.info(
                "%s %s 500 %.1fms (unhandled)",
                request.method,
                request.url.path,
                elapsed_ms,
            )
            raise
        finally:
            request_id_var.reset(t_rid)
            http_method_var.reset(t_method)
            http_path_var.reset(t_path)
            http_status_var.reset(t_status)
            http_latency_ms_var.reset(t_latency)


# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGIN", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["X-API-Key", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(_RequestIdMiddleware)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, summary="Health check")
def health_check() -> dict:
    """Health check endpoint - NO auth (Docker healthcheck must access without key)."""
    return {
        "status": "ok",
        "service": "folio-backend",
        "demo_mode": os.getenv("FOLIO_DEMO_MODE", "") == "1",
    }


@app.post(
    "/admin/cache/clear",
    summary="Clear all backend caches (L1 + L2)",
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("10/minute")
def clear_cache(request: Request) -> dict:
    """Admin endpoint - WITH auth and rate limiting."""
    from application.stock.stock_service import clear_market_data_caches

    result = clear_market_data_caches()
    return {"status": "ok", **result}


# ---------------------------------------------------------------------------
# 註冊路由
# ---------------------------------------------------------------------------

# Apply auth to all routers (health endpoint is exempt as it's not in a router)
auth_deps = [Depends(require_api_key)]

app.include_router(analytics_router, dependencies=auth_deps)
app.include_router(account_router, dependencies=auth_deps)
app.include_router(stock_router, dependencies=auth_deps)
app.include_router(stock_split_router, dependencies=auth_deps)
app.include_router(dividend_router, dependencies=auth_deps)
app.include_router(thesis_router, dependencies=auth_deps)
app.include_router(scan_router, dependencies=auth_deps)
app.include_router(backtest_router, dependencies=auth_deps)
app.include_router(crypto_router, dependencies=auth_deps)
app.include_router(persona_router, dependencies=auth_deps)
app.include_router(holding_router, dependencies=auth_deps)
app.include_router(telegram_router, dependencies=auth_deps)
app.include_router(preferences_router, dependencies=auth_deps)
app.include_router(forex_router, dependencies=auth_deps)
app.include_router(fx_watch_router, dependencies=auth_deps)
app.include_router(guru_router, dependencies=auth_deps)
app.include_router(resonance_router, dependencies=auth_deps)
app.include_router(snapshot_router, dependencies=auth_deps)
app.include_router(transaction_router, dependencies=auth_deps)
app.include_router(wrapper_router, dependencies=auth_deps)

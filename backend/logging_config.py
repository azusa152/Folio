"""
Folio — 集中式 Logging 設定
- 每日輪替 (TimedRotatingFileHandler)，保留 3 天自動刪除
- 同時輸出至 console（讓 Docker logs 仍可使用）
- 所有模組透過 get_logger(__name__) 取得 logger
- 設定 LOG_FORMAT=json 環境變數可切換為 JSON 結構化輸出（適用 ELK / Loki / Grafana）
  JSON 欄位包含：timestamp, level, request_id, method, path, status, latency_ms, logger, message
- 設定 LOG_LEVEL 環境變數可調整 log 等級（預設 INFO）
"""

import contextvars
import json
import logging
import os
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = os.getenv("LOG_DIR", "/app/data/logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_LOG_FORMAT_ENV = os.getenv("LOG_FORMAT", "text").lower()

_TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Context variables — populated by RequestIdMiddleware in main.py
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)
http_method_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "http_method", default="-"
)
http_path_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "http_path", default="-"
)
http_status_var: contextvars.ContextVar[int] = contextvars.ContextVar(
    "http_status", default=0
)
http_latency_ms_var: contextvars.ContextVar[float] = contextvars.ContextVar(
    "http_latency_ms", default=0.0
)

# 確保 log 目錄存在
os.makedirs(LOG_DIR, exist_ok=True)

_root_configured = False
_YF_NOISE_MARKERS = (
    "failed to perform, curl:",
    "ssl_error_syscall",
    "possibly delisted; no price data found",
)


class _RequestIdFilter(logging.Filter):
    """Injects per-request context (ID, HTTP fields) into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()  # type: ignore[attr-defined]
        record.http_method = http_method_var.get()  # type: ignore[attr-defined]
        record.http_path = http_path_var.get()  # type: ignore[attr-defined]
        record.http_status = http_status_var.get()  # type: ignore[attr-defined]
        record.http_latency_ms = http_latency_ms_var.get()  # type: ignore[attr-defined]
        return True


class _YfinanceNoiseFilter(logging.Filter):
    """Drop known noisy transient yfinance transport/delisted lines."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not record.name.startswith("yfinance"):
            return True
        message = record.getMessage().lower()
        return not any(marker in message for marker in _YF_NOISE_MARKERS)


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON for structured log aggregation.

    Stable schema (ELK / Loki / Grafana compatible):
        timestamp    – ISO-style datetime string
        level        – log level (INFO, WARNING, ERROR, …)
        request_id   – per-request correlation ID (set by RequestIdMiddleware)
        method       – HTTP method (GET, POST, …) or "-" outside request context
        path         – URL path or "-" outside request context
        status       – HTTP response status code, or null outside request context
        latency_ms   – response latency in milliseconds, or null outside request context
        logger       – Python logger name (module path)
        message      – log message
    """

    def format(self, record: logging.LogRecord) -> str:
        status = getattr(record, "http_status", 0)
        latency = getattr(record, "http_latency_ms", 0.0)
        log_entry: dict = {
            "timestamp": self.formatTime(record, LOG_DATE_FORMAT),
            "level": record.levelname,
            "request_id": getattr(record, "request_id", "-"),
            "method": getattr(record, "http_method", "-"),
            "path": getattr(record, "http_path", "-"),
            "status": status if status else None,
            "latency_ms": round(latency, 1) if latency else None,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_entry["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(log_entry, ensure_ascii=False)


def _make_formatter() -> logging.Formatter:
    if _LOG_FORMAT_ENV == "json":
        return _JsonFormatter()
    return logging.Formatter(_TEXT_FORMAT, datefmt=LOG_DATE_FORMAT)


def _configure_root_logger() -> None:
    """設定 root logger（僅執行一次）。"""
    global _root_configured
    if _root_configured:
        return

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    formatter = _make_formatter()
    req_id_filter = _RequestIdFilter()

    # --- Console Handler ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(formatter)
    # Filter must be on the handler, not the root logger. Filters on a logger
    # only run for records originating from that exact logger; child loggers
    # propagate records directly to handlers, bypassing the parent's filters.
    console_handler.addFilter(req_id_filter)
    root.addHandler(console_handler)

    # --- File Handler：每日輪替，保留 3 天 ---
    log_file = os.path.join(LOG_DIR, "radar.log")
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=3,
        encoding="utf-8",
        utc=True,
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(req_id_filter)
    root.addHandler(file_handler)

    # 降低第三方套件的 log 等級以減少雜訊
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    yfinance_logger = logging.getLogger("yfinance")
    yfinance_logger.setLevel(logging.WARNING)
    yfinance_logger.addFilter(_YfinanceNoiseFilter())
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("curl_cffi").setLevel(logging.WARNING)

    _root_configured = True


def get_logger(name: str) -> logging.Logger:
    """取得指定名稱的 logger，自動確保 root logger 已設定。"""
    _configure_root_logger()
    return logging.getLogger(name)

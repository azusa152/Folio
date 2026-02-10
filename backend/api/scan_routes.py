"""
API — 掃描路由（非同步 fire-and-forget）。
掃描在背景執行緒執行，結果透過 Telegram 通知。
"""

import threading

from fastapi import APIRouter
from sqlmodel import Session

from application.services import run_scan, send_weekly_digest
from infrastructure.database import engine
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _run_scan_background() -> None:
    """在背景執行緒中執行掃描（自建 DB Session）。"""
    try:
        with Session(engine) as session:
            run_scan(session)
    except Exception as e:
        logger.error("背景掃描失敗：%s", e, exc_info=True)


def _run_digest_background() -> None:
    """在背景執行緒中生成每週摘要（自建 DB Session）。"""
    try:
        with Session(engine) as session:
            send_weekly_digest(session)
    except Exception as e:
        logger.error("每週摘要生成失敗：%s", e, exc_info=True)


@router.post("/scan")
def run_scan_route() -> dict:
    """觸發 V2 三層漏斗掃描（非同步），結果透過 Telegram 通知。"""
    thread = threading.Thread(target=_run_scan_background, daemon=True)
    thread.start()
    logger.info("掃描已在背景執行緒啟動。")
    return {"status": "accepted", "message": "掃描已啟動，結果將透過 Telegram 通知。"}


@router.post("/digest")
def run_digest_route() -> dict:
    """觸發每週摘要（非同步），結果透過 Telegram 通知。"""
    thread = threading.Thread(target=_run_digest_background, daemon=True)
    thread.start()
    logger.info("每週摘要已在背景執行緒啟動。")
    return {"status": "accepted", "message": "每週摘要已啟動，結果將透過 Telegram 通知。"}

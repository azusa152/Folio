"""
Infrastructure — 資料庫連線與 Session 管理。
使用 SQLite (透過 SQLModel / SQLAlchemy)。
"""

import os
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from logging_config import get_logger

logger = get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/radar.db")

# SQLite 需要 check_same_thread=False 以支援多執行緒存取
connect_args = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

logger.info("資料庫連線位置：%s", DATABASE_URL)


def create_db_and_tables() -> None:
    """建立所有 SQLModel 定義的資料表（若不存在）。"""
    # 確保所有 Entity 已被 import，SQLModel metadata 才會完整
    import domain.entities  # noqa: F401

    logger.info("建立資料表（若不存在）...")
    SQLModel.metadata.create_all(engine)
    logger.info("資料表就緒。")


def get_session() -> Generator[Session, None, None]:
    """FastAPI Dependency：提供一個 DB Session，結束後自動關閉。"""
    with Session(engine) as session:
        yield session

"""Infrastructure — Settings Repository.

UserPreferences, UserTelegramSettings, UserInvestmentProfile, SystemTemplate.
"""

from __future__ import annotations

from sqlmodel import Session, select

from domain.constants import DEFAULT_USER_ID
from domain.entities import (
    SystemTemplate,
    UserInvestmentProfile,
    UserPreferences,
    UserTelegramSettings,
)

# ===========================================================================
# UserPreferences Repository
# ===========================================================================


def find_user_preferences(
    session: Session, user_id: str = DEFAULT_USER_ID
) -> UserPreferences | None:
    """查詢使用者偏好設定。"""
    return session.get(UserPreferences, user_id)


def save_user_preferences(session: Session, prefs: UserPreferences) -> UserPreferences:
    """新增或更新使用者偏好設定（含 refresh）。"""
    session.add(prefs)
    session.commit()
    session.refresh(prefs)
    return prefs


# ===========================================================================
# UserTelegramSettings Repository
# ===========================================================================


def find_telegram_settings(
    session: Session, user_id: str = DEFAULT_USER_ID
) -> UserTelegramSettings | None:
    """查詢使用者 Telegram 通知設定。"""
    return session.get(UserTelegramSettings, user_id)


def save_telegram_settings(
    session: Session, settings: UserTelegramSettings
) -> UserTelegramSettings:
    """新增或更新 Telegram 通知設定（含 refresh）。"""
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


# ===========================================================================
# UserInvestmentProfile / SystemTemplate Repository
# ===========================================================================


def find_system_templates(session: Session) -> list[SystemTemplate]:
    """查詢所有系統範本。"""
    return list(session.exec(select(SystemTemplate)).all())


def find_active_profile(
    session: Session, user_id: str = DEFAULT_USER_ID
) -> UserInvestmentProfile | None:
    """查詢指定使用者目前啟用中的投資組合設定檔。"""
    stmt = select(UserInvestmentProfile).where(
        UserInvestmentProfile.user_id == user_id,
        UserInvestmentProfile.is_active == True,  # noqa: E712
    )
    return session.exec(stmt).first()


def find_profile_by_id(
    session: Session, profile_id: int
) -> UserInvestmentProfile | None:
    """根據 ID 查詢投資組合設定檔。"""
    return session.get(UserInvestmentProfile, profile_id)


def save_profile(
    session: Session, profile: UserInvestmentProfile
) -> UserInvestmentProfile:
    """新增或更新投資組合設定檔（含 refresh）。"""
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile

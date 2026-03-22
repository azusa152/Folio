"""
API — 投資人格 (Persona) 與投資組合配置 (Profile) 路由。
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from api.error_mapping import to_http_exception
from api.schemas import (
    MessageResponse,
    PersonaTemplateResponse,
    ProfileCreateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from application.errors import ApplicationError
from application.portfolio.insight_service import invalidate_insight_cache
from application.portfolio.rebalance_service import invalidate_rebalance_cache
from application.settings import persona_service
from i18n import get_user_language, t
from infrastructure.database import get_session
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Persona Templates (read-only)
# ---------------------------------------------------------------------------


@router.get(
    "/personas/templates",
    response_model=list[PersonaTemplateResponse],
    summary="List persona templates",
)
def list_persona_templates(
    session: Session = Depends(get_session),
) -> list[PersonaTemplateResponse]:
    """取得所有系統預設投資人格範本。"""
    return [
        PersonaTemplateResponse(**t) for t in persona_service.list_templates(session)
    ]


# ---------------------------------------------------------------------------
# User Investment Profiles (CRUD)
# ---------------------------------------------------------------------------


@router.get(
    "/profiles",
    response_model=ProfileResponse | None,
    summary="Get active investment profile",
)
def get_active_profile(
    session: Session = Depends(get_session),
) -> ProfileResponse | None:
    """取得目前啟用中的投資組合配置。"""
    profile = persona_service.get_active_profile(session)
    if not profile:
        return None
    return ProfileResponse(**profile)


@router.post(
    "/profiles", response_model=ProfileResponse, summary="Create an investment profile"
)
def create_profile(
    payload: ProfileCreateRequest,
    session: Session = Depends(get_session),
) -> ProfileResponse:
    """建立新的投資組合配置（同時停用舊的）。"""
    lang = get_user_language(session)
    return ProfileResponse(
        **persona_service.create_profile(session, payload.model_dump(), lang)
    )


@router.put(
    "/profiles/{profile_id}",
    response_model=ProfileResponse,
    summary="Update an investment profile",
)
def update_profile(
    profile_id: int,
    payload: ProfileUpdateRequest,
    session: Session = Depends(get_session),
) -> ProfileResponse:
    """更新投資組合配置。"""
    lang = get_user_language(session)
    try:
        result = ProfileResponse(
            **persona_service.update_profile(session, profile_id, payload.model_dump())
        )
    except ApplicationError as exc:
        raise to_http_exception(exc, lang=lang) from exc
    invalidate_rebalance_cache()
    invalidate_insight_cache()
    return result


@router.delete(
    "/profiles/{profile_id}",
    response_model=MessageResponse,
    summary="Deactivate an investment profile",
)
def delete_profile(
    profile_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """停用投資組合配置（軟刪除）。"""
    lang = get_user_language(session)
    try:
        result = persona_service.deactivate_profile(session, profile_id)
    except ApplicationError as exc:
        raise to_http_exception(exc, lang=lang) from exc
    invalidate_rebalance_cache()
    invalidate_insight_cache()
    return {"message": t("api.profile_deactivated", lang=lang, name=result["name"])}

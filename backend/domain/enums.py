"""Backward-compatibility shim — re-exports domain.core.enums.

Consumers using ``from domain.enums import X`` continue to work unchanged.
"""

from domain.core.enums import (  # noqa: F401
    CATEGORY_LABEL,
    FEAR_GREED_LABEL,
    FX_ALERT_LABEL,
    TAX_WRAPPER_LABEL,
    TAX_WRAPPER_TREATMENT,
    FearGreedLevel,
    FXAlertType,
    HoldingAction,
    I18nKey,
    IDeCoEmploymentType,
    MarketSentiment,
    MoatStatus,
    RestorationPolicy,
    ScanSignal,
    StockCategory,
    TaxTreatment,
    TaxWrapperType,
    TransactionType,
)

"""Backward-compatibility shim — re-exports domain.core.entities.

Consumers using ``from domain.entities import X`` continue to work unchanged.
"""

from domain.core.entities import (  # noqa: F401
    Account,
    ContributionLedgerEntry,
    DividendEvent,
    DriftAcknowledgment,
    EligibleAsset,
    EligibleAssetSyncState,
    FXWatchConfig,
    Guru,
    GuruFiling,
    GuruHolding,
    Holding,
    MutualFundNav,
    NotificationLog,
    PortfolioSnapshot,
    PriceAlert,
    RemovalLog,
    ScanLog,
    Stock,
    StockSplitEvent,
    SystemTemplate,
    ThesisLog,
    Transaction,
    UserInvestmentProfile,
    UserPreferences,
    UserTelegramSettings,
)

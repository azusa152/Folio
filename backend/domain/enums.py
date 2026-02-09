"""
Domain — 列舉定義。
業務規則中使用的分類與狀態常數。
"""

from enum import Enum


class StockCategory(str, Enum):
    """股票分類：風向球 / 護城河 / 成長夢想"""

    TREND_SETTER = "Trend_Setter"
    MOAT = "Moat"
    GROWTH = "Growth"


class MoatStatus(str, Enum):
    """護城河趨勢狀態"""

    DETERIORATING = "DETERIORATING"
    STABLE = "STABLE"
    NOT_AVAILABLE = "N/A"


class MarketSentiment(str, Enum):
    """市場情緒判定"""

    POSITIVE = "POSITIVE"
    CAUTION = "CAUTION"


class ScanSignal(str, Enum):
    """掃描決策訊號"""

    THESIS_BROKEN = "THESIS_BROKEN"
    CONTRARIAN_BUY = "CONTRARIAN_BUY"
    OVERHEATED = "OVERHEATED"
    NORMAL = "NORMAL"


CATEGORY_LABEL: dict[str, str] = {
    "Trend_Setter": "風向球",
    "Moat": "護城河",
    "Growth": "成長夢想",
}

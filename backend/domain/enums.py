"""
Domain — 列舉定義。
業務規則中使用的分類與狀態常數。
"""

from enum import Enum


class StockCategory(str, Enum):
    """股票分類：風向球 / 護城河 / 成長夢想 / 債券 / 現金"""

    TREND_SETTER = "Trend_Setter"
    MOAT = "Moat"
    GROWTH = "Growth"
    BOND = "Bond"
    CASH = "Cash"


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


class FearGreedLevel(str, Enum):
    """恐懼與貪婪指數等級（VIX + CNN Fear & Greed 綜合）"""

    EXTREME_FEAR = "EXTREME_FEAR"
    FEAR = "FEAR"
    NEUTRAL = "NEUTRAL"
    GREED = "GREED"
    EXTREME_GREED = "EXTREME_GREED"
    NOT_AVAILABLE = "N/A"


FEAR_GREED_LABEL: dict[str, str] = {
    "EXTREME_FEAR": "極度恐懼",
    "FEAR": "恐懼",
    "NEUTRAL": "中性",
    "GREED": "貪婪",
    "EXTREME_GREED": "極度貪婪",
    "N/A": "無資料",
}


CATEGORY_LABEL: dict[str, str] = {
    "Trend_Setter": "風向球",
    "Moat": "護城河",
    "Growth": "成長夢想",
    "Bond": "債券",
    "Cash": "現金",
}

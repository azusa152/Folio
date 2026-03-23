"""
Seed approximate sector weight overrides for Japanese mutual funds.

Sector compositions are derived from index provider / Morningstar data
(approximate, as of 2025). For balanced funds, only the equity-allocation
portion is included; bond / REIT / cash allocations are excluded because they
do not contribute to the GICS sector exposure chart.

Run inside the Docker container:

    docker compose exec backend uv run --frozen --no-dev python -m scripts.seed_fund_sector_weights

For local-only execution (debugging against a local DB):

    FOLIO_ALLOW_LOCAL_DB=1 uv run python -m scripts.seed_fund_sector_weights [--dry-run]
"""

from __future__ import annotations

import argparse

from logging_config import get_logger
from scripts import assert_docker_runtime

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Sector weight data
# ---------------------------------------------------------------------------
# Weights represent the equity-level sector breakdown.
# For pure equity index funds they should sum close to 1.0.
# For balanced funds they sum to the equity portion weight (e.g. ~0.5 for a
# 50/50 equity/bond fund), so the non-equity value is silently excluded from
# the sector exposure chart — which is the correct behaviour.
# ---------------------------------------------------------------------------

_FUND_SECTOR_WEIGHTS: dict[str, dict[str, float]] = {
    # 野村インデックスファンド・JPX日経400
    # Tracks JPX-Nikkei 400 Index (400 large/mid-cap Japanese equities).
    # Source: JPX-Nikkei 400 sector breakdown (approx. as of 2025-Q1).
    "01311143": {
        "Industrials": 0.202,
        "Technology": 0.176,
        "Consumer Cyclical": 0.148,
        "Financial Services": 0.138,
        "Healthcare": 0.088,
        "Consumer Defensive": 0.072,
        "Basic Materials": 0.058,
        "Communication Services": 0.050,
        "Energy": 0.034,
        "Real Estate": 0.022,
        "Utilities": 0.012,
    },
    # 野村インデックスファンド・新興国株式
    # Tracks MSCI Emerging Markets Index.
    # Source: MSCI EM sector weights (approx. as of 2025-Q1).
    "0131310B": {
        "Technology": 0.248,
        "Financial Services": 0.204,
        "Consumer Cyclical": 0.130,
        "Communication Services": 0.092,
        "Consumer Defensive": 0.062,
        "Energy": 0.062,
        "Basic Materials": 0.060,
        "Industrials": 0.058,
        "Healthcare": 0.042,
        "Real Estate": 0.024,
        "Utilities": 0.018,
    },
    # 野村つみたて日本株投信
    # Tracks MSCI Japan Investable Market Index (broad Japan equity).
    # Source: MSCI Japan IMI sector breakdown (approx. as of 2025-Q1).
    "0131217A": {
        "Industrials": 0.210,
        "Consumer Cyclical": 0.168,
        "Technology": 0.152,
        "Financial Services": 0.130,
        "Healthcare": 0.086,
        "Consumer Defensive": 0.078,
        "Communication Services": 0.060,
        "Basic Materials": 0.052,
        "Real Estate": 0.030,
        "Energy": 0.024,
        "Utilities": 0.010,
    },
    # つみたて日本株式(TOPIX)
    # Tracks TOPIX (Tokyo Stock Price Index, ~2,200 listed companies).
    # Source: TSE TOPIX sector breakdown (approx. as of 2025-Q1).
    "03312178": {
        "Industrials": 0.215,
        "Consumer Cyclical": 0.162,
        "Technology": 0.148,
        "Financial Services": 0.138,
        "Healthcare": 0.082,
        "Consumer Defensive": 0.076,
        "Communication Services": 0.058,
        "Basic Materials": 0.056,
        "Real Estate": 0.030,
        "Energy": 0.022,
        "Utilities": 0.013,
    },
    # 野村6資産均等バランス（6-asset equal-weight balanced fund）
    # Asset mix (approx.): Domestic equity 1/6, Foreign equity 1/6,
    #   Domestic bonds 1/6, Foreign bonds 1/6, Domestic REIT 1/6, Foreign REIT 1/6.
    # Equity portion ≈ 33.3% of fund value. Sector weights below are expressed
    # relative to the FULL fund NAV (i.e. equity weight × sector share within equity).
    # Combined domestic + foreign equity sector breakdown.
    "01312179": {
        "Industrials": 0.055,
        "Technology": 0.054,
        "Financial Services": 0.046,
        "Consumer Cyclical": 0.044,
        "Healthcare": 0.028,
        "Consumer Defensive": 0.024,
        "Communication Services": 0.022,
        "Basic Materials": 0.016,
        "Energy": 0.014,
        "Real Estate": 0.012,
        "Utilities": 0.008,
        # Bonds, REITs excluded — not tracked in sector exposure
    },
    # 野村インデックスファンド・内外7資産バランス・為替ヘッジ型
    # Asset mix (approx.): 7 assets each ~14.3%.
    # Equity: Domestic equity ~14.3%, Foreign equity (developed) ~14.3% ≈ 28.6% total.
    # Sector weights relative to full fund NAV.
    "01313139": {
        "Industrials": 0.044,
        "Technology": 0.042,
        "Financial Services": 0.036,
        "Consumer Cyclical": 0.034,
        "Healthcare": 0.022,
        "Consumer Defensive": 0.019,
        "Communication Services": 0.018,
        "Basic Materials": 0.013,
        "Energy": 0.011,
        "Real Estate": 0.009,
        "Utilities": 0.006,
        # Bonds, REITs, domestic REIT excluded
    },
}


def run(*, dry_run: bool = False) -> dict[str, int]:
    from sqlmodel import Session

    from infrastructure.database import create_db_and_tables, engine
    from infrastructure.repositories import upsert_sector_weights

    create_db_and_tables()
    stats: dict[str, int] = {"seeded": 0, "skipped": 0}

    with Session(engine) as session:
        for fund_code, weights in _FUND_SECTOR_WEIGHTS.items():
            if dry_run:
                total = round(sum(weights.values()), 4)
                logger.info(
                    "[DRY RUN] %s — %d sectors, total weight=%.4f",
                    fund_code,
                    len(weights),
                    total,
                )
                stats["seeded"] += 1
            else:
                upsert_sector_weights(session, fund_code, weights, source="seed")
                logger.info(
                    "Seeded sector weights for %s (%d sectors).",
                    fund_code,
                    len(weights),
                )
                stats["seeded"] += 1

    return stats


def main(args: list[str] | None = None) -> int:
    assert_docker_runtime()
    global logger
    from logging_config import get_logger as _get_logger

    logger = _get_logger(__name__)

    parser = argparse.ArgumentParser(
        description="Seed sector weight overrides for Japanese mutual funds."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview seeding without writing to the database.",
    )
    parsed = parser.parse_args(args)

    stats = run(dry_run=parsed.dry_run)
    action = "DRY RUN preview" if parsed.dry_run else "Seeding"
    logger.info("%s complete: %s", action, stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

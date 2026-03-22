"""Domain — Tax Wrapper constants (NISA, iDeCo, tax rates)."""

# ---------------------------------------------------------------------------
# Tax Wrapper — NISA Limits (New NISA, effective 2024-01-01)
# ---------------------------------------------------------------------------
NISA_RESTORATION_POLICY = "next_year"  # Change to "same_day" when 2026 reform activates

NISA_LIMITS = {
    "nisa_tsumitate": {
        "annual": 1_200_000,
    },
    "nisa_growth": {
        "annual": 2_400_000,
        "lifetime_sub_limit": 12_000_000,
    },
    "combined_annual": 3_600_000,
    "combined_lifetime": 18_000_000,
}

# ---------------------------------------------------------------------------
# Tax Wrapper — iDeCo Limits (as of Dec 2024 reform)
# ---------------------------------------------------------------------------
IDECO_LIMITS = {
    "self_employed": {"monthly": 68_000, "annual": 816_000},
    "employee_no_pension": {"monthly": 23_000, "annual": 276_000},
    "employee_dc_only": {"monthly": 20_000, "annual": 240_000},
    "employee_with_db": {"monthly": 20_000, "annual": 240_000},
    "public_servant": {"monthly": 20_000, "annual": 240_000},
    "homemaker": {"monthly": 23_000, "annual": 276_000},
}

# ---------------------------------------------------------------------------
# Tax Wrapper — Tax Rates
# ---------------------------------------------------------------------------
TOKUTEI_TAX_RATE = 0.20315  # 所得税 15.315% + 住民税 5%

# ---------------------------------------------------------------------------
# Tax Wrapper — Wrapper Type Options (for frontend selector)
# ---------------------------------------------------------------------------
TAX_WRAPPER_OPTIONS = [
    "tokutei",
    "nisa_tsumitate",
    "nisa_growth",
    "ideco",
    "ippan",
]

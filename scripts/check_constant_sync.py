"""
Compare key constants between backend and frontend.
Exit 1 if any drift is detected.

Constant groups verified:
  - Stock categories:  STOCK_CATEGORIES  ↔  STOCK_CATEGORIES
  - Radar categories:  RADAR_CATEGORIES  ↔  RADAR_CATEGORIES
  - Category icons:    CATEGORY_ICON  ↔  CATEGORY_ICON_SHORT
  - Supported currencies and dropdowns:
      SUPPORTED_CURRENCIES ↔ FX_CURRENCY_OPTIONS/CASH_CURRENCY_OPTIONS/DISPLAY_CURRENCIES
  - Currency region maps:
      CURRENCY_TO_REGION keys ↔ SUPPORTED_CURRENCIES
      GEOGRAPHIC_COLOR_MAP/GEOGRAPHIC_LABELS keys include all mapped regions + Other
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
BACKEND_CONSTANTS = ROOT / "backend" / "domain" / "core" / "constants.py"
BACKEND_PORTFOLIO_CONSTANTS = ROOT / "backend" / "domain" / "core" / "_constants_portfolio.py"
BACKEND_MARKET_CONSTANTS = ROOT / "backend" / "domain" / "core" / "_constants_market.py"
FRONTEND_CONSTANTS = ROOT / "frontend-react" / "src" / "lib" / "constants.ts"


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def _get_node_name(node: ast.AST) -> str | None:
    """Return the variable name from an Assign or AnnAssign node."""
    if isinstance(node, ast.Assign):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            return node.targets[0].id
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _get_node_value(node: ast.AST) -> ast.expr | None:
    """Return the value expression from an Assign or AnnAssign node."""
    if isinstance(node, ast.Assign):
        return node.value
    elif isinstance(node, ast.AnnAssign):
        return node.value
    return None


def extract_python_list(filepath: Path, var_name: str) -> list[str]:
    """Extract a top-level list constant from a Python file using AST."""
    source = filepath.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if (
            _get_node_name(node) == var_name
            and isinstance(_get_node_value(node), ast.List)
        ):
            value = _get_node_value(node)
            assert isinstance(value, ast.List)
            return [
                elt.value
                for elt in value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
    raise ValueError(f"{var_name} not found as a list in {filepath}")


def extract_python_dict(filepath: Path, var_name: str) -> dict[str, str]:
    """Extract a top-level dict[str, str] constant from a Python file using AST."""
    source = filepath.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if (
            _get_node_name(node) == var_name
            and isinstance(_get_node_value(node), ast.Dict)
        ):
            value = _get_node_value(node)
            assert isinstance(value, ast.Dict)
            result = {}
            for k, v in zip(value.keys, value.values):
                if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                    result[k.value] = v.value
            return result
    raise ValueError(f"{var_name} not found as a dict in {filepath}")


def extract_ts_array(filepath: Path, var_name: str) -> list[str]:
    """Extract a TypeScript array constant (string literals) using regex."""
    source = filepath.read_text()
    # Match: export const VAR_NAME = [ ... ] as const
    pattern = rf"export\s+const\s+{re.escape(var_name)}\s*=\s*\[(.*?)\]"
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        raise ValueError(f"{var_name} not found as an array in {filepath}")
    body = match.group(1)
    return re.findall(r'"([^"]+)"', body)


def extract_ts_record(filepath: Path, var_name: str) -> dict[str, str]:
    """Extract a TypeScript Record<string, string> constant using regex."""
    source = filepath.read_text()
    # Match: export const VAR_NAME: Record<...> = { ... }
    pattern = rf"export\s+const\s+{re.escape(var_name)}[^=]*=\s*\{{(.*?)\}}"
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        raise ValueError(f"{var_name} not found as a record in {filepath}")
    body = match.group(1)
    # Parse key: "value" pairs
    result = {}
    for pair in re.finditer(r'(\w+)\s*:\s*"([^"]+)"', body):
        result[pair.group(1)] = pair.group(2)
    return result


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_categories() -> list[str]:
    """Verify backend STOCK_CATEGORIES matches frontend STOCK_CATEGORIES."""
    errors = []
    backend = extract_python_list(BACKEND_PORTFOLIO_CONSTANTS, "STOCK_CATEGORIES")
    frontend = list(extract_ts_array(FRONTEND_CONSTANTS, "STOCK_CATEGORIES"))
    if backend != frontend:
        errors.append(
            f"STOCK_CATEGORIES mismatch:\n"
            f"  backend  STOCK_CATEGORIES:        {backend}\n"
            f"  frontend STOCK_CATEGORIES:        {frontend}"
        )
    return errors


def check_radar_categories() -> list[str]:
    """Verify backend RADAR_CATEGORIES matches frontend RADAR_CATEGORIES."""
    errors = []
    backend_radar = extract_python_list(BACKEND_PORTFOLIO_CONSTANTS, "RADAR_CATEGORIES")
    frontend = list(extract_ts_array(FRONTEND_CONSTANTS, "RADAR_CATEGORIES"))
    if backend_radar != frontend:
        errors.append(
            f"RADAR_CATEGORIES mismatch:\n"
            f"  backend  RADAR_CATEGORIES:                {backend_radar}\n"
            f"  frontend RADAR_CATEGORIES:                {frontend}"
        )
    return errors


def check_category_icons() -> list[str]:
    """Verify CATEGORY_ICON matches CATEGORY_ICON_SHORT."""
    errors = []
    backend = extract_python_dict(BACKEND_PORTFOLIO_CONSTANTS, "CATEGORY_ICON")
    frontend = extract_ts_record(FRONTEND_CONSTANTS, "CATEGORY_ICON_SHORT")
    if backend != frontend:
        only_backend = {k: v for k, v in backend.items() if frontend.get(k) != v}
        only_frontend = {k: v for k, v in frontend.items() if backend.get(k) != v}
        errors.append(
            f"CATEGORY_ICON mismatch:\n"
            f"  backend-only changes:  {only_backend}\n"
            f"  frontend-only changes: {only_frontend}"
        )
    return errors


def check_currencies() -> list[str]:
    """Verify currency constants stay aligned across backend/frontend surfaces."""
    errors = []
    backend = extract_python_list(BACKEND_MARKET_CONSTANTS, "SUPPORTED_CURRENCIES")
    backend_set = set(backend)
    backend_currency_region = extract_python_dict(BACKEND_MARKET_CONSTANTS, "CURRENCY_REGION_MAP")

    frontend_fx = list(extract_ts_array(FRONTEND_CONSTANTS, "FX_CURRENCY_OPTIONS"))
    frontend_cash = list(extract_ts_array(FRONTEND_CONSTANTS, "CASH_CURRENCY_OPTIONS"))
    frontend_display = list(extract_ts_array(FRONTEND_CONSTANTS, "DISPLAY_CURRENCIES"))

    if backend_set != set(frontend_fx):
        errors.append(
            f"Supported currencies mismatch (FX):\n"
            f"  backend  SUPPORTED_CURRENCIES: {backend}\n"
            f"  frontend FX_CURRENCY_OPTIONS:  {frontend_fx}"
        )

    if backend_set != set(frontend_cash):
        errors.append(
            f"Supported currencies mismatch (cash):\n"
            f"  backend  SUPPORTED_CURRENCIES:  {backend}\n"
            f"  frontend CASH_CURRENCY_OPTIONS: {frontend_cash}"
        )

    if backend_set != set(frontend_display):
        errors.append(
            f"Supported currencies mismatch (display):\n"
            f"  backend  SUPPORTED_CURRENCIES: {backend}\n"
            f"  frontend DISPLAY_CURRENCIES:   {frontend_display}"
        )

    # Order guardrails: keep a stable, predictable user-facing currency order.
    if frontend_fx != backend:
        errors.append(
            f"Currency order mismatch (FX):\n"
            f"  backend  SUPPORTED_CURRENCIES order: {backend}\n"
            f"  frontend FX_CURRENCY_OPTIONS order:  {frontend_fx}"
        )

    if frontend_cash != frontend_display:
        errors.append(
            f"Currency order mismatch (cash/display):\n"
            f"  frontend CASH_CURRENCY_OPTIONS: {frontend_cash}\n"
            f"  frontend DISPLAY_CURRENCIES:    {frontend_display}"
        )

    currency_to_region = extract_ts_record(FRONTEND_CONSTANTS, "CURRENCY_TO_REGION")
    region_colors = extract_ts_record(FRONTEND_CONSTANTS, "GEOGRAPHIC_COLOR_MAP")
    region_labels = extract_ts_record(FRONTEND_CONSTANTS, "GEOGRAPHIC_LABELS")

    if backend_set != set(currency_to_region.keys()):
        errors.append(
            f"CURRENCY_TO_REGION keys mismatch:\n"
            f"  expected from SUPPORTED_CURRENCIES: {sorted(backend_set)}\n"
            f"  actual CURRENCY_TO_REGION keys:     {sorted(currency_to_region.keys())}"
        )

    if backend_set != set(backend_currency_region.keys()):
        errors.append(
            f"CURRENCY_REGION_MAP keys mismatch:\n"
            f"  expected from SUPPORTED_CURRENCIES: {sorted(backend_set)}\n"
            f"  actual CURRENCY_REGION_MAP keys:    {sorted(backend_currency_region.keys())}"
        )

    if backend_currency_region != currency_to_region:
        only_backend = {
            k: v for k, v in backend_currency_region.items() if currency_to_region.get(k) != v
        }
        only_frontend = {
            k: v for k, v in currency_to_region.items() if backend_currency_region.get(k) != v
        }
        errors.append(
            f"Currency region mapping mismatch:\n"
            f"  backend  CURRENCY_REGION_MAP: {backend_currency_region}\n"
            f"  frontend CURRENCY_TO_REGION:  {currency_to_region}\n"
            f"  differing backend entries:    {only_backend}\n"
            f"  differing frontend entries:   {only_frontend}"
        )

    expected_regions = set(currency_to_region.values()) | {"Other"}
    color_keys = set(region_colors.keys())
    label_keys = set(region_labels.keys())

    if expected_regions != color_keys:
        errors.append(
            f"GEOGRAPHIC_COLOR_MAP keys mismatch:\n"
            f"  expected region keys: {sorted(expected_regions)}\n"
            f"  actual color keys:    {sorted(color_keys)}"
        )

    if expected_regions != label_keys:
        errors.append(
            f"GEOGRAPHIC_LABELS keys mismatch:\n"
            f"  expected region keys: {sorted(expected_regions)}\n"
            f"  actual label keys:    {sorted(label_keys)}"
        )
    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def preflight() -> None:
    """Assert all constant files exist."""
    for path in (
        BACKEND_CONSTANTS,
        BACKEND_PORTFOLIO_CONSTANTS,
        BACKEND_MARKET_CONSTANTS,
        FRONTEND_CONSTANTS,
    ):
        if not path.exists():
            print(f"ERROR: constant file not found: {path}")
            sys.exit(1)


def main() -> None:
    preflight()
    errors: list[str] = []
    errors.extend(check_categories())
    errors.extend(check_radar_categories())
    errors.extend(check_category_icons())
    errors.extend(check_currencies())

    if errors:
        print("Constant sync errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("Constants in sync.")


if __name__ == "__main__":
    main()

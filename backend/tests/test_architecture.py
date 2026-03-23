"""
Architecture boundary tests — enforce clean architecture layer dependencies.

Allowed dependency direction:
  domain/     → stdlib only (no application, infrastructure, api)
  application/ → domain, infrastructure, i18n, logging_config
  infrastructure/ → domain, i18n, logging_config (NOT application, api)
  api/        → application, domain, api, i18n, logging_config (NOT infrastructure, except get_session)
"""

import ast
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).parent.parent

LAYER_RULES = {
    "domain": {
        "forbidden": ["application", "infrastructure", "api"],
        "note": "Domain must not depend on any outer layer",
    },
    "infrastructure": {
        "forbidden": ["application", "api"],
        "note": "Infrastructure must not depend on application or api",
    },
    "api": {
        "forbidden_modules": [
            "infrastructure.repositories",
            "infrastructure.market_data",
            "infrastructure.notification",
            "infrastructure.crypto",
            "infrastructure.sec_edgar",
        ],
        "allowed_infrastructure": ["infrastructure.database"],
        "note": "API routes may only import get_session from infrastructure.database",
    },
}


def _collect_imports(filepath: Path) -> list[str]:
    """Parse a Python file and return all imported module names."""
    source = filepath.read_text()
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _get_python_files(layer_dir: Path) -> list[Path]:
    """Get all .py files in a layer directory (non-recursive for test files)."""
    if not layer_dir.exists():
        return []
    return sorted(layer_dir.rglob("*.py"))


class TestDomainBoundary:
    """Domain layer must not import from application, infrastructure, or api."""

    @pytest.fixture
    def domain_files(self):
        return _get_python_files(BACKEND_ROOT / "domain")

    def test_no_forbidden_imports(self, domain_files):
        violations = []
        for filepath in domain_files:
            imports = _collect_imports(filepath)
            violations.extend(
                f"{filepath.name}: imports {imp}"
                for imp in imports
                for forbidden in LAYER_RULES["domain"]["forbidden"]
                if imp == forbidden or imp.startswith(f"{forbidden}.")
            )
        assert violations == [], "Domain layer violations:\n" + "\n".join(violations)


class TestInfrastructureBoundary:
    """Infrastructure must not import from application or api."""

    @pytest.fixture
    def infra_files(self):
        return _get_python_files(BACKEND_ROOT / "infrastructure")

    def test_no_forbidden_imports(self, infra_files):
        violations = []
        for filepath in infra_files:
            imports = _collect_imports(filepath)
            violations.extend(
                f"{filepath.name}: imports {imp}"
                for imp in imports
                for forbidden in LAYER_RULES["infrastructure"]["forbidden"]
                if imp == forbidden or imp.startswith(f"{forbidden}.")
            )
        assert violations == [], "Infrastructure layer violations:\n" + "\n".join(
            violations
        )


class TestApiControllerBoundary:
    """API routes may only use infrastructure.database (for get_session)."""

    @pytest.fixture
    def api_files(self):
        return _get_python_files(BACKEND_ROOT / "api")

    def test_no_direct_infrastructure_imports(self, api_files):
        allowed = set(LAYER_RULES["api"]["allowed_infrastructure"])
        violations = [
            f"{filepath.name}: imports {imp}"
            for filepath in api_files
            for imp in _collect_imports(filepath)
            if imp.startswith("infrastructure") and imp not in allowed
        ]
        assert violations == [], "API layer infrastructure violations:\n" + "\n".join(
            violations
        )


class TestNotificationDisplayNames:
    """Guard that Telegram/chat notification formatter functions never display
    bare ticker identifiers directly.  Every stock identifier shown to users
    must be wrapped in ``format_stock_display`` so that human-readable names
    appear alongside the raw ticker symbol.

    The test scans ``application/formatters.py`` for functions whose names
    suggest they build Telegram or chat messages and flags any line that
    contains a raw ``item['ticker']`` or ``item["ticker"]`` access that is not
    already guarded by a ``format_stock_display`` or ``resolve_display_names``
    call within the same function body.

    Known limitations (heuristic-based check):
    - Guard detection is function-wide text search, not line-scoped: a single
      mention of ``format_stock_display`` anywhere in the function body (even
      a comment) satisfies the guard. Precise per-line checking would require
      full AST dataflow analysis.
    - Only ``item['ticker']`` / ``item["ticker"]`` subscription access is
      detected as "bare"; other patterns such as ``item.get("ticker")``,
      ``s.ticker``, or loop variables are not flagged.
    """

    _FORMATTERS_PATH = Path(__file__).parent.parent / "application" / "formatters.py"

    # Telegram/chat formatter functions that must not expose bare item['ticker']
    _NOTIFICATION_FUNC_PREFIXES = (
        "format_weekly_digest",
        "format_guru_",
        "format_resonance_",
        "format_withdrawal_",
    )

    def test_no_bare_ticker_in_notification_formatters(self):
        """Formatter functions must not directly subscript item['ticker'] / item[\"ticker\"]
        without wrapping the result in format_stock_display."""
        import re

        source = self._FORMATTERS_PATH.read_text()
        tree = ast.parse(source)

        # Patterns indicating a bare ticker access going directly into a string
        bare_patterns = [
            re.compile(r"""item\[['"]ticker['"]\]"""),
        ]
        guard_patterns = [
            re.compile(r"format_stock_display"),
            re.compile(r"resolve_display_names"),
            re.compile(r"_names\.get"),
            re.compile(r"name_map"),
        ]

        violations: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if not any(
                node.name.startswith(p) for p in self._NOTIFICATION_FUNC_PREFIXES
            ):
                continue
            lines = source.splitlines()
            func_source = "\n".join(lines[node.lineno - 1 : node.end_lineno])

            # Skip functions that have no bare pattern at all
            has_bare = any(p.search(func_source) for p in bare_patterns)
            if not has_bare:
                continue

            # If bare pattern exists but NO guard exists, it's a violation
            has_guard = any(p.search(func_source) for p in guard_patterns)
            if not has_guard:
                violations.append(
                    f"{node.name} (line {node.lineno}): contains bare item['ticker'] "
                    "without format_stock_display / resolve_display_names guard"
                )

        assert violations == [], (
            "Notification formatters must wrap all ticker displays with "
            "format_stock_display(name, ticker):\n" + "\n".join(violations)
        )


class TestDomainConstantsAllSync:
    """Guard that domain/core/constants.__all__ stays in sync with the module's
    public names.  Prevents the __all__ list from drifting when constants are
    added or removed."""

    def test_all_contains_every_public_name(self):
        import types

        import domain.core.constants as mod

        declared = set(mod.__all__)
        actual = {
            name
            for name in dir(mod)
            if not name.startswith("_")
            and not isinstance(getattr(mod, name), types.ModuleType)
        }
        missing_from_all = actual - declared
        assert not missing_from_all, (
            f"Names defined in domain.core.constants but missing from __all__: "
            f"{sorted(missing_from_all)}\n"
            "Add them to __all__ in backend/domain/core/constants.py."
        )

    def test_all_has_no_phantom_names(self):
        import domain.core.constants as mod

        declared = set(mod.__all__)
        actual = set(dir(mod))
        phantom = declared - actual
        assert not phantom, (
            f"Names in __all__ that are not defined in domain.core.constants: "
            f"{sorted(phantom)}\n"
            "Remove them from __all__ in backend/domain/core/constants.py."
        )

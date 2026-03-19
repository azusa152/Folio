"""Tax wrapper constant/enumeration consistency tests."""

from domain.constants import TAX_WRAPPER_OPTIONS
from domain.enums import TAX_WRAPPER_LABEL, TAX_WRAPPER_TREATMENT, TaxWrapperType


def test_tax_wrapper_constants_should_match_enum_values() -> None:
    enum_values = {item.value for item in TaxWrapperType}
    option_values = set(TAX_WRAPPER_OPTIONS)
    label_values = set(TAX_WRAPPER_LABEL.keys())
    treatment_values = set(TAX_WRAPPER_TREATMENT.keys())

    assert option_values == enum_values
    assert label_values == enum_values
    assert treatment_values == enum_values

"""Unit tests for CanonicalUnitNormalizer."""
from decimal import Decimal
import pytest

from app.lib.units import (
    CanonicalUnit,
    IncompatibleUnitError,
    UnitCategory,
    are_units_compatible,
    convert_quantity,
    get_unit_info,
    normalize_to_canonical,
)


def test_mass_unit_normalization():
    # 1,000 kg -> 1 MT
    canonical_qty, base_unit = normalize_to_canonical(1000, "kg")
    assert base_unit == CanonicalUnit.METRIC_TONNE
    assert canonical_qty == Decimal("1.000")

    # 20 bags of 50kg -> 1 MT
    canonical_qty, base_unit = normalize_to_canonical(20, "BAG_50KG")
    assert base_unit == CanonicalUnit.METRIC_TONNE
    assert canonical_qty == Decimal("1.00")

    # 10 quintals -> 1 MT
    canonical_qty, base_unit = normalize_to_canonical(10, "QUINTAL")
    assert base_unit == CanonicalUnit.METRIC_TONNE
    assert canonical_qty == Decimal("1.0")


def test_volume_unit_normalization():
    # 1,000 liters -> 1 cubic meter
    canonical_qty, base_unit = normalize_to_canonical(1000, "liter")
    assert base_unit == CanonicalUnit.CUBIC_METER
    assert canonical_qty == Decimal("1.000")

    # 5 kiloliters -> 5 cubic meters
    canonical_qty, base_unit = normalize_to_canonical(5, "KL")
    assert base_unit == CanonicalUnit.CUBIC_METER
    assert canonical_qty == Decimal("5.0")


def test_discrete_unit_normalization():
    # 12 dozen -> 144 units
    canonical_qty, base_unit = normalize_to_canonical(12, "dozen")
    assert base_unit == CanonicalUnit.UNITS
    assert canonical_qty == Decimal("144.0")

    # 3 thousand -> 3000 units
    canonical_qty, base_unit = normalize_to_canonical(3, "thousand")
    assert base_unit == CanonicalUnit.UNITS
    assert canonical_qty == Decimal("3000.0")


def test_time_unit_normalization():
    # 5 days (8h standard work shift) -> 40 hours
    canonical_qty, base_unit = normalize_to_canonical(5, "DAY_8H")
    assert base_unit == CanonicalUnit.HOURS
    assert canonical_qty == Decimal("40.0")


def test_conversion_between_compatible_units():
    # 2 MT to kg
    kg = convert_quantity(2, "MT", "KG")
    assert kg == Decimal("2000")

    # 500 kg to bags of 50kg
    bags = convert_quantity(500, "KG", "BAG_50KG")
    assert bags == Decimal("10")


def test_rejection_of_incompatible_dimensions():
    # Cannot convert Liters to Metric Tonnes without density
    assert not are_units_compatible("LITER", "METRIC_TONNE")
    with pytest.raises(IncompatibleUnitError) as exc_info:
        convert_quantity(1000, "LITER", "METRIC_TONNE")
    assert "Cannot convert incompatible dimensions" in str(exc_info.value)

    # Cannot convert hours to units
    assert not are_units_compatible("HOURS", "UNITS")
    with pytest.raises(IncompatibleUnitError):
        convert_quantity(10, "HOURS", "UNITS")


def test_unrecognized_unit_handling():
    assert get_unit_info("UNKNOWN_XYZ") is None
    with pytest.raises(IncompatibleUnitError) as exc_info:
        normalize_to_canonical(10, "UNKNOWN_XYZ")
    assert "Unsupported or unrecognized unit" in str(exc_info.value)


def test_us_vs_imperial_gallon_distinction():
    # US liquid gallon vs Imperial gallon have distinct volumes
    us_vol, base_us = normalize_to_canonical(100, "GALLON_US")
    imp_vol, base_imp = normalize_to_canonical(100, "GALLON_IMP")

    assert base_us == CanonicalUnit.CUBIC_METER
    assert base_imp == CanonicalUnit.CUBIC_METER
    assert us_vol == Decimal("0.378541")
    assert imp_vol == Decimal("0.454609")
    # Imperial gallon is larger than US gallon
    assert imp_vol > us_vol

    # Barrel volume check (42 US gal)
    bbl_vol, _ = normalize_to_canonical(1, "BARREL")
    assert bbl_vol == Decimal("0.1589873")


def test_pound_mass_normalization():
    # 1 MT is approximately 2204.62 lbs
    lbs = convert_quantity(1, "MT", "LB")
    assert round(float(lbs), 1) == 2204.6


def test_discrete_transport_and_packaging_units():
    # Containers, truckloads, pallets normalize to discrete UNITS base
    qty_c, base_c = normalize_to_canonical(5, "CONTAINER")
    assert base_c == CanonicalUnit.UNITS
    assert qty_c == Decimal("5.0")

    qty_t, base_t = normalize_to_canonical(10, "TRUCKLOAD")
    assert base_t == CanonicalUnit.UNITS
    assert qty_t == Decimal("10.0")

    # Rejection of discrete to mass (no assumed truck capacity)
    assert not are_units_compatible("TRUCKLOAD", "METRIC_TONNE")
    with pytest.raises(IncompatibleUnitError):
        convert_quantity(5, "TRUCKLOAD", "METRIC_TONNE")

    assert not are_units_compatible("CONTAINER", "CUBIC_METER")
    with pytest.raises(IncompatibleUnitError):
        convert_quantity(2, "CONTAINER", "CUBIC_METER")


def test_service_time_units():
    # 5 man-days -> 40 hours
    man_days_hrs, base = normalize_to_canonical(5, "MAN_DAY")
    assert base == CanonicalUnit.HOURS
    assert man_days_hrs == Decimal("40.0")

    # 1 man-month -> 160 hours
    man_month_hrs, _ = normalize_to_canonical(1, "MAN_MONTH")
    assert man_month_hrs == Decimal("160.0")

    # 2 days (24h) -> 48 hours
    day24_hrs, _ = normalize_to_canonical(2, "DAY_24H")
    assert day24_hrs == Decimal("48.0")


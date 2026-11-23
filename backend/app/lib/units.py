"""Canonical unit normalizer for business requirements and offerings.

Normalizes commercial quantities across compatible units and strictly rejects
incompatible cross-category conversions (e.g., volume to mass without density).
"""
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional, Tuple


class UnitCategory(str, Enum):
    MASS = "MASS"
    VOLUME = "VOLUME"
    DISCRETE = "DISCRETE"
    TIME = "TIME"


class CanonicalUnit(str, Enum):
    METRIC_TONNE = "METRIC_TONNE"
    CUBIC_METER = "CUBIC_METER"
    UNITS = "UNITS"
    HOURS = "HOURS"


class IncompatibleUnitError(ValueError):
    """Raised when attempting to convert between incompatible unit dimensions."""
    pass


# Map of supported unit aliases to (Category, Base Canonical Unit, Multiplier to Base)
UNIT_REGISTRY: Dict[str, Tuple[UnitCategory, CanonicalUnit, Decimal]] = {
    # Mass (Base: METRIC_TONNE)
    "METRIC_TONNE": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("1.0")),
    "MT": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("1.0")),
    "TONNE": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("1.0")),
    "TONNES": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("1.0")),
    "TON": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("1.0")),
    "TONS": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("1.0")),
    "KILOGRAM": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("0.001")),
    "KG": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("0.001")),
    "KGS": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("0.001")),
    "BAG_50KG": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("0.05")),
    "BAGS_50KG": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("0.05")),
    "BAG": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("0.05")),
    "BAGS": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("0.05")),
    "QUINTAL": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("0.1")),
    "QUINTALS": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("0.1")),
    "POUND": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("0.00045359237")),
    "POUNDS": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("0.00045359237")),
    "LB": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("0.00045359237")),
    "LBS": (UnitCategory.MASS, CanonicalUnit.METRIC_TONNE, Decimal("0.00045359237")),

    # Volume (Base: CUBIC_METER)
    "CUBIC_METER": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("1.0")),
    "CUM": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("1.0")),
    "M3": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("1.0")),
    "LITER": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("0.001")),
    "LITERS": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("0.001")),
    "LITRE": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("0.001")),
    "LITRES": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("0.001")),
    "L": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("0.001")),
    "KILOLITER": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("1.0")),
    "KL": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("1.0")),
    "GALLON_US": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("0.00378541")),
    "GALLON_UK": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("0.00454609")),
    "GALLON_IMP": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("0.00454609")),
    "IMPERIAL_GALLON": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("0.00454609")),
    "BARREL": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("0.1589873")),
    "BARRELS": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("0.1589873")),
    "BBL": (UnitCategory.VOLUME, CanonicalUnit.CUBIC_METER, Decimal("0.1589873")),

    # Discrete (Base: UNITS)
    "UNIT": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "UNITS": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "PCS": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "PIECES": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "SET": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "SETS": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "BOX": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "BOXES": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "PALLET": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "PALLETS": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "CONTAINER": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "CONTAINERS": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "TRUCKLOAD": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "TRUCKLOADS": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "TRUCK": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "TRUCKS": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "VEHICLE": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "VEHICLES": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "BATCH": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "BATCHES": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1.0")),
    "DOZEN": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("12.0")),
    "DOZENS": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("12.0")),
    "HUNDRED": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("100.0")),
    "THOUSAND": (UnitCategory.DISCRETE, CanonicalUnit.UNITS, Decimal("1000.0")),

    # Professional Time (Base: HOURS)
    "HOUR": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("1.0")),
    "HOURS": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("1.0")),
    "HR": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("1.0")),
    "HRS": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("1.0")),
    "MAN_HOUR": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("1.0")),
    "MAN_HOURS": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("1.0")),
    "DAY_8H": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("8.0")),
    "DAYS_8H": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("8.0")),
    "MAN_DAY": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("8.0")),
    "MAN_DAYS": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("8.0")),
    "SHIFT_8H": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("8.0")),
    "DAY_24H": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("24.0")),
    "DAYS_24H": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("24.0")),
    "WEEK_40H": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("40.0")),
    "MAN_WEEK": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("40.0")),
    "MAN_WEEKS": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("40.0")),
    "MONTH_160H": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("160.0")),
    "MAN_MONTH": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("160.0")),
    "MAN_MONTHS": (UnitCategory.TIME, CanonicalUnit.HOURS, Decimal("160.0")),
}


def normalize_unit_string(unit: str) -> str:
    """Normalize input string to uppercase alphanumeric with underscore."""
    if not unit:
        return ""
    clean = unit.strip().upper().replace(" ", "_").replace("-", "_")
    return clean


def get_unit_info(unit: str) -> Optional[Tuple[UnitCategory, CanonicalUnit, Decimal]]:
    """Return (Category, CanonicalUnit, Multiplier) for a given unit string."""
    norm = normalize_unit_string(unit)
    return UNIT_REGISTRY.get(norm)


def are_units_compatible(unit_a: str, unit_b: str) -> bool:
    """Check if two units belong to the same physical dimension."""
    info_a = get_unit_info(unit_a)
    info_b = get_unit_info(unit_b)
    if not info_a or not info_b:
        return False
    return info_a[0] == info_b[0]


def normalize_to_canonical(quantity: Decimal | float | int, unit: str) -> Tuple[Decimal, CanonicalUnit]:
    """Convert a quantity to its dimension's canonical base unit.

    Returns:
        (canonical_quantity, canonical_unit)
    """
    info = get_unit_info(unit)
    if not info:
        raise IncompatibleUnitError(f"Unsupported or unrecognized unit: '{unit}'")

    cat, base_unit, factor = info
    dec_qty = Decimal(str(quantity))
    canonical_qty = dec_qty * factor
    return canonical_qty, base_unit


def convert_quantity(
    quantity: Decimal | float | int, from_unit: str, to_unit: str
) -> Decimal:
    """Convert quantity between two compatible units.

    Raises:
        IncompatibleUnitError: if units belong to different categories or are unrecognized.
    """
    info_from = get_unit_info(from_unit)
    info_to = get_unit_info(to_unit)

    if not info_from:
        raise IncompatibleUnitError(f"Unrecognized source unit: '{from_unit}'")
    if not info_to:
        raise IncompatibleUnitError(f"Unrecognized target unit: '{to_unit}'")

    if info_from[0] != info_to[0]:
        raise IncompatibleUnitError(
            f"Cannot convert incompatible dimensions: '{from_unit}' ({info_from[0].value}) "
            f"to '{to_unit}' ({info_to[0].value})"
        )

    dec_qty = Decimal(str(quantity))
    # quantity * factor_from gives base; base / factor_to gives target
    base_qty = dec_qty * info_from[2]
    return base_qty / info_to[2]

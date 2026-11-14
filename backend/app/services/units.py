"""Explicit unit normalisation.

POLIS never silently merges different units. When a lab report uses a supported
alternate unit, the value and its reference interval are converted together and
the original unit is preserved in provenance and surfaced in the UI. Unsupported
units are rejected rather than guessed.
"""

from __future__ import annotations

from dataclasses import dataclass


class UnitError(ValueError):
    """Raised when a unit is not supported for the requested biomarker."""


@dataclass(frozen=True)
class Conversion:
    factor: float
    note: str


# Alternate unit -> canonical unit factors, keyed by biomarker code.
_CONVERSIONS: dict[str, dict[str, Conversion]] = {
    "glucose": {"mmol/l": Conversion(18.0182, "mmol/L × 18.0182 → mg/dL")},
    "creatinine": {"umol/l": Conversion(0.0113122, "µmol/L ÷ 88.4 → mg/dL")},
    "bilirubin": {"umol/l": Conversion(0.058467, "µmol/L ÷ 17.104 → mg/dL")},
    "total_cholesterol": {"mmol/l": Conversion(38.67, "mmol/L × 38.67 → mg/dL")},
    "ldl": {"mmol/l": Conversion(38.67, "mmol/L × 38.67 → mg/dL")},
    "hdl": {"mmol/l": Conversion(38.67, "mmol/L × 38.67 → mg/dL")},
    "triglycerides": {"mmol/l": Conversion(88.57, "mmol/L × 88.57 → mg/dL")},
    "testosterone": {"nmol/l": Conversion(28.842, "nmol/L × 28.84 → ng/dL")},
    "estradiol": {"pmol/l": Conversion(0.2724, "pmol/L ÷ 3.671 → pg/mL")},
    "cortisol": {"nmol/l": Conversion(0.03625, "nmol/L ÷ 27.59 → µg/dL")},
    "hemoglobin": {"g/l": Conversion(0.1, "g/L ÷ 10 → g/dL")},
    "ferritin": {"pmol/l": Conversion(0.445, "pmol/L × 0.445 → ng/mL")},
    "tsh": {
        "uiu/ml": Conversion(1.0, "µIU/mL is numerically equivalent to mIU/L"),
        "miu/l": Conversion(1.0, "mIU/L is numerically equivalent to µIU/mL"),
    },
    "wbc": {"k/ul": Conversion(1.0, "10³/µL is numerically equivalent to ×10⁹/L")},
    "platelets": {"k/ul": Conversion(1.0, "10³/µL is numerically equivalent to ×10⁹/L")},
    "rbc": {"million/ul": Conversion(1.0, "10⁶/µL is numerically equivalent to ×10¹²/L")},
    "free_t4": {"pmol/l": Conversion(0.0777, "pmol/L × 0.0777 → ng/dL")},
    "free_t3": {"pmol/l": Conversion(0.651, "pmol/L × 0.651 → pg/mL")},
    "vitamin_d": {"nmol/l": Conversion(0.4006, "nmol/L × 0.4006 → ng/mL")},
    "b12": {"pmol/l": Conversion(1.355, "pmol/L × 1.355 → pg/mL")},
}


def normalize_unit(unit: str) -> str:
    return (
        unit.strip()
        .lower()
        .replace("μ", "u")
        .replace("µ", "u")
        .replace("³", "3")
        .replace("²", "2")
        .replace(" ", "")
    )


def convert_to_canonical(code: str, value: float, unit: str, canonical_unit: str) -> tuple[float, str | None]:
    """Return (canonical_value, human-readable conversion note or None).

    Raises UnitError for any unit that is not exactly canonical or explicitly
    supported. HbA1c uses the NGSP/IFCC equation rather than a linear factor.
    """
    supplied = normalize_unit(unit)
    canonical = normalize_unit(canonical_unit)
    if supplied == canonical:
        return value, None

    if code == "hba1c" and supplied == "mmol/mol":
        converted = (0.09148 * value) + 2.152
        return round(converted, 2), "IFCC mmol/mol → NGSP % using the NGSP equation"

    conversions = _CONVERSIONS.get(code, {})
    conversion = conversions.get(supplied)
    if not conversion:
        raise UnitError(
            f"Unit '{unit}' is not supported for {code}. Use '{canonical_unit}'. "
            "POLIS will not guess or silently merge incompatible units."
        )
    return round(value * conversion.factor, 4), conversion.note


def supported_units(code: str, canonical_unit: str) -> list[str]:
    units = [canonical_unit]
    units.extend(list(_CONVERSIONS.get(code, {}).keys()))
    if code == "hba1c":
        units.append("mmol/mol")
    return units

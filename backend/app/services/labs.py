"""Laboratory result classification, serialization and trend computation."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Biomarker, LabResult
from app.schemas import LabCreate, LabResultOut, TrendOut, TrendPoint
from app.services.units import UnitError, convert_to_canonical


def classify_range(value: float, low: float | None, high: float | None) -> str:
    """Classify against the *result's own* reference interval only.

    If the laboratory did not supply a usable interval, the result remains
    indeterminate. POLIS deliberately does not fall back to population ranges
    for clinical classification.
    """
    if low is None and high is None:
        return "indeterminate"
    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"
    if low is not None or high is not None:
        return "normal"
    return "indeterminate"


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def serialize_lab(
    result: LabResult,
    biomarker: Biomarker,
    *,
    now: datetime | None = None,
    converted_from: str | None = None,
) -> LabResultOut:
    now = now or datetime.now(UTC)
    measured = _aware(result.measured_at)
    age_days = max((now - measured).days, 0)
    ref_low = result.ref_low
    ref_high = result.ref_high
    status = classify_range(result.value, ref_low, ref_high)
    display = f"{result.value:g}" if abs(result.value) >= 1 else f"{result.value:.3g}"
    return LabResultOut(
        id=result.id,
        biomarker_id=result.biomarker_id,
        code=biomarker.code,
        name=biomarker.name,
        category=biomarker.category,
        value=result.value,
        unit=result.unit,
        display_value=display,
        ref_low=ref_low,
        ref_high=ref_high,
        ref_text=result.ref_text,
        range_status=status,  # type: ignore[arg-type]
        measured_at=measured,
        source=result.source,
        method=result.method,
        confidence=result.confidence,
        quality_status=result.quality_status,
        notes=result.notes,
        context=result.context or {},
        is_synthetic=result.is_synthetic,
        is_stale=age_days > 365,
        age_days=age_days,
        converted_from=converted_from
        or (result.provenance or {}).get("unit_conversion_from"),
    )


def create_result(
    db: Session,
    *,
    user_id: str,
    payload: LabCreate,
    source: str,
    quality_status: str = "self_reported",
    confidence: float = 0.75,
    is_synthetic: bool = False,
    context: dict | None = None,
    provenance: dict | None = None,
) -> LabResult:
    biomarker = db.scalar(select(Biomarker).where(Biomarker.code == payload.code.strip()))
    if not biomarker:
        raise UnitError(f"Unknown biomarker code '{payload.code}'")
    if payload.measured_at.tzinfo is None:
        measured_at = payload.measured_at.replace(tzinfo=UTC)
    else:
        measured_at = payload.measured_at.astimezone(UTC)
    if measured_at > datetime.now(UTC):
        raise ValueError("Measurement date cannot be in the future")

    try:
        value, conversion_note = convert_to_canonical(
            biomarker.code, payload.value, payload.unit, biomarker.canonical_unit
        )
        ref_low = payload.ref_low
        ref_high = payload.ref_high
        if conversion_note and ref_low is not None:
            ref_low, _ = convert_to_canonical(
                biomarker.code, ref_low, payload.unit, biomarker.canonical_unit
            )
        if conversion_note and ref_high is not None:
            ref_high, _ = convert_to_canonical(
                biomarker.code, ref_high, payload.unit, biomarker.canonical_unit
            )
    except UnitError:
        raise

    record_provenance = dict(provenance or {})
    if conversion_note:
        record_provenance["unit_conversion_from"] = payload.unit
        record_provenance["unit_conversion_detail"] = conversion_note
    record_provenance.setdefault("entered_source", source)
    record_provenance.setdefault("recorded_at", datetime.now(UTC).isoformat())

    result = LabResult(
        user_id=user_id,
        biomarker_id=biomarker.id,
        value=value,
        unit=biomarker.canonical_unit,
        ref_low=ref_low,
        ref_high=ref_high,
        ref_text=payload.ref_text,
        measured_at=measured_at,
        source=source,
        method=payload.method,
        confidence=confidence,
        quality_status=quality_status,
        notes=payload.notes,
        context=context or {},
        provenance=record_provenance,
        is_synthetic=is_synthetic,
    )
    db.add(result)
    db.flush()
    return result


def results_for_user(
    db: Session, user_id: str, *, latest_only: bool = False, category: str | None = None
) -> list[tuple[LabResult, Biomarker]]:
    stmt = (
        select(LabResult, Biomarker)
        .join(Biomarker, LabResult.biomarker_id == Biomarker.id)
        .where(LabResult.user_id == user_id)
        .order_by(LabResult.measured_at.desc())
    )
    if category:
        stmt = stmt.where(Biomarker.category == category)
    rows = list(db.execute(stmt).all())
    if not latest_only:
        return rows
    seen: set[str] = set()
    latest: list[tuple[LabResult, Biomarker]] = []
    for result, biomarker in rows:
        if biomarker.code not in seen:
            seen.add(biomarker.code)
            latest.append((result, biomarker))
    return latest


def latest_by_code(db: Session, user_id: str) -> dict[str, tuple[LabResult, Biomarker]]:
    return {biomarker.code: (result, biomarker) for result, biomarker in results_for_user(db, user_id, latest_only=True)}


def build_trends(db: Session, user_id: str) -> list[TrendOut]:
    rows = results_for_user(db, user_id)
    grouped: dict[str, list[tuple[LabResult, Biomarker]]] = {}
    for result, biomarker in rows:
        grouped.setdefault(biomarker.code, []).append((result, biomarker))

    trends: list[TrendOut] = []
    for code, items in grouped.items():
        items.sort(key=lambda pair: _aware(pair[0].measured_at))
        biomarker = items[0][1]
        points = [
            TrendPoint(
                date=_aware(result.measured_at),
                value=result.value,
                ref_low=result.ref_low,
                ref_high=result.ref_high,
                source=result.source,
                is_synthetic=result.is_synthetic,
            )
            for result, _ in items
        ]
        latest = items[-1][0].value
        previous = items[-2][0].value if len(items) > 1 else None
        absolute = round(latest - previous, 4) if previous is not None else None
        percent = (
            round(((latest - previous) / previous) * 100, 1)
            if previous not in (None, 0) and absolute is not None
            else None
        )
        latest_result = items[-1][0]
        status = classify_range(latest, latest_result.ref_low, latest_result.ref_high)
        interval = ""
        if latest_result.ref_low is not None or latest_result.ref_high is not None:
            interval = f" The laboratory interval is {latest_result.ref_low}–{latest_result.ref_high} {biomarker.canonical_unit}."
        direction = "increased" if (absolute or 0) > 0 else "decreased" if (absolute or 0) < 0 else "unchanged"
        if previous is None:
            interpretation = f"Single available result; no trend can be inferred yet.{interval}"
        else:
            interpretation = (
                f"Latest value {direction} by {abs(absolute) if absolute is not None else 0:g} "
                f"{biomarker.canonical_unit} since the previous result. Latest status relative to the "
                f"laboratory interval: {status}.{interval} A change does not establish a cause."
            )
        trends.append(
            TrendOut(
                code=code,
                name=biomarker.name,
                unit=biomarker.canonical_unit,
                category=biomarker.category,
                points=points,
                latest=latest,
                previous=previous,
                absolute_change=absolute,
                percent_change=percent,
                interpretation=interpretation,
            )
        )
    trends.sort(key=lambda trend: (trend.category, trend.name))
    return trends

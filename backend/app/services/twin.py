"""Digital twin aggregation: systems, completeness, statuses and limitations.

Status values describe data availability and whether measured values fall
outside their reporting laboratory's interval. They never mean "diseased".
Experimental simulation outputs are deliberately excluded from organ status.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.biology import PATHWAYS, SYSTEMS
from app.models import HealthProfile, WearableMeasurement
from app.schemas import TwinOverview, TwinSignal, TwinSystemDetail, TwinSystemSummary
from app.services.labs import _aware, classify_range, latest_by_code, serialize_lab
from app.services.pgx import phenotype_map

METRIC_LABELS = {
    "resting_hr": ("Resting heart rate", "bpm"),
    "hrv": ("Heart-rate variability", "ms"),
    "sleep_duration": ("Sleep duration", "h"),
    "deep_sleep": ("Deep sleep", "h"),
    "rem_sleep": ("REM sleep", "h"),
    "steps": ("Steps", "steps"),
    "respiratory_rate": ("Respiratory rate", "breaths/min"),
    "skin_temp": ("Skin temperature deviation", "°C"),
    "spo2": ("Oxygen saturation", "%"),
    "active_minutes": ("Active minutes", "min"),
    "blood_pressure_systolic": ("Systolic blood pressure", "mmHg"),
    "blood_pressure_diastolic": ("Diastolic blood pressure", "mmHg"),
}

# Data completeness is capped where validated organ-function tests are absent.
# A profile can be rich in consumer data and still not support organ assessment.
COMPLETENESS_CAP = {
    "liver": 95,
    "kidneys": 95,
    "heart": 85,
    "lungs": 55,
    "brain": 60,
    "digestive": 65,
    "endocrine": 90,
    "immune": 85,
    "musculoskeletal": 75,
    "metabolic": 90,
}

SYSTEM_CONDITION_MAP = {
    "heart": ["Hypertension", "Hyperlipidemia"],
    "lungs": ["Asthma"],
    "endocrine": ["Hypothyroidism"],
    "metabolic": ["Hyperlipidemia", "Hypertension"],
    "immune": ["Seasonal allergic rhinitis"],
}


def latest_wearables(db: Session, user_id: str) -> dict[str, WearableMeasurement]:
    rows = list(
        db.scalars(
            select(WearableMeasurement)
            .where(WearableMeasurement.user_id == user_id)
            .order_by(WearableMeasurement.recorded_at.desc())
        ).all()
    )
    latest: dict[str, WearableMeasurement] = {}
    for row in rows:
        latest.setdefault(row.metric, row)
    return latest


def wearable_averages(db: Session, user_id: str, days: int = 14) -> dict[str, dict]:
    cutoff = datetime.now(UTC).timestamp() - days * 86400
    rows = list(
        db.scalars(
            select(WearableMeasurement)
            .where(WearableMeasurement.user_id == user_id)
            .order_by(WearableMeasurement.recorded_at.desc())
        ).all()
    )
    grouped: dict[str, list[WearableMeasurement]] = {}
    for row in rows:
        if _aware(row.recorded_at).timestamp() >= cutoff:
            grouped.setdefault(row.metric, []).append(row)
    result: dict[str, dict] = {}
    for metric, values in grouped.items():
        numeric = [v.value for v in values]
        result[metric] = {
            "average": round(sum(numeric) / len(numeric), 2),
            "latest": values[0].value,
            "min": min(numeric),
            "max": max(numeric),
            "count": len(numeric),
            "unit": values[0].unit,
            "quality": values[0].quality,
            "source": values[0].source,
            "latest_at": _aware(values[0].recorded_at),
        }
    return result


def _fmt(value: float, unit: str, decimals: int = 1) -> str:
    if unit in {"steps", "bpm"}:
        return f"{value:,.0f} {unit}"
    return f"{value:g} {unit}" if decimals == 0 else f"{value:.{decimals}f} {unit}"


def _system_status(
    *,
    available: int,
    expected: int,
    has_review: bool,
    max_status: str | None = None,
    has_any_measurement: bool,
) -> tuple[str, str]:
    if not has_any_measurement and expected > 0:
        return "missing", "No directly relevant measurements are available."
    if expected == 0:
        return "missing", "No validated direct measurement is available for this system."
    if has_review:
        return "review", "One or more latest measured values fall outside the reporting laboratory's interval."
    coverage = available / expected if expected else 0
    if coverage < 0.7:
        return "partial", f"{available} of {expected} expected measurement domains are available."
    if max_status == "partial":
        return "partial", "Available device or indirect data do not capture validated organ function."
    return "available", "Available measurements are within their reporting laboratory intervals."


def _build_system(
    system: dict,
    db: Session,
    user_id: str,
    latest_labs: dict,
    w_latest: dict,
    w_avg: dict,
    pgx: dict,
    profile: HealthProfile | None,
) -> TwinSystemSummary:
    expected_codes: list[str] = system["expected_codes"]
    expected_metrics: list[str] = system["expected_metrics"]
    measurements = 0
    has_review = False
    signals: list[TwinSignal] = []

    for code in expected_codes:
        pair = latest_labs.get(code)
        if not pair:
            continue
        result, biomarker = pair
        measurements += 1
        status = classify_range(result.value, result.ref_low, result.ref_high)
        if status in {"high", "low"}:
            has_review = True
        signals.append(
            TwinSignal(
                label=biomarker.name,
                value=f"{result.value:g} {biomarker.canonical_unit}",
                status=status,
                meta=f"{_aware(result.measured_at).strftime('%d %b %Y')} · lab range {result.ref_low}–{result.ref_high}".replace(
                    "None", "Not available"
                ),
            )
        )

    for metric in expected_metrics:
        if metric not in w_latest:
            continue
        measurements += 1
        summary = w_avg.get(metric, {})
        label, unit = METRIC_LABELS.get(metric, (metric, w_latest[metric].unit))
        avg = summary.get("average", w_latest[metric].value)
        signals.append(
            TwinSignal(
                label=label,
                value=_fmt(avg, unit, 0 if unit in {"steps", "bpm", "min"} else 1),
                status="device_estimate",
                meta=f"14-day average · {summary.get('count', 0)} device samples",
            )
        )

    total_expected = len(expected_codes) + len(expected_metrics)
    available = sum(1 for code in expected_codes if code in latest_labs) + sum(
        1 for metric in expected_metrics if metric in w_latest
    )
    completeness = round((available / total_expected) * 100) if total_expected else 0
    completeness = min(completeness, COMPLETENESS_CAP.get(system["id"], 100))
    max_status = "partial" if system["id"] in {"lungs", "brain", "digestive"} else None
    status, reason = _system_status(
        available=available,
        expected=total_expected,
        has_review=has_review,
        max_status=max_status,
        has_any_measurement=measurements > 0,
    )

    # Relevant genetic results (only where a phenotype actually exists).
    genes = [gene for gene in system["genes"] if gene in pgx][:4]
    if genes and profile and profile.is_synthetic:
        genes = genes
    last_candidates = [_aware(pair[0].measured_at) for code, pair in latest_labs.items() if code in expected_codes]
    last_candidates.extend(
        _aware(w_latest[metric].recorded_at) for metric in expected_metrics if metric in w_latest
    )
    last_updated = max(last_candidates) if last_candidates else None

    # Limit signals to a readable set but keep missingness visible.
    selected_signals = signals[:4]
    if len(signals) > 4:
        selected_signals.append(
            TwinSignal(label="Additional measurements", value=f"+{len(signals) - 4} more", status="available", meta=None)
        )

    return TwinSystemSummary(
        id=system["id"],
        name=system["name"],
        tagline=system["tagline"],
        accent=system["accent"],
        status=status,  # type: ignore[arg-type]
        status_reason=reason,
        completeness=completeness,
        measurements=measurements,
        genes=genes,
        pathways=system["pathways"],
        last_updated=last_updated,
        signals=selected_signals,
        limitations=system["limitations"],
    )


def build_overview(db: Session, user_id: str) -> TwinOverview:
    profile = db.scalar(select(HealthProfile).where(HealthProfile.user_id == user_id))
    latest_labs = latest_by_code(db, user_id)
    w_latest = latest_wearables(db, user_id)
    w_avg = wearable_averages(db, user_id)
    pgx = phenotype_map(db, user_id)
    systems = [
        _build_system(system, db, user_id, latest_labs, w_latest, w_avg, pgx, profile)
        for system in SYSTEMS
    ]
    dated = [system.last_updated for system in systems if system.last_updated]
    synthetic = any(result.is_synthetic for result, _ in latest_labs.values()) or any(
        measurement.is_synthetic for measurement in w_latest.values()
    ) or any(row.get("is_synthetic") for row in pgx.values())
    completeness = round(sum(system.completeness for system in systems) / len(systems)) if systems else 0
    return TwinOverview(
        systems=systems,
        overall_completeness=completeness,
        last_updated=max(dated) if dated else None,
        synthetic_data=synthetic,
        disclaimer=(
            "The digital body is a navigation and explanation interface. It is not a scan or an image of "
            "your organs, and no system is classified as diseased. Status reflects data availability and "
            "whether measured values fall outside their reporting laboratory intervals."
        ),
    )


def build_system_detail(db: Session, user_id: str, system_id: str) -> TwinSystemDetail | None:
    config = next((system for system in SYSTEMS if system["id"] == system_id), None)
    if not config:
        return None
    profile = db.scalar(select(HealthProfile).where(HealthProfile.user_id == user_id))
    latest_labs = latest_by_code(db, user_id)
    w_latest = latest_wearables(db, user_id)
    w_avg = wearable_averages(db, user_id)
    pgx = phenotype_map(db, user_id)
    summary = _build_system(config, db, user_id, latest_labs, w_latest, w_avg, pgx, profile)

    measurements_detail: list[dict] = []
    for code in config["expected_codes"]:
        pair = latest_labs.get(code)
        if not pair:
            measurements_detail.append(
                {
                    "kind": "lab",
                    "code": code,
                    "name": code.replace("_", " ").upper(),
                    "status": "missing",
                    "value": None,
                    "unit": None,
                    "date": None,
                    "ref_low": None,
                    "ref_high": None,
                    "source": None,
                    "label": "Missing",
                }
            )
            continue
        result, biomarker = pair
        status = classify_range(result.value, result.ref_low, result.ref_high)
        measurements_detail.append(
            {
                "kind": "lab",
                "code": code,
                "name": biomarker.name,
                "status": status,
                "value": result.value,
                "unit": result.unit,
                "date": _aware(result.measured_at).isoformat(),
                "ref_low": result.ref_low,
                "ref_high": result.ref_high,
                "ref_text": result.ref_text,
                "source": result.source,
                "method": result.method,
                "quality_status": result.quality_status,
                "confidence": result.confidence,
                "is_synthetic": result.is_synthetic,
                "label": "Laboratory measurement",
            }
        )
    for metric in config["expected_metrics"]:
        if metric in w_latest:
            measurement = w_latest[metric]
            label, unit = METRIC_LABELS.get(metric, (metric, measurement.unit))
            summary_metric = w_avg.get(metric, {})
            measurements_detail.append(
                {
                    "kind": "wearable",
                    "code": metric,
                    "name": label,
                    "status": "device_estimate",
                    "value": summary_metric.get("average", measurement.value),
                    "unit": unit,
                    "date": _aware(measurement.recorded_at).isoformat(),
                    "ref_low": None,
                    "ref_high": None,
                    "source": measurement.source,
                    "method": "consumer device estimate",
                    "quality_status": measurement.quality,
                    "confidence": 0.5,
                    "is_synthetic": measurement.is_synthetic,
                    "label": "Wearable estimate · 14-day average",
                }
            )
        else:
            measurements_detail.append(
                {
                    "kind": "wearable",
                    "code": metric,
                    "name": METRIC_LABELS.get(metric, (metric, ""))[0],
                    "status": "missing",
                    "value": None,
                    "unit": None,
                    "date": None,
                    "source": None,
                    "label": "Missing device data",
                }
            )

    genetic_factors = []
    for gene in config["genes"]:
        if gene in pgx:
            info = pgx[gene]
            genetic_factors.append(
                {
                    "gene": gene,
                    "diplotype": info["diplotype"],
                    "phenotype": info["phenotype"],
                    "guideline": info["guideline"],
                    "evidence_level": info["evidence_level"],
                    "is_synthetic": info["is_synthetic"],
                    "interpretation": info["interpretation"],
                    "limitations": info["limitations"],
                }
            )

    risk_factors = []
    if profile:
        condition_names = {condition.get("name") for condition in (profile.conditions or [])}
        for condition in SYSTEM_CONDITION_MAP.get(system_id, []):
            if condition in condition_names:
                risk_factors.append(f"{condition} (self-reported condition)")
        if profile.allergies and system_id == "immune":
            for allergy in profile.allergies:
                risk_factors.append(
                    f"Reported allergy: {allergy.get('substance')} ({allergy.get('severity', 'unknown')} severity; patient-reported)"
                )

    evidence_quality = (
        "Moderate: synthetic laboratory measurements plus device-derived estimates. "
        "No validated diagnostic study for this system is connected."
        if summary.status in {"available", "review"}
        else "Limited: data are incomplete or indirect. Interpretation must remain conservative."
    )
    uncertainty = (
        "Measurement uncertainty includes pre-analytical variation, laboratory assay variation, and "
        "biological variation. Status compares a single latest value with the laboratory's interval and "
        "does not account for that variation. No probabilistic diagnostic model is used."
    )

    connected = [
        system["name"] for system in SYSTEMS if system["id"] in config.get("connected", [])
    ] or [system["name"] for system in SYSTEMS if system["id"] in config.get("connected", [])]
    connected = [
        next((s["name"] for s in SYSTEMS if s["id"] == other_id), other_id)
        for other_id in config.get("connected", [])
    ]

    return TwinSystemDetail(
        **summary.model_dump(),
        description=config["description"],
        measurements_detail=measurements_detail,
        genetic_factors=genetic_factors,
        risk_factors=risk_factors,
        connected_systems=connected,
        evidence_quality=evidence_quality,
        uncertainty=uncertainty,
    )

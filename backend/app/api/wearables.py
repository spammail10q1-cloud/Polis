from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select

from app.core.security import CurrentUser, DbSession
from app.data.demo import WEARABLE_REGISTRY
from app.models import WearableDevice, WearableMeasurement
from app.schemas import WearableDeviceOut, WearableMetricSummary, WearableOverview
from app.services import audit
from app.services.twin import METRIC_LABELS, wearable_averages

router = APIRouter(prefix="/wearables", tags=["wearables"])

METRIC_UNITS = {
    "sleep_duration": ({"h", "hours"}, 0, 24),
    "deep_sleep": ({"h", "hours"}, 0, 12),
    "rem_sleep": ({"h", "hours"}, 0, 12),
    "resting_hr": ({"bpm"}, 25, 220),
    "hrv": ({"ms"}, 1, 400),
    "steps": ({"steps", "count"}, 0, 200000),
    "respiratory_rate": ({"breaths/min", "breaths per minute", "rpm"}, 3, 80),
    "skin_temp": ({"°c", "°c deviation", "c", "c deviation"}, -10, 10),
    "spo2": ({"%", "percent"}, 50, 100),
    "active_minutes": ({"min", "minutes"}, 0, 1440),
}


@router.get("", response_model=WearableOverview)
def wearables(user: CurrentUser, db: DbSession) -> WearableOverview:
    devices = list(
        db.scalars(
            select(WearableDevice)
            .where(WearableDevice.user_id == user.id)
            .order_by(WearableDevice.created_at)
        ).all()
    )
    latest_rows = list(
        db.scalars(
            select(WearableMeasurement)
            .where(WearableMeasurement.user_id == user.id)
            .order_by(WearableMeasurement.recorded_at.desc())
        ).all()
    )
    latest: dict[str, WearableMeasurement] = {}
    for row in latest_rows:
        latest.setdefault(row.metric, row)
    averages = wearable_averages(db, user.id, days=14)
    metrics = []
    for metric, row in latest.items():
        summary = averages.get(metric, {})
        label, unit = METRIC_LABELS.get(metric, (metric, row.unit))
        metrics.append(
            WearableMetricSummary(
                metric=metric,
                label=label,
                unit=unit,
                latest=round(row.value, 2),
                average=round(summary.get("average", row.value), 2),
                min_value=round(summary.get("min", row.value), 2),
                max_value=round(summary.get("max", row.value), 2),
                sample_count=summary.get("count", 1),
                quality=row.quality,
                source=row.source,
            )
        )
    metrics.sort(key=lambda item: item.label)
    return WearableOverview(
        devices=[WearableDeviceOut.model_validate(device) for device in devices],
        metrics=metrics,
        integration_registry=WEARABLE_REGISTRY,
    )


@router.get("/series")
def series(
    user: CurrentUser,
    db: DbSession,
    metric: str = Query(min_length=2, max_length=48),
    days: int = Query(default=45, ge=1, le=365),
) -> dict:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = list(
        db.scalars(
            select(WearableMeasurement)
            .where(
                WearableMeasurement.user_id == user.id,
                WearableMeasurement.metric == metric,
                WearableMeasurement.recorded_at >= cutoff,
            )
            .order_by(WearableMeasurement.recorded_at)
        ).all()
    )
    label, unit = METRIC_LABELS.get(metric, (metric, rows[0].unit if rows else ""))
    return {
        "metric": metric,
        "label": label,
        "unit": unit,
        "quality": "device_estimate",
        "source": rows[0].source if rows else None,
        "points": [
            {"date": row.recorded_at.isoformat(), "value": row.value, "is_synthetic": row.is_synthetic}
            for row in rows
        ],
        "data_quality_note": (
            "Consumer-device estimates are not laboratory measurements and can contain motion, wear, and "
            "proprietary-algorithm error. They are not diagnostic."
        ),
    }


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_wearable_csv(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> dict:
    filename = (file.filename or "wearable-import.csv").strip()
    content = await file.read()
    if len(content) > 5_000_000:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Wearable CSV exceeds the 5 MB MVP limit.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Wearable CSV must be UTF-8 encoded.") from exc
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t").delimiter
    except csv.Error:
        dialect = ","
    reader = csv.DictReader(io.StringIO(text), delimiter=dialect)
    if not reader.fieldnames:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="CSV has no header row.")
    normalized = {name.strip().lower(): name for name in reader.fieldnames if name}
    required = {"metric", "value", "unit", "date"}
    if not required.issubset(normalized):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSV needs headers: {', '.join(sorted(required))}.",
        )

    device = db.scalar(
        select(WearableDevice).where(
            WearableDevice.user_id == user.id,
            WearableDevice.provider == "manual_import",
        )
    )
    created_device = False
    if not device:
        device = WearableDevice(
            user_id=user.id,
            provider="manual_import",
            name="Manual wearable import",
            connection_status="manual_import",
            last_synced_at=datetime.now(UTC),
            is_synthetic=False,
        )
        db.add(device)
        db.flush()
        created_device = True

    imported = 0
    skipped = 0
    errors: list[str] = []
    warnings: list[str] = []
    seen = set()
    for index, raw in enumerate(reader, start=2):
        if index > 5002:
            warnings.append("Import limited to 5,000 rows.")
            break
        row = {key: (raw.get(normalized.get(key, ""), "") or "").strip() for key in ["metric", "value", "unit", "date", "source"] if key in normalized}
        if not row.get("metric") and not row.get("value"):
            continue
        metric = row.get("metric", "").lower()
        spec = METRIC_UNITS.get(metric)
        if not spec:
            errors.append(f"Row {index}: unsupported metric '{metric}'.")
            continue
        allowed_units, low, high = spec
        unit = row.get("unit", "")
        if unit.lower() not in allowed_units:
            errors.append(f"Row {index}: unit '{unit}' is not supported for {metric}; allowed: {', '.join(sorted(allowed_units))}.")
            continue
        try:
            value = float(row.get("value", "").replace(",", ""))
        except ValueError:
            errors.append(f"Row {index}: value is not numeric.")
            continue
        if value < low or value > high:
            errors.append(f"Row {index}: value outside the supported range {low}–{high}.")
            continue
        raw_date = row.get("date", "")
        recorded = None
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d %b %Y"):
            try:
                parsed = datetime.strptime(raw_date, fmt)
                recorded = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
                break
            except ValueError:
                continue
        if recorded is None:
            try:
                recorded = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                recorded = recorded.replace(tzinfo=UTC) if recorded.tzinfo is None else recorded.astimezone(UTC)
            except ValueError:
                errors.append(f"Row {index}: date must be ISO 8601 (YYYY-MM-DD or full timestamp).")
                continue
        if recorded > datetime.now(UTC) + timedelta(minutes=10):
            errors.append(f"Row {index}: date is in the future.")
            continue
        canonical_metric = metric
        canonical_unit = {
            "sleep_duration": "h", "deep_sleep": "h", "rem_sleep": "h", "resting_hr": "bpm",
            "hrv": "ms", "steps": "steps", "respiratory_rate": "breaths/min",
            "skin_temp": "°C", "spo2": "%", "active_minutes": "min",
        }[metric]
        key = (canonical_metric, recorded)
        if key in seen:
            skipped += 1
            continue
        existing = db.scalar(
            select(WearableMeasurement).where(
                WearableMeasurement.user_id == user.id,
                WearableMeasurement.metric == canonical_metric,
                WearableMeasurement.recorded_at == recorded,
            )
        )
        if existing:
            skipped += 1
            continue
        seen.add(key)
        db.add(
            WearableMeasurement(
                user_id=user.id,
                device_id=device.id,
                metric=canonical_metric,
                value=value,
                unit=canonical_unit,
                recorded_at=recorded,
                source=row.get("source") or f"Manual import: {filename}",
                quality="user_import",
                is_synthetic=False,
            )
        )
        imported += 1
    if imported:
        device.last_synced_at = datetime.now(UTC)
    audit.record(
        db,
        user_id=user.id,
        action="wearables.import",
        resource_type="wearable_import",
        detail={"filename": filename, "imported": imported, "skipped": skipped, "errors": len(errors)},
    )
    db.commit()
    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:25],
        "warnings": warnings,
        "device": WearableDeviceOut.model_validate(device).model_dump(mode="json"),
        "notice": (
            "Imported wearable values are user-supplied device estimates, not laboratory measurements. "
            "No live provider connection is implied."
        ),
    }


@router.get("/integrations")
def integrations(user: CurrentUser) -> dict:
    return {
        "integrations": WEARABLE_REGISTRY,
        "operational": False,
        "note": (
            "Integration interfaces are designed but no third-party OAuth authorization or live ingestion is "
            "enabled in this MVP. The displayed wearable data are labelled synthetic samples."
        ),
    }
